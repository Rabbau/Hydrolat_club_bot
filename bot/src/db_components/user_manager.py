from typing import Dict, Any, Optional, List
from sqlalchemy import select, delete, and_
from .database import get_db_session
from .models import User, UserAnswer
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class UserManager:
    """Асинхронный менеджер пользователей"""
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_index(self, user_id: int) -> Optional[int]:
        """Возвращает индекс пользователя в списке или None"""
        users = await self.get_all_users()
        try:
            return users.index(user_id)
        except ValueError:
            return None
    
    async def add_user(
        self, 
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> None:
        """Добавляет нового пользователя, если его ещё нет"""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user is not None:
                return  # уже существует

            new_user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(new_user)
            await session.commit()
            logger.info(f"Пользователь {user_id} добавлен в БД")
    
    async def add_answer(
        self, 
        user_id: int, 
        question_id: int | str, 
        answer: str
    ) -> bool:
        """
        Добавляет/обновляет ответ пользователя на вопрос.
        Возвращает True если успешно, False если пользователя нет.
        """
        async with get_db_session() as session:
            # Проверяем существование пользователя
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                logger.warning(f"Попытка добавить ответ для несуществующего пользователя {user_id}")
                return False

            # Ищем существующий ответ
            result = await session.execute(
                select(UserAnswer).where(
                    and_(
                        UserAnswer.user_id == user_id,
                        UserAnswer.question_id == str(question_id),
                    )
                )
            )
            existing_answer = result.scalar_one_or_none()

            if existing_answer:
                # Обновляем существующий ответ
                existing_answer.answer = answer
                existing_answer.updated_at = datetime.utcnow()
            else:
                # Создаем новый ответ
                new_answer = UserAnswer(
                    user_id=user_id,
                    question_id=str(question_id),
                    answer=answer,
                )
                session.add(new_answer)

            await session.commit()
            return True
    
    async def get_answers(self, user_id: int) -> Optional[Dict[str, str]]:
        """Возвращает словарь ответов пользователя или None"""
        async with get_db_session() as session:
            # Проверяем существование пользователя
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return None

            result = await session.execute(
                select(UserAnswer).where(UserAnswer.user_id == user_id)
            )
            answers = result.scalars().all()

            return {str(answer.question_id): answer.answer for answer in answers}
    
    async def get_answer(self, user_id: int, question_id: int | str) -> Optional[str]:
        """Получить конкретный ответ пользователя на вопрос"""
        async with get_db_session() as session:
            result = await session.execute(
                select(UserAnswer).where(
                    and_(
                        UserAnswer.user_id == user_id,
                        UserAnswer.question_id == str(question_id),
                    )
                )
            )
            answer = result.scalar_one_or_none()
            return answer.answer if answer else None
    
    async def clear_answers(self, user_id: int) -> bool:
        """Очищает все ответы пользователя"""
        async with get_db_session() as session:
            # Проверяем существование пользователя
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return False

            await session.execute(
                delete(UserAnswer).where(UserAnswer.user_id == user_id)
            )
            await session.commit()
            return True
    
    async def remove_user(self, user_id: int) -> bool:
        """Удаляет пользователя полностью"""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return False

            await session.execute(
                delete(UserAnswer).where(UserAnswer.user_id == user_id)
            )
            await session.delete(user)
            await session.commit()
            logger.info(f"Пользователь {user_id} удален из БД")
            return True
    
    async def get_all_users(self) -> list:
        """Возвращает список всех пользователей (только id)"""
        async with get_db_session() as session:
            result = await session.execute(select(User.id))
            users = result.scalars().all()
            return list(users)
    
    async def get_all_users_with_info(self) -> List[Dict[str, Any]]:
        """Возвращает список всех пользователей с информацией"""
        async with get_db_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            users_list = []
            for user in users:
                # Получаем количество ответов для каждого пользователя
                answers_result = await session.execute(
                    select(UserAnswer).where(UserAnswer.user_id == user.id)
                )
                answers_count = len(answers_result.scalars().all())
                
                users_list.append({
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "created_at": user.created_at,
                    "answers_count": answers_count,
                })
            
            return users_list
    
    async def user_exists(self, user_id: int) -> bool:
        """Проверяет, существует ли пользователь"""
        user = await self.get_user(user_id)
        return user is not None
    
    async def update_user_info(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> bool:
        """Обновляет информацию о пользователе"""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return False

            if username is not None:
                user.username = username
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name

            await session.commit()
            return True
    
    async def get_users_count(self) -> int:
        """Возвращает количество пользователей"""
        async with get_db_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            return len(users)
    
    async def get_answers_count(self, user_id: Optional[int] = None) -> int:
        """Возвращает количество ответов (всех или конкретного пользователя)"""
        async with get_db_session() as session:
            if user_id:
                result = await session.execute(
                    select(UserAnswer).where(UserAnswer.user_id == user_id)
                )
            else:
                result = await session.execute(select(UserAnswer))
            
            answers = result.scalars().all()
            return len(answers)


# Глобальный экземпляр для использования в приложении
user_manager = UserManager()
