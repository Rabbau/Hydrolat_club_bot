from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from .database import async_session_maker
from .models import User, UserStatus, Questionnaire, QuestionnaireStatus, Question, Answer, Admin
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


async def get_user_questionnaires(telegram_id: int) -> list:
    """Получить все анкеты пользователя."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Questionnaire)
            .join(User)
            .where(User.telegram_id == telegram_id)
            .order_by(desc(Questionnaire.created_at))
            .options(selectinload(Questionnaire.user))
        )
        return result.scalars().all()


async def can_user_create_questionnaire(telegram_id: int) -> tuple[bool, str]:
    """Проверить, может ли пользователь создать анкету."""
    async with async_session_maker() as session:
        # Получаем пользователя
        result = await session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.questionnaires))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return True, ""
        
        # Проверяем анкеты пользователя
        if user.questionnaires:
            # Получаем последнюю анкету
            latest_questionnaire = max(user.questionnaires, key=lambda x: x.created_at)
            
            # Если есть анкета со статусом pending или approved - нельзя создать новую
            if latest_questionnaire.status in [QuestionnaireStatus.pending, QuestionnaireStatus.approved]:
                return False, "У вас уже есть активная анкета. Дождитесь решения по текущей заявке."
            
            # Если последняя анкета отклонена - можно создать новую
            if latest_questionnaire.status == QuestionnaireStatus.rejected:
                return True, "Предыдущая анкета была отклонена. Вы можете подать новую заявку."
        
        return True, "Можно создать анкету"


# ========== ФУНКЦИИ ДЛЯ АДМИНИСТРАТОРОВ ==========

async def get_admin(telegram_id: int) -> Admin | None:
    """Получить администратора по telegram_id."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

async def is_admin(telegram_id: int) -> bool:
    """Проверить, является ли пользователь администратором."""
    admin = await get_admin(telegram_id)
    return admin is not None

async def is_superadmin(telegram_id: int) -> bool:
    """Проверить, является ли пользователь суперадмином (уровень 2)."""
    print(f"🔍 DEBUG is_superadmin: Проверка telegram_id={telegram_id}")
    
    async with async_session_maker() as session:
        stmt = select(Admin).where(
            Admin.telegram_id == telegram_id,
            Admin.level == 2
        )
        result = await session.execute(stmt)
        admin = result.scalar_one_or_none()
        
        print(f"🔍 DEBUG is_superadmin: Найден админ: {admin}")
        return admin is not None

async def get_all_admins() -> list[Admin]:
    """Получить всех администраторов."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Admin).order_by(Admin.level.desc(), Admin.created_at)
        )
        return result.scalars().all()

async def get_admins_with_users() -> list[tuple[Admin, User | None]]:
    """Получить администраторов с информацией о пользователях."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Admin).options(selectinload(Admin.user))
        )
        admins = result.scalars().all()
        
        return [(admin, admin.user) for admin in admins]

async def add_admin(
    telegram_id: int, 
    username: str | None = None, 
    fullname: str | None = None, 
    level: int = 1
) -> tuple[bool, str]:
    """Добавить администратора."""
    async with async_session_maker() as session:
        try:
            # Проверяем, не является ли уже админом
            stmt = select(Admin).where(Admin.telegram_id == telegram_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                return False, "Этот пользователь уже является администратором"
            
            # Находим пользователя в базе (если есть)
            user_stmt = select(User).where(User.telegram_id == telegram_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            # Создаем администратора
            admin = Admin(
                telegram_id=telegram_id,
                username=username,
                fullname=fullname,
                level=level
            )
            
            # Если пользователь найден, связываем
            if user:
                admin.user = user
            
            session.add(admin)
            await session.commit()
            
            return True, f"✅ Пользователь добавлен как администратор (уровень {level})"
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка при добавлении администратора: {e}")
            return False, f"❌ Ошибка: {str(e)}"

async def remove_admin(telegram_id: int, by_superadmin_id: int = None) -> tuple[bool, str]:
    """Удалить администратора."""
    async with async_session_maker() as session:
        try:
            # Находим админа
            stmt = select(Admin).where(Admin.telegram_id == telegram_id)
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()
            
            if not admin:
                return False, "❌ Пользователь не найден среди администраторов"
            
            # Проверяем, не пытаемся ли удалить сами себя
            if by_superadmin_id and telegram_id == by_superadmin_id:
                return False, "❌ Нельзя удалить самого себя"

            # Удаляем
            await session.delete(admin)
            
            # Коммитим изменения
            await session.commit()   
            return True, "✅ Администратор удален"
            
        except Exception as e:
            import traceback
            traceback.print_exc()  # Печатаем полный трейс ошибки
            await session.rollback()
            return False, f"❌ Ошибка: {str(e)}"

async def initialize_superadmin_from_env():
    """Инициализировать суперадмина из .env (если указан)."""
    from src.Config.settings import settings
    
    if settings.superadmin_id:
        async with async_session_maker() as session:
            # Проверяем, существует ли уже
            stmt = select(Admin).where(Admin.telegram_id == settings.superadmin_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                # Находим пользователя (если есть)
                user_stmt = select(User).where(User.telegram_id == settings.superadmin_id)
                user_result = await session.execute(user_stmt)
                user = user_result.scalar_one_or_none()
                
                admin = Admin(
                    telegram_id=settings.superadmin_id,
                    level=2,
                    username=user.username if user else None,
                    fullname=user.fullname if user else None
                )
                
                if user:
                    admin.user = user
                
                session.add(admin)
                await session.commit()

# async def migrate_admins_from_env():
#     """Перенести админов из .env в базу данных."""
#     from src.Config.settings import settings
    
#     if hasattr(settings, 'admin_ids') and settings.admin_ids:
#         async with async_session_maker() as session:
#             for admin_id in settings.admin_ids:
#                 # Проверяем, есть ли уже в базе
#                 stmt = select(Admin).where(Admin.telegram_id == admin_id)
#                 result = await session.execute(stmt)
#                 existing = result.scalar_one_or_none()
                
#                 if not existing:
#                     # Находим пользователя (если есть)
#                     user_stmt = select(User).where(User.telegram_id == admin_id)
#                     user_result = await session.execute(user_stmt)
#                     user = user_result.scalar_one_or_none()
                    
#                     admin = Admin(
#                         telegram_id=admin_id,
#                         level=1,
#                         username=user.username if user else None,
#                         fullname=user.fullname if user else None
#                     )
                    
#                     if user:
#                         admin.user = user
                    
#                     session.add(admin)
            
#             await session.commit()