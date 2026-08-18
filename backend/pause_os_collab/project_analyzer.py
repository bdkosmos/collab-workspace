"""
ProjectAnalyzer - анализатор проектов
Анализирует контент проекта и предоставляет инсайты
"""

import re
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    """Результат анализа проекта"""
    themes: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    key_elements: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    suggestions: List[str] = field(default_factory=list)
    word_count: int = 0
    reading_time_minutes: int = 0


class ProjectAnalyzer:
    """Анализирует проекты и предоставляет рекомендации"""
    
    def __init__(self):
        self.sentiment_keywords = {
            "positive": ["отлично", "хорошо", "прекрасно", "вдохновение", "успех", "радость", "любовь"],
            "negative": ["плохо", "проблема", "ошибка", "трудность", "неудача", "грусть"],
        }
    
    def analyze(self, content: str) -> AnalysisResult:
        """Полный анализ контента проекта"""
        return AnalysisResult(
            themes=self._extract_themes(content),
            sentiment=self._analyze_sentiment(content),
            key_elements=self._extract_key_elements(content),
            complexity_score=self._calculate_complexity(content),
            suggestions=self._generate_suggestions(content),
            word_count=len(content.split()),
            reading_time_minutes=max(1, len(content.split()) // 200)
        )
    
    def _extract_themes(self, content: str) -> List[str]:
        """Извлекает основные темы из текста"""
        content_lower = content.lower()
        themes = []
        
        theme_indicators = {
            "творчество": ["творчество", "искусство", "вдохновение", "креатив"],
            "технологии": ["технология", "код", "программирование", "digital"],
            "бизнес": ["бизнес", "продукт", "рынок", "клиент", "продажи"],
            "образование": ["обучение", "курс", "знания", "навыки"],
            "здоровье": ["здоровье", "спорт", "фитнес", "питание"],
            "путешествия": ["путешествие", "поездка", "туризм", "отдых"],
        }
        
        for theme, keywords in theme_indicators.items():
            if any(kw in content_lower for kw in keywords):
                themes.append(theme)
        
        return themes if themes else ["общая тема"]
    
    def _analyze_sentiment(self, content: str) -> str:
        """Анализ тональности текста"""
        content_lower = content.lower()
        positive_count = sum(1 for word in self.sentiment_keywords["positive"] if word in content_lower)
        negative_count = sum(1 for word in self.sentiment_keywords["negative"] if word in content_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"
    
    def _extract_key_elements(self, content: str) -> List[str]:
        """Извлекает ключевые элементы (заголовки, важные фразы)"""
        headers = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
        bold_text = re.findall(r'\*\*(.+?)\*\*', content)
        
        elements = headers + bold_text
        return elements[:10]  # Максимум 10 элементов
    
    def _calculate_complexity(self, content: str) -> float:
        """Рассчитывает сложность текста (0-100)"""
        words = content.split()
        if not words:
            return 0.0
        
        avg_word_length = sum(len(w) for w in words) / len(words)
        sentences = len(re.split(r'[.!?]+', content))
        avg_sentence_length = len(words) / max(1, sentences)
        
        # Формула сложности
        complexity = min(100, (avg_word_length * 5) + (avg_sentence_length * 2))
        return round(complexity, 1)
    
    def _generate_suggestions(self, content: str) -> List[str]:
        """Генерирует предложения по улучшению"""
        suggestions = []
        content_lower = content.lower()
        
        if len(content.split()) < 100:
            suggestions.append("Добавьте больше деталей и описаний")
        
        if "?" not in content:
            suggestions.append("Задайте вопросы аудитории для вовлечения")
        
        if not any(char.isdigit() for char in content):
            suggestions.append("Добавьте конкретные данные или примеры")
        
        if len(re.findall(r'!+', content)) > 5:
            suggestions.append("Используйте восклицательные знаки умеренно")
        
        if not suggestions:
            suggestions.append("Контент выглядит сбалансированным!")
        
        return suggestions
    
    def quick_summary(self, content: str) -> str:
        """Быстрое резюме проекта"""
        analysis = self.analyze(content)
        return f"Темы: {', '.join(analysis.themes)} | Слов: {analysis.word_count} | Сложность: {analysis.complexity_score}/100"
