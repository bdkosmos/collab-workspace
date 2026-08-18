"""
CriticFeedback - система обратной связи
Управляет фидбеком и комментариями к проектам
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class FeedbackType(Enum):
    STRENGTH = "strength"           # Сильная сторона
    IMPROVEMENT = "improvement"     # Область для улучшения
    QUESTION = "question"           # Вопрос
    IDEA = "idea"                   # Идея/предложение
    GENERAL = "general"             # Общий комментарий


class FeedbackStatus(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class FeedbackItem:
    """Элемент фидбека"""
    id: str
    project_id: str
    author: str
    content: str
    feedback_type: FeedbackType
    status: FeedbackStatus
    created_at: datetime
    updated_at: datetime
    line_number: Optional[int] = None
    section: Optional[str] = None
    parent_id: Optional[str] = None  # Для ответов на фидбек
    reactions: Dict[str, int] = field(default_factory=dict)  # emoji -> count


class CriticFeedback:
    """Система управления фидбеком"""
    
    def __init__(self):
        self._feedback: Dict[str, FeedbackItem] = {}
        self._project_feedback: Dict[str, List[str]] = {}  # project_id -> [feedback_ids]
    
    def add_feedback(self, project_id: str, author: str, content: str,
                     feedback_type: str = "general", line_number: Optional[int] = None,
                     section: Optional[str] = None, parent_id: Optional[str] = None) -> FeedbackItem:
        """Добавляет новый фидбек"""
        
        feedback_id = str(uuid.uuid4())
        now = datetime.now()
        
        try:
            fb_type = FeedbackType(feedback_type)
        except ValueError:
            fb_type = FeedbackType.GENERAL
        
        item = FeedbackItem(
            id=feedback_id,
            project_id=project_id,
            author=author,
            content=content,
            feedback_type=fb_type,
            status=FeedbackStatus.NEW,
            created_at=now,
            updated_at=now,
            line_number=line_number,
            section=section,
            parent_id=parent_id,
            reactions={}
        )
        
        self._feedback[feedback_id] = item
        
        if project_id not in self._project_feedback:
            self._project_feedback[project_id] = []
        self._project_feedback[project_id].append(feedback_id)
        
        return item
    
    def get_feedback(self, feedback_id: str) -> Optional[FeedbackItem]:
        """Получает фидбек по ID"""
        return self._feedback.get(feedback_id)
    
    def get_project_feedback(self, project_id: str, 
                            feedback_type: Optional[str] = None) -> List[FeedbackItem]:
        """Получает все фидбеки проекта"""
        feedback_ids = self._project_feedback.get(project_id, [])
        items = [self._feedback[fid] for fid in feedback_ids if fid in self._feedback]
        
        if feedback_type:
            try:
                fb_type = FeedbackType(feedback_type)
                items = [i for i in items if i.feedback_type == fb_type]
            except ValueError:
                pass
        
        return sorted(items, key=lambda x: x.created_at, reverse=True)
    
    def update_status(self, feedback_id: str, status: str) -> Optional[FeedbackItem]:
        """Обновляет статус фидбека"""
        item = self._feedback.get(feedback_id)
        if not item:
            return None
        
        try:
            item.status = FeedbackStatus(status)
            item.updated_at = datetime.now()
        except ValueError:
            pass
        
        return item
    
    def add_reaction(self, feedback_id: str, emoji: str) -> bool:
        """Добавляет реакцию к фидбеку"""
        item = self._feedback.get(feedback_id)
        if not item:
            return False
        
        item.reactions[emoji] = item.reactions.get(emoji, 0) + 1
        return True
    
    def get_feedback_stats(self, project_id: str) -> Dict[str, Any]:
        """Статистика фидбека проекта"""
        items = self.get_project_feedback(project_id)
        
        stats = {
            "total": len(items),
            "by_type": {},
            "by_status": {},
            "open_count": 0,
            "resolved_count": 0
        }
        
        for item in items:
            type_name = item.feedback_type.value
            status_name = item.status.value
            
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            stats["by_status"][status_name] = stats["by_status"].get(status_name, 0) + 1
            
            if item.status in [FeedbackStatus.NEW, FeedbackStatus.IN_PROGRESS]:
                stats["open_count"] += 1
            elif item.status == FeedbackStatus.RESOLVED:
                stats["resolved_count"] += 1
        
        return stats
    
    def get_pending_feedback(self, project_id: str, author: Optional[str] = None) -> List[FeedbackItem]:
        """Получает нерешённый фидбек"""
        items = self.get_project_feedback(project_id)
        pending = [i for i in items if i.status in [FeedbackStatus.NEW, FeedbackStatus.IN_PROGRESS]]
        
        if author:
            pending = [i for i in pending if i.author != author]
        
        return pending
    
    def to_dict(self, item: FeedbackItem) -> Dict[str, Any]:
        """Конвертирует фидбек в словарь"""
        return {
            "id": item.id,
            "project_id": item.project_id,
            "author": item.author,
            "content": item.content,
            "feedback_type": item.feedback_type.value,
            "status": item.status.value,
            "created_at": item.created_at.isoformat(),
            "line_number": item.line_number,
            "section": item.section,
            "parent_id": item.parent_id,
            "reactions": item.reactions
        }
