"""
CollabCoordinator - координатор совместной работы
Управляет версиями и сессиями коллаборации
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import difflib
import uuid


class SessionStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


@dataclass
class Version:
    """Версия проекта"""
    id: str
    project_id: str
    content: str
    author: str
    comment: str
    created_at: datetime
    version_number: int
    parent_version: Optional[str] = None


@dataclass
class CollaborationSession:
    """Сессия совместной работы"""
    id: str
    project_id: str
    participants: Set[str]
    status: SessionStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    current_version_id: Optional[str] = None
    activity_log: List[Dict] = field(default_factory=list)


class CollabCoordinator:
    """Координирует совместную работу и версионирование"""
    
    def __init__(self):
        self._versions: Dict[str, Version] = {}
        self._project_versions: Dict[str, List[str]] = {}  # project_id -> [version_ids]
        self._sessions: Dict[str, CollaborationSession] = {}
        self._project_sessions: Dict[str, List[str]] = {}  # project_id -> [session_ids]
    
    def create_version(self, project_id: str, content: str, author: str,
                       comment: str = "", parent_version: Optional[str] = None) -> Version:
        """Создаёт новую версию проекта"""
        
        version_id = str(uuid.uuid4())
        
        # Определяем номер версии
        existing_versions = self._project_versions.get(project_id, [])
        version_number = len(existing_versions) + 1
        
        version = Version(
            id=version_id,
            project_id=project_id,
            content=content,
            author=author,
            comment=comment,
            created_at=datetime.now(),
            version_number=version_number,
            parent_version=parent_version
        )
        
        self._versions[version_id] = version
        
        if project_id not in self._project_versions:
            self._project_versions[project_id] = []
        self._project_versions[project_id].append(version_id)
        
        return version
    
    def get_version(self, version_id: str) -> Optional[Version]:
        """Получает версию по ID"""
        return self._versions.get(version_id)
    
    def get_project_versions(self, project_id: str) -> List[Version]:
        """Получает все версии проекта"""
        version_ids = self._project_versions.get(project_id, [])
        versions = [self._versions[vid] for vid in version_ids if vid in self._versions]
        return sorted(versions, key=lambda v: v.version_number, reverse=True)
    
    def get_latest_version(self, project_id: str) -> Optional[Version]:
        """Получает последнюю версию проекта"""
        versions = self.get_project_versions(project_id)
        return versions[0] if versions else None
    
    def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """Сравнивает две версии и возвращает diff"""
        v1 = self._versions.get(version_id_1)
        v2 = self._versions.get(version_id_2)
        
        if not v1 or not v2:
            return {"error": "Одна или обе версии не найдены"}
        
        lines1 = v1.content.splitlines(keepends=True)
        lines2 = v2.content.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            lines1, lines2,
            fromfile=f"v{v1.version_number}",
            tofile=f"v{v2.version_number}",
            lineterm=""
        ))
        
        return {
            "version_1": v1.version_number,
            "version_2": v2.version_number,
            "author_1": v1.author,
            "author_2": v2.author,
            "diff": "\n".join(diff),
            "changes_count": len([l for l in diff if l.startswith('+') or l.startswith('-')])
        }
    
    def start_session(self, project_id: str, participant: str) -> CollaborationSession:
        """Начинает новую сессию коллаборации"""
        
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Получаем текущую версию
        latest = self.get_latest_version(project_id)
        
        session = CollaborationSession(
            id=session_id,
            project_id=project_id,
            participants={participant},
            status=SessionStatus.ACTIVE,
            started_at=now,
            current_version_id=latest.id if latest else None,
            activity_log=[{
                "action": "session_started",
                "by": participant,
                "at": now.isoformat()
            }]
        )
        
        self._sessions[session_id] = session
        
        if project_id not in self._project_sessions:
            self._project_sessions[project_id] = []
        self._project_sessions[project_id].append(session_id)
        
        return session
    
    def join_session(self, session_id: str, participant: str) -> Optional[CollaborationSession]:
        """Добавляет участника в сессию"""
        session = self._sessions.get(session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            return None
        
        session.participants.add(participant)
        session.activity_log.append({
            "action": "participant_joined",
            "by": participant,
            "at": datetime.now().isoformat()
        })
        
        return session
    
    def leave_session(self, session_id: str, participant: str) -> Optional[CollaborationSession]:
        """Убирает участника из сессии"""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        session.participants.discard(participant)
        session.activity_log.append({
            "action": "participant_left",
            "by": participant,
            "at": datetime.now().isoformat()
        })
        
        if len(session.participants) == 0:
            session.status = SessionStatus.ENDED
            session.ended_at = datetime.now()
        
        return session
    
    def log_activity(self, session_id: str, action: str, user: str, details: Dict = None):
        """Логирует активность в сессии"""
        session = self._sessions.get(session_id)
        if session:
            entry = {
                "action": action,
                "by": user,
                "at": datetime.now().isoformat(),
                "details": details or {}
            }
            session.activity_log.append(entry)
    
    def get_active_sessions(self, project_id: str) -> List[CollaborationSession]:
        """Получает активные сессии проекта"""
        session_ids = self._project_sessions.get(project_id, [])
        sessions = [self._sessions[sid] for sid in session_ids if sid in self._sessions]
        return [s for s in sessions if s.status == SessionStatus.ACTIVE]
    
    def to_dict_version(self, version: Version) -> Dict[str, Any]:
        """Конвертирует версию в словарь"""
        return {
            "id": version.id,
            "project_id": version.project_id,
            "author": version.author,
            "comment": version.comment,
            "created_at": version.created_at.isoformat(),
            "version_number": version.version_number,
            "parent_version": version.parent_version,
            "content_preview": version.content[:200] + "..." if len(version.content) > 200 else version.content
        }
    
    def to_dict_session(self, session: CollaborationSession) -> Dict[str, Any]:
        """Конвертирует сессию в словарь"""
        return {
            "id": session.id,
            "project_id": session.project_id,
            "participants": list(session.participants),
            "status": session.status.value,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "current_version_id": session.current_version_id,
            "activity_count": len(session.activity_log)
        }
