"""
NotebookLMOrchestrator - оркестратор для генерации промптов
Создаёт контекстно-зависимые промпты для LLM
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class PromptType(Enum):
    BRAINSTORM = "brainstorm"
    EXPAND = "expand"
    CRITIQUE = "critique"
    COLLABORATE = "collaborate"
    SUMMARIZE = "summarize"


@dataclass
class PromptTemplate:
    """Шаблон промпта"""
    system_prompt: str
    user_template: str
    context_window: int = 4000
    temperature: float = 0.7


class NotebookLMOrchestrator:
    """Оркестрирует генерацию промптов для разных задач"""
    
    def __init__(self):
        self.templates: Dict[PromptType, PromptTemplate] = {
            PromptType.BRAINSTORM: PromptTemplate(
                system_prompt="""Ты креативный помощник для brainstorm-сессий. 
Генерируй необычные идеи, мыслишь ассоциативно, предлагаешь нестандартные подходы.
Отвечай на русском языке.""",
                user_template="""Проект: {project_title}
Описание: {project_description}
Текущий контекст: {context}

Задача: Сгенерируй {num_ideas} креативных идеи для развития этого проекта.
Каждая идея должна быть:
- Конкретной и реализуемой
- Оригинальной (не банальной)
- С кратким обоснованием почему это сработает"""
            ),
            PromptType.EXPAND: PromptTemplate(
                system_prompt="""Ты помощник для развития идей. 
Берёшь базовую концепцию и детально её прорабатываешь.
Отвечай на русском языке.""",
                user_template="""Проект: {project_title}
Раздел для расширения: {section}
Текущий текст: {current_text}

Задача: Детально развей эту идею. Добавь:
- Конкретные примеры
- Детали реализации
- Возможные варианты развития
- Потенциальные сложности и их решения"""
            ),
            PromptType.CRITIQUE: PromptTemplate(
                system_prompt="""Ты конструктивный критик. 
Анализируешь проекты объективно, находишь сильные и слабые стороны.
Твоя критика всегда конструктивна и помогает улучшить проект.
Отвечай на русском языке.""",
                user_template="""Проект: {project_title}
Содержание: {content}

Задача: Проведи конструктивный анализ проекта:
1. Сильные стороны (что работает хорошо)
2. Области для улучшения
3. Потенциальные риски
4. Конкретные рекомендации"""
            ),
            PromptType.COLLABORATE: PromptTemplate(
                system_prompt="""Ты помощник для совместной работы.
Помогаешь командам синхронизироваться и эффективно сотрудничать.
Отвечай на русском языке.""",
                user_template="""Проект: {project_title}
Участники: {participants}
Текущий статус: {status}
Недавние изменения: {recent_changes}

Задача: Предложи:
1. Следующие шаги для команды
2. Как разделить работу между участниками
3. Возможные точки синхронизации
4. Рекомендации по коммуникации"""
            ),
            PromptType.SUMMARIZE: PromptTemplate(
                system_prompt="""Ты эксперт по саммаризации.
Создаёшь краткие, информативные резюме сохраняя ключевые моменты.
Отвечай на русском языке.""",
                user_template="""Содержание для саммаризации: {content}

Задача: Создай краткое резюме (максимум {max_length} слов).
Выдели:
- Главную идею
- Ключевые пункты (3-5)
- Следующие шаги или выводы"""
            ),
        }
    
    def generate_prompt(self, prompt_type: PromptType, **kwargs) -> Dict[str, Any]:
        """Генерирует полный промпт для LLM"""
        template = self.templates.get(prompt_type)
        if not template:
            raise ValueError(f"Неизвестный тип промпта: {prompt_type}")
        
        user_prompt = template.user_template.format(**kwargs)
        
        return {
            "system": template.system_prompt,
            "user": user_prompt,
            "temperature": template.temperature,
            "max_tokens": template.context_window,
        }
    
    def brainstorm_ideas(self, project_title: str, project_description: str, 
                         context: str = "", num_ideas: int = 5) -> Dict[str, Any]:
        """Генерирует промпт для brainstorm"""
        return self.generate_prompt(
            PromptType.BRAINSTORM,
            project_title=project_title,
            project_description=project_description,
            context=context,
            num_ideas=num_ideas
        )
    
    def expand_section(self, project_title: str, section: str, 
                       current_text: str) -> Dict[str, Any]:
        """Генерирует промпт для расширения раздела"""
        return self.generate_prompt(
            PromptType.EXPAND,
            project_title=project_title,
            section=section,
            current_text=current_text
        )
    
    def critique_project(self, project_title: str, content: str) -> Dict[str, Any]:
        """Генерирует промпт для критики проекта"""
        return self.generate_prompt(
            PromptType.CRITIQUE,
            project_title=project_title,
            content=content
        )
    
    def collaboration_plan(self, project_title: str, participants: List[str],
                          status: str, recent_changes: str) -> Dict[str, Any]:
        """Генерирует промпт для планирования совместной работы"""
        return self.generate_prompt(
            PromptType.COLLABORATE,
            project_title=project_title,
            participants=", ".join(participants),
            status=status,
            recent_changes=recent_changes
        )
    
    def summarize(self, content: str, max_length: int = 100) -> Dict[str, Any]:
        """Генерирует промпт для саммаризации"""
        return self.generate_prompt(
            PromptType.SUMMARIZE,
            content=content,
            max_length=max_length
        )
    
    def create_chat_context(self, project_history: List[Dict], 
                           current_topic: str) -> str:
        """Создаёт контекст для чат-ассистента"""
        context_parts = []
        
        if project_history:
            context_parts.append("История проекта:")
            for entry in project_history[-5:]:  # Последние 5 записей
                context_parts.append(f"- {entry.get('action', 'изменение')}: {entry.get('summary', '')}")
        
        context_parts.append(f"\nТекущая тема: {current_topic}")
        context_parts.append("\nПомоги с этим вопросом, учитывая контекст проекта.")
        
        return "\n".join(context_parts)
