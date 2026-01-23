from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .database import async_session_maker
from .models import User, UserStatus, Questionnaire, QuestionnaireStatus, Question, Answer

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