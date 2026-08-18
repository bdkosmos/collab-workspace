"""
FastAPI Backend с WebSocket синхронизацией
Collaborative Workspace сервер
"""

import json
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from pause_os_collab.project_analyzer import ProjectAnalyzer
from pause_os_collab.notebook_lm_orchestrator import NotebookLMOrchestrator
from pause_os_collab.critic_feedback import CriticFeedback
from pause_os_collab.collab_coordinator import CollabCoordinator


# ===== МОДЕЛИ ДАННЫХ =====

class ProjectCreate(BaseModel):
    title: str
    content: str = ""
    author: str = "anonymous"


class ProjectUpdate(BaseModel):
    content: str
    author: str


class FeedbackCreate(BaseModel):
    project_id: str
    author: str
    content: str
    feedback_type: str = "general"
    line_number: Optional[int] = None


class VersionCreate(BaseModel):
    project_id: str
    content: str
    author: str
    comment: str = ""


class ChatMessage(BaseModel):
    project_id: str
    author: str
    message: str


# ===== ХРАНИЛИЩЕ =====

class ProjectStore:
    """In-memory хранилище проектов"""
    
    def __init__(self):
        self.projects: Dict[str, dict] = {}
        self.project_counter = 0
    
    def create(self, title: str, content: str = "", author: str = "anonymous") -> dict:
        self.project_counter += 1
        project_id = f"proj_{self.project_counter}"
        
        project = {
            "id": project_id,
            "title": title,
            "content": content,
            "author": author,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "collaborators": [author],
            "is_active": True
        }
        
        self.projects[project_id] = project
        return project
    
    def get(self, project_id: str) -> Optional[dict]:
        return self.projects.get(project_id)
    
    def get_all(self) -> List[dict]:
        return sorted(
            [p for p in self.projects.values() if p["is_active"]],
            key=lambda x: x["updated_at"],
            reverse=True
        )
    
    def update(self, project_id: str, content: str, author: str) -> Optional[dict]:
        project = self.projects.get(project_id)
        if not project:
            return None
        
        project["content"] = content
        project["updated_at"] = datetime.now().isoformat()
        
        if author not in project["collaborators"]:
            project["collaborators"].append(author)
        
        return project


# ===== WEBSOCKET МЕНЕДЖЕР =====

class ConnectionManager:
    """Управление WebSocket соединениями"""
    
    def __init__(self):
        # project_id -> {websocket: user_name}
        self.active_connections: Dict[str, Dict[WebSocket, str]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str, user: str):
        await websocket.accept()
        
        if project_id not in self.active_connections:
            self.active_connections[project_id] = {}
        
        self.active_connections[project_id][websocket] = user
        
        # Уведомляем всех о новом участнике
        await self.broadcast(project_id, {
            "type": "user_joined",
            "user": user,
            "timestamp": datetime.now().isoformat(),
            "participants": list(self.active_connections[project_id].values())
        }, exclude=websocket)
    
    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            user = self.active_connections[project_id].pop(websocket, None)
            
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
            elif user:
                # Уведомляем об уходе
                asyncio.create_task(self.broadcast(project_id, {
                    "type": "user_left",
                    "user": user,
                    "timestamp": datetime.now().isoformat()
                }))
    
    async def broadcast(self, project_id: str, message: dict, exclude: WebSocket = None):
        """Отправляет сообщение всем участникам проекта"""
        if project_id not in self.active_connections:
            return
        
        disconnected = []
        for ws, user in list(self.active_connections[project_id].items()):
            if ws != exclude:
                try:
                    await ws.send_json(message)
                except:
                    disconnected.append(ws)
        
        # Удаляем отключившихся
        for ws in disconnected:
            self.disconnect(ws, project_id)
    
    async def send_to_user(self, websocket: WebSocket, message: dict):
        """Отправляет сообщение конкретному пользователю"""
        try:
            await websocket.send_json(message)
        except:
            pass
    
    def get_participants(self, project_id: str) -> List[str]:
        """Получает список участников проекта"""
        if project_id not in self.active_connections:
            return []
        return list(self.active_connections[project_id].values())


# ===== ИНИЦИАЛИЗАЦИЯ =====

store = ProjectStore()
manager = ConnectionManager()
analyzer = ProjectAnalyzer()
orchestrator = NotebookLMOrchestrator()
feedback_system = CriticFeedback()
coordinator = CollabCoordinator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Collaborative Workspace сервер запускается...")
    yield
    # Shutdown
    print("👋 Сервер остановлен")


app = FastAPI(title="Collaborative Workspace", lifespan=lifespan)


# ===== API ENDPOINTS =====

