from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from .database import async_session_maker
from .models import User, UserStatus, Questionnaire, QuestionnaireStatus, Question, Answer
from sqlalchemy import desc 


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    fullname: str | None
) -> User:
    """Найти существующего пользователя или создать нового."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        print(f"Найден существующий пользователь: {user.id}")
        return user
    
    # Создаем нового пользователя
    user = User(
        telegram_id=telegram_id,
        username=username,
        fullname=fullname,
        status=UserStatus.new
    )
    session.add(user)
    await session.flush()  # Получаем ID без коммита
    print(f"Создан новый пользователь: {user.id}")
    return user

async def ensure_questions_exist(session: AsyncSession):
    """Убедиться, что вопросы существуют в базе данных."""
    result = await session.execute(select(Question))
    existing_questions = result.scalars().all()
    
    if existing_questions:
        print(f"В базе уже есть {len(existing_questions)} вопросов")
        return existing_questions
    
    # Создаем стандартные вопросы
    questions_data = [
        {
            "text": "Как давно вы делаете гидролаты?",
            "type": "text",
            "order": 1,
            "is_active": True
        },
        {
            "text": "Сколько видов гидролатов вы делаете?",
            "type": "text",
            "order": 2,
            "is_active": True
        },
        {
            "text": "Почему хотите вступить в клуб?",
            "type": "text",
            "order": 3,
            "is_active": True
        }
    ]
    
    questions = []
    for q_data in questions_data:
        question = Question(**q_data)
        session.add(question)
        questions.append(question)
    
    await session.flush()
    print(f"Создано {len(questions)} вопросов в базе данных")
    return questions

async def save_questionnaire(
    telegram_id: int,
    username: str | None,
    fullname: str | None,
    answers_data: dict
) -> tuple[bool, str]:
    """
    Сохранить анкету пользователя в базу данных.
    
    Возвращает: (успех, сообщение)
    """
    try:
        async with async_session_maker() as session:
            # 1. Найти или создать пользователя
            user = await get_or_create_user(session, telegram_id, username, fullname)
            
            # 2. Убедиться, что вопросы существуют
            questions = await ensure_questions_exist(session)
            
            # 3. Создать анкету
            questionnaire = Questionnaire(
                user_id=user.id,
                status=QuestionnaireStatus.pending
            )
            session.add(questionnaire)
            await session.flush()
            print(f"Создана анкета: {questionnaire.id}")
            
            # 4. Сохранить ответы, сопоставляя с вопросами по порядку
            # answers_data имеет ключи: q1, q2, q3
            for i in range(1, 4):
                answer_key = f'q{i}'
                if answer_key in answers_data:
                    # Находим вопрос с соответствующим order
                    question = next((q for q in questions if q.order == i), None)
                    
                    if question:
                        answer = Answer(
                            questionnaire_id=questionnaire.id,
                            question_id=question.id,
                            answer_text=answers_data[answer_key]
                        )
                        session.add(answer)
                        print(f"Сохранен ответ на вопрос {i}: {answers_data[answer_key][:50]}...")
                    else:
                        print(f"Внимание: не найден вопрос с order={i}")
            
            # 5. Обновить статус пользователя
            user.status = UserStatus.questionnaire_completed
            
            # 6. Коммитим все изменения
            await session.commit()
            
            print(f"✅ Анкета успешно сохранена!")
            print(f"   Пользователь: {user.id}")
            print(f"   Анкета: {questionnaire.id}")
            
            return True, "Анкета успешно сохранена"
            
    except Exception as e:
        print(f"❌ Ошибка при сохранении анкеты: {e}")
        # В случае ошибки откатываем изменения
        return False, f"Ошибка при сохранении: {str(e)}"
    
async def get_statistics() -> dict:
    """Получить статистику для админки."""
    async with async_session_maker() as session:
        # Общая статистика пользователей
        total_users = await session.scalar(select(func.count(User.id)))
        
        # Статистика по статусам пользователей
        user_status_stats = {}
        for status in UserStatus:
            count = await session.scalar(
                select(func.count(User.id)).where(User.status == status)
            )
            user_status_stats[status.value] = count
        
        # Статистика анкет
        total_questionnaires = await session.scalar(select(func.count(Questionnaire.id)))
        
        # Статистика по статусам анкет
        questionnaire_status_stats = {}
        for status in QuestionnaireStatus:
            count = await session.scalar(
                select(func.count(Questionnaire.id)).where(Questionnaire.status == status)
            )
            questionnaire_status_stats[status.value] = count
        
        # За сегодня
        today = datetime.now().date()
        users_today = await session.scalar(
            select(func.count(User.id)).where(func.date(User.created_at) == today)
        )
        
        questionnaires_today = await session.scalar(
            select(func.count(Questionnaire.id)).where(func.date(Questionnaire.created_at) == today)
        )
        
        return {
            "total_users": total_users,
            "new_users": user_status_stats.get("new", 0),
            "questionnaire_completed": user_status_stats.get("questionnaire_completed", 0),
            "member_users": user_status_stats.get("member", 0),
            
            "total_questionnaires": total_questionnaires,
            "pending_count": questionnaire_status_stats.get("pending", 0),
            "approved_count": questionnaire_status_stats.get("approved", 0),
            "rejected_count": questionnaire_status_stats.get("rejected", 0),
            
            "users_today": users_today,
            "questionnaires_today": questionnaires_today,
        }


async def get_pending_questionnaires_count() -> int:
    """Получить количество анкет на модерации."""
    async with async_session_maker() as session:
        count = await session.scalar(
            select(func.count(Questionnaire.id)).where(
                Questionnaire.status == QuestionnaireStatus.pending
            )
        )
        return count or 0


async def get_pending_questionnaires_list(limit: int = 10, offset: int = 0):
    """Получить список анкет на модерации."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Questionnaire)
            .where(Questionnaire.status == QuestionnaireStatus.pending)
            .options(selectinload(Questionnaire.user))
            .order_by(Questionnaire.created_at)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


