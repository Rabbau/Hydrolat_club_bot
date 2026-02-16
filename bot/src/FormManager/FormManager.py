from typing import Any, Dict, Optional

from sqlalchemy import func, select

from src.db_components.database import get_db_session
from src.db_components.models import SurveyQuestion


class FormManager:
    """Manager for survey questions stored in PostgreSQL."""

    async def _get_next_position(self) -> int:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveyQuestion).order_by(SurveyQuestion.position.desc())
            )
            last = result.scalars().first()
            return (last.position + 1) if last else 1

    async def create(self) -> None:
        """Backward-compatible noop: schema is managed by migrations."""
        return

    async def add_question(self, text: str, question_type: str = "text") -> int:
        position = await self._get_next_position()
        async with get_db_session() as session:
            question = SurveyQuestion(
                position=position,
                text=text.strip(),
                question_type=question_type.strip(),
            )
            session.add(question)
        return position

    async def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveyQuestion).where(SurveyQuestion.position == question_id)
            )
            question = result.scalar_one_or_none()
            if not question:
                return None
            return {
                "id": question.position,
                "text": question.text,
                "type": question.question_type,
            }

    async def edit_question(
        self,
        question_id: int,
        new_text: Optional[str] = None,
        new_type: Optional[str] = None,
    ) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveyQuestion).where(SurveyQuestion.position == question_id)
            )
            question = result.scalar_one_or_none()
            if not question:
                return False

            if new_text is not None:
                question.text = new_text.strip()
            if new_type is not None:
                question.question_type = new_type.strip()
            return True

    async def delete_question(self, question_id: int) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveyQuestion).where(SurveyQuestion.position == question_id)
            )
            target = result.scalar_one_or_none()
            if not target:
                return False

            await session.delete(target)

            result = await session.execute(
                select(SurveyQuestion)
                .where(SurveyQuestion.position > question_id)
                .order_by(SurveyQuestion.position.asc())
            )
            for question in result.scalars().all():
                question.position -= 1
            return True

    async def get_form_for_admin(self) -> str:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveyQuestion).order_by(SurveyQuestion.position.asc())
            )
            questions = result.scalars().all()

        if not questions:
            return "Анкета пуста"

        lines = [f"#{q.position} {q.text} ({q.question_type})" for q in questions]
        return "\n".join(lines)

    async def clear(self) -> None:
        async with get_db_session() as session:
            result = await session.execute(select(SurveyQuestion))
            for question in result.scalars().all():
                await session.delete(question)

    async def get_questions_count(self) -> int:
        async with get_db_session() as session:
            result = await session.execute(select(func.count()).select_from(SurveyQuestion))
            return int(result.scalar_one())