# ===== НАСТРОЙКИ ПУТЕЙ =====
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Раздача статики
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def root():
    """Главная страница"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return {"message": "Collaborative Workspace API", "version": "1.0"}


@app.get("/api/projects")
async def get_projects():
    """Получить список всех проектов"""
    return store.get_all()


@app.post("/api/projects")
async def create_project(project: ProjectCreate):
    """Создать новый проект"""
    new_project = store.create(project.title, project.content, project.author)
    
    # Создаём начальную версию
    if project.content:
        coordinator.create_version(
            new_project["id"],
            project.content,
            project.author,
            "Начальная версия"
        )
    
    return new_project


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Получить проект по ID"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, update: ProjectUpdate):
    """Обновить проект"""
    project = store.update(project_id, update.content, update.author)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


@app.get("/api/projects/{project_id}/versions")
async def get_versions(project_id: str):
    """Получить историю версий проекта"""
    versions = coordinator.get_project_versions(project_id)
    return [coordinator.to_dict_version(v) for v in versions]


@app.post("/api/projects/{project_id}/versions")
async def create_version(project_id: str, version: VersionCreate):
    """Создать новую версию"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    new_version = coordinator.create_version(
        project_id, version.content, version.author, version.comment
    )
    
    return coordinator.to_dict_version(new_version)


@app.get("/api/projects/{project_id}/feedback")
async def get_feedback(project_id: str):
    """Получить фидбек проекта"""
    items = feedback_system.get_project_feedback(project_id)
    return [feedback_system.to_dict(item) for item in items]


@app.post("/api/projects/{project_id}/feedback")
async def add_feedback(project_id: str, feedback: FeedbackCreate):
    """Добавить фидбек"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    item = feedback_system.add_feedback(
        project_id, feedback.author, feedback.content,
        feedback.feedback_type, feedback.line_number
    )
    
    return feedback_system.to_dict(item)


@app.get("/api/projects/{project_id}/analysis")
async def analyze_project(project_id: str):
    """Проанализировать проект"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    if not project["content"]:
        return {"error": "Проект пуст"}
    
    result = analyzer.analyze(project["content"])
    
    return {
        "themes": result.themes,
        "sentiment": result.sentiment,
        "key_elements": result.key_elements,
        "complexity_score": result.complexity_score,
        "suggestions": result.suggestions,
        "word_count": result.word_count,
        "reading_time_minutes": result.reading_time_minutes
    }


@app.post("/api/projects/{project_id}/brainstorm")
async def brainstorm(project_id: str, request: dict):
    """Сгенерировать идеи для проекта"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    prompt_data = orchestrator.brainstorm_ideas(
        project["title"],
        project["content"][:500],
        context=request.get("context", ""),
        num_ideas=request.get("num_ideas", 5)
    )
    
    return prompt_data


# ===== WEBSOCKET ENDPOINT =====

@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str, user: str = Query("anonymous")):
    """WebSocket для real-time синхронизации"""
    
    await manager.connect(websocket, project_id, user)
    
    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_json()
            
            msg_type = data.get("type")
            
            if msg_type == "content_update":
                # Обновление контента
                content = data.get("content", "")
                author = data.get("author", user)
                
                # Обновляем проект
                store.update(project_id, content, author)
                
                # Рассылаем всем остальным
                await manager.broadcast(project_id, {
                    "type": "content_updated",
                    "content": content,
                    "author": author,
                    "timestamp": datetime.now().isoformat()
                }, exclude=websocket)
            
            elif msg_type == "cursor_position":
                # Позиция курсора
                await manager.broadcast(project_id, {
                    "type": "cursor_moved",
                    "user": user,
                    "position": data.get("position"),
                    "timestamp": datetime.now().isoformat()
                }, exclude=websocket)
            
            elif msg_type == "chat_message":
                # Чат-сообщение
                message = data.get("message", "")
                await manager.broadcast(project_id, {
                    "type": "chat_message",
                    "user": user,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
            
            elif msg_type == "save_version":
                # Сохранение версии
                content = data.get("content", "")
                comment = data.get("comment", "")
                
                version = coordinator.create_version(project_id, content, user, comment)
                
                await manager.broadcast(project_id, {
                    "type": "version_saved",
                    "version": coordinator.to_dict_version(version),
                    "by": user,
                    "timestamp": datetime.now().isoformat()
                })
            
            elif msg_type == "request_analysis":
                # Запрос анализа
                project = store.get(project_id)
                if project and project["content"]:
                    result = analyzer.analyze(project["content"])
                    
                    await manager.send_to_user(websocket, {
                        "type": "analysis_result",
                        "analysis": {
                            "themes": result.themes,
                            "sentiment": result.sentiment,
                            "suggestions": result.suggestions,
                            "complexity_score": result.complexity_score
                        }
                    })
            
            elif msg_type == "ping":
                await manager.send_to_user(websocket, {"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, project_id)


# ===== STATIC FILES =====

# Предполагается, что frontend файлы будут в ../frontend
# Для разработки можно использовать отдельный сервер

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