async def get_questionnaire_details(questionnaire_id: int):
    """Получить детали анкеты с ответами."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Questionnaire)
            .where(Questionnaire.id == questionnaire_id)
            .options(
                selectinload(Questionnaire.user),
                selectinload(Questionnaire.answers).selectinload(Answer.question)
            )
        )
        return result.scalar_one_or_none()

async def approve_questionnaire(questionnaire_id: int) -> tuple[bool, User | None]:
    """Одобрить анкету и изменить статус пользователя."""
    async with async_session_maker() as session:
        try:
            # Получаем анкету с пользователем
            result = await session.execute(
                select(Questionnaire)
                .where(Questionnaire.id == questionnaire_id)
                .options(selectinload(Questionnaire.user))
            )
            questionnaire = result.scalar_one_or_none()
            
            if not questionnaire:
                return False, None
            
            # Обновляем статус анкеты
            questionnaire.status = QuestionnaireStatus.approved
            
            # Обновляем статус пользователя
            questionnaire.user.status = UserStatus.approved
            
            await session.commit()
            return True, questionnaire.user
            
        except Exception as e:
            await session.rollback()
            print(f"Ошибка при одобрении анкеты: {e}")
            return False, None


async def reject_questionnaire(questionnaire_id: int) -> tuple[bool, User | None]:
    """Отклонить анкету и изменить статус пользователя."""
    async with async_session_maker() as session:
        try:
            # Получаем анкету с пользователем
            result = await session.execute(
                select(Questionnaire)
                .where(Questionnaire.id == questionnaire_id)
                .options(selectinload(Questionnaire.user))
            )
            questionnaire = result.scalar_one_or_none()
            
            if not questionnaire:
                return False, None
            
            # Обновляем статус анкеты
            questionnaire.status = QuestionnaireStatus.rejected
            
            # Обновляем статус пользователя
            questionnaire.user.status = UserStatus.rejected
            
            await session.commit()
            return True, questionnaire.user
            
        except Exception as e:
            await session.rollback()
            print(f"Ошибка при отклонении анкеты: {e}")
            return False, None

async def approve_questionnaire(questionnaire_id: int) -> tuple[bool, User | None]:
    """Одобрить анкету и изменить статус пользователя."""
    async with async_session_maker() as session:
        try:
            # Получаем анкету с пользователем
            result = await session.execute(
                select(Questionnaire)
                .where(Questionnaire.id == questionnaire_id)
                .options(selectinload(Questionnaire.user))
            )
            questionnaire = result.scalar_one_or_none()
            
            if not questionnaire:
                return False, None
            
            # Обновляем статус анкеты
            questionnaire.status = QuestionnaireStatus.approved
            
            # Обновляем статус пользователя
            questionnaire.user.status = UserStatus.approved
            
            await session.commit()
            return True, questionnaire.user
            
        except Exception as e:
            await session.rollback()
            print(f"Ошибка при одобрении анкеты: {e}")
            return False, None


async def reject_questionnaire(questionnaire_id: int) -> tuple[bool, User | None]:
    """Отклонить анкету и изменить статус пользователя."""
    async with async_session_maker() as session:
        try:
            # Получаем анкету с пользователем
            result = await session.execute(
                select(Questionnaire)
                .where(Questionnaire.id == questionnaire_id)
                .options(selectinload(Questionnaire.user))
            )
            questionnaire = result.scalar_one_or_none()
            
            if not questionnaire:
                return False, None
            
            # Обновляем статус анкеты
            questionnaire.status = QuestionnaireStatus.rejected
            
            # Обновляем статус пользователя
            questionnaire.user.status = UserStatus.rejected
            
            await session.commit()
            return True, questionnaire.user
            
        except Exception as e:
            await session.rollback()
            print(f"Ошибка при отклонении анкеты: {e}")
            return False, None
        
async def get_approved_questionnaires(limit: int = 10) -> list:
    """Получить одобренные анкеты."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Questionnaire)
            .join(User)
            .where(Questionnaire.status == QuestionnaireStatus.approved)
            .order_by(desc(Questionnaire.created_at))  # Здесь используется desc
            .limit(limit)
            .options(selectinload(Questionnaire.user))
        )
        return result.scalars().all()


async def get_rejected_questionnaires(limit: int = 10) -> list:
    """Получить отклоненные анкеты."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Questionnaire)
            .join(User)
            .where(Questionnaire.status == QuestionnaireStatus.rejected)
            .order_by(desc(Questionnaire.created_at))  # Здесь используется desc
            .limit(limit)
            .options(selectinload(Questionnaire.user))
        )
        return result.scalars().all()