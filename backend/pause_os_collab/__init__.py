"""
PAUSE OS Collaboration Module
Модуль для совместной работы над творческими проектами
"""

from .project_analyzer import ProjectAnalyzer
from .notebook_lm_orchestrator import NotebookLMOrchestrator
from .critic_feedback import CriticFeedback
from .collab_coordinator import CollabCoordinator

__all__ = [
    "ProjectAnalyzer",
    "NotebookLMOrchestrator",
    "CriticFeedback",
    "CollabCoordinator",
]
