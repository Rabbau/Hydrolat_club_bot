from typing import Dict, Any, Optional, List
from sqlalchemy import select, and_, desc, update
from .database import get_db_session
from .models import (
    SurveySubmission, SurveyStatusEnum, PaymentPlan, Subscription, 
    SubscriptionStatusEnum, PromoCode, AdminUser, User, BotMessage, BotMessageType
)
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SurveyManager:
    """Менеджер для работы с анкетами"""
    
    async def submit_survey(self, user_id: int, answers: dict) -> bool:
        """Отправить анкету на рассмотрение"""
        async with get_db_session() as session:
            survey = SurveySubmission(
                user_id=user_id,
                answers=answers,
                status=SurveyStatusEnum.PENDING_REVIEW,
            )
            session.add(survey)
            await session.commit()
            logger.info(f"Анкета пользователя {user_id} отправлена на рассмотрение")
            return True
    
    async def get_survey(self, user_id: int) -> Optional[SurveySubmission]:
        """
        Получить последнюю анкету пользователя (по дате создания).
        Оставлена для обратной совместимости.
        """
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission)
                .where(SurveySubmission.user_id == user_id)
                .order_by(desc(SurveySubmission.created_at))
            )
            return result.scalars().first()

    async def get_latest_survey(self, user_id: int) -> Optional[SurveySubmission]:
        """Явный синоним: получить последнюю анкету пользователя."""
        return await self.get_survey(user_id)
    
    async def get_surveys_by_status(self, status: SurveyStatusEnum) -> List[SurveySubmission]:
        """Получить анкеты по статусу"""
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission).where(SurveySubmission.status == status)
            )
            return result.scalars().all()
    
    async def approve_survey(self, survey_id: int, admin_id: int, discount: int = 0) -> bool:
        """Одобрить анкету"""
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission).where(SurveySubmission.id == survey_id)
            )
            survey = result.scalar_one_or_none()
            
            if not survey:
                logger.warning(f"Анкета {survey_id} не найдена")
                return False
            
            survey.status = SurveyStatusEnum.PENDING_PAYMENT
            survey.reviewer_id = admin_id
            survey.personal_discount = discount
            survey.updated_at = datetime.utcnow()
            
            await session.commit()
            logger.info(f"Анкета {survey_id} одобрена администратором {admin_id}")
            return True
    
    async def reject_survey(self, survey_id: int, admin_id: int, comment: str = "") -> bool:
        """Отклонить анкету"""
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission).where(SurveySubmission.id == survey_id)
            )
            survey = result.scalar_one_or_none()
            
            if not survey:
                logger.warning(f"Анкета {survey_id} не найдена")
                return False
            
            survey.status = SurveyStatusEnum.REJECTED
            survey.reviewer_id = admin_id
            survey.reviewer_comment = comment
            survey.updated_at = datetime.utcnow()
            
            await session.commit()
            logger.info(f"Анкета {survey_id} отклонена администратором {admin_id}")
            return True


class PaymentManager:
    """Менеджер для работы с платежами и подписками"""
    
    async def create_payment_plan(self, name: str, duration_days: int, price: float, description: str = "") -> bool:
        """Создать тарифный план"""
        async with get_db_session() as session:
            plan = PaymentPlan(
                name=name,
                duration_days=duration_days,
                price=price,
                description=description
            )
            session.add(plan)
            await session.commit()
            logger.info(f"Тарифный план '{name}' создан")
            return True
    
    async def get_payment_plans(self) -> List[PaymentPlan]:
        """Получить все активные тарифные планы"""
        async with get_db_session() as session:
            result = await session.execute(
                select(PaymentPlan).where(PaymentPlan.is_active == True)
            )
            return result.scalars().all()
    
    async def delete_payment_plan(self, plan_id: int) -> bool:
        """Удалить тарифный план"""
        async with get_db_session() as session:
            result = await session.execute(
                select(PaymentPlan).where(PaymentPlan.id == plan_id)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                return False
            
            plan.is_active = False
            await session.commit()
            logger.info(f"Тарифный план {plan_id} удален")
            return True
    
    async def create_subscription(
        self, 
        user_id: int, 
        plan_id: int, 
        promo_code_id: int = None,
        custom_price: float = None
    ) -> bool:
        """Создать подписку для пользователя"""
        async with get_db_session() as session:
            # Получаем план
            result = await session.execute(
                select(PaymentPlan).where(PaymentPlan.id == plan_id)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                logger.warning(f"План {plan_id} не найден")
                return False
            
            # Вычисляем цену с скидкой
            price = custom_price if custom_price is not None else plan.price
            
            # Рассчитываем даты
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=plan.duration_days)
            
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                start_date=start_date,
                end_date=end_date,
                price_paid=price,
                promo_code_id=promo_code_id,
                status=SubscriptionStatusEnum.ACTIVE
            )
            session.add(subscription)
            await session.commit()
            logger.info(f"Подписка создана для пользователя {user_id}")
            return True
    
    async def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Получить активную подписку пользователя"""
        async with get_db_session() as session:
            result = await session.execute(
                select(Subscription).where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.status == SubscriptionStatusEnum.ACTIVE
                    )
                )
            )
            return result.scalar_one_or_none()


class PromoCodeManager:
    """Менеджер для работы с промокодами"""
    
    async def create_promo_code(
        self,
        code: str,
        discount_percent: int,
        is_collective: bool = True,
        assigned_user_id: int = None,
        max_uses: int = None
    ) -> bool:
        """Создать новый промокод"""
        async with get_db_session() as session:
            promo = PromoCode(
                code=code.upper(),
                discount_percent=discount_percent,
                is_collective=is_collective,
                assigned_user_id=assigned_user_id,
                max_uses=max_uses
            )
            session.add(promo)
            await session.commit()
            logger.info(f"Промокод '{code}' создан с скидкой {discount_percent}%")
            return True
    
    async def get_promo_code(self, code: str) -> Optional[PromoCode]:
        """Получить промокод по коду"""
        async with get_db_session() as session:
            result = await session.execute(
                select(PromoCode).where(
                    and_(
                        PromoCode.code == code.upper(),
                        PromoCode.is_active == True
                    )
                )
            )
            return result.scalar_one_or_none()
    
    async def validate_promo_code(self, code: str, user_id: int) -> Optional[PromoCode]:
        """Проверить промокод и вернуть скидку"""
        promo = await self.get_promo_code(code)
        
        if not promo:
            return None
        
        # Проверяем личный код
        if not promo.is_collective and promo.assigned_user_id != user_id:
            logger.warning(f"Пользователь {user_id} пытается использовать чужой код {code}")
            return None
        
        # Проверяем лимит использований
        if promo.max_uses and promo.current_uses >= promo.max_uses:
            logger.warning(f"Промокод {code} исчерпал лимит использований")
            return None
        
        return promo
    
    async def use_promo_code(self, code: str) -> bool:
        """Отметить промокод как использованный"""
        async with get_db_session() as session:
            result = await session.execute(
                select(PromoCode).where(PromoCode.code == code.upper())
            )
            promo = result.scalar_one_or_none()
            
            if not promo:
                return False
            
            promo.current_uses += 1
            await session.commit()
            return True
    
    async def delete_promo_code(self, code: str) -> bool:
        """Удалить промокод"""
        async with get_db_session() as session:
            result = await session.execute(
                select(PromoCode).where(PromoCode.code == code.upper())
            )
            promo = result.scalar_one_or_none()
            
            if not promo:
                return False
            
            promo.is_active = False
            await session.commit()
            logger.info(f"Промокод {code} удален")
            return True


class AdminManager:
    """Менеджер для работы с администраторами"""
    
    async def add_admin(self, admin_id: int, username: str = None, first_name: str = None, is_super_admin: bool = False) -> bool:
        """Добавить администратора"""
        async with get_db_session() as session:
            # Проверяем, не существует ли уже
            result = await session.execute(
                select(AdminUser).where(AdminUser.id == admin_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.warning(f"Администратор {admin_id} уже существует")
                return False
            
            admin = AdminUser(
                id=admin_id,
                username=username,
                first_name=first_name,
                is_super_admin=is_super_admin
            )
            session.add(admin)
            await session.commit()
            logger.info(f"Администратор {admin_id} добавлен")
            return True
    
    async def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        async with get_db_session() as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.id == user_id)
            )
            return result.scalar_one_or_none() is not None
    
    async def is_super_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь супер-администратором"""
        async with get_db_session() as session:
            result = await session.execute(
                select(AdminUser).where(
                    and_(
                        AdminUser.id == user_id,
                        AdminUser.is_super_admin == True
                    )
                )
            )
            return result.scalar_one_or_none() is not None
    
    async def remove_admin(self, admin_id: int) -> bool:
        """Удалить администратора"""
        async with get_db_session() as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.id == admin_id)
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                return False
            
            await session.delete(admin)
            await session.commit()
            logger.info(f"Администратор {admin_id} удален")
            return True
    
    async def get_all_admins(self) -> List[AdminUser]:
        """Получить всех администраторов"""
        async with get_db_session() as session:
            result = await session.execute(select(AdminUser))
            return result.scalars().all()


class BotMessageManager:
    """Менеджер для работы с управляемыми сообщениями бота"""
    
    async def get_message(self, message_type: BotMessageType) -> Optional[BotMessage]:
        """Получить сообщение по типу"""
        async with get_db_session() as session:
            result = await session.execute(
                select(BotMessage).where(BotMessage.message_type == message_type)
            )
            return result.scalar_one_or_none()
    
    async def get_all_messages(self) -> List[BotMessage]:
        """Получить все сообщения"""
        async with get_db_session() as session:
            result = await session.execute(select(BotMessage))
            return result.scalars().all()
    
    async def init_default_messages(self) -> None:
        """Инициализировать стандартные сообщения при первом запуске"""
        async with get_db_session() as session:
            # Проверяем, существуют ли уже сообщения
            result = await session.execute(select(BotMessage))
            existing = result.scalars().all()
            
            if existing:
                logger.info("Сообщения уже инициализированы")
                return
            
            # Создаем стандартные сообщения
            default_messages = [
                BotMessage(
                    message_type=BotMessageType.WELCOME,
                    content="👋 Добро пожаловать в дискуссионный клуб по гидролатам!\n\n"
                            "Для вступления в наш эксклюзивный клуб, пожалуйста, заполните анкету."
                ),
                BotMessage(
                    message_type=BotMessageType.PAYMENT_DETAILS,
                    content="💳 <b>Реквизиты для оплаты:</b>\n\n"
                            "Номер счета: 12345678901234567890\n"
                            "Получатель: ООО Гидролаты\n"
                            "БИК: 044525225\n\n"
                            "После оплаты, пожалуйста, напишите администратору."
                ),
                BotMessage(
                    message_type=BotMessageType.PAYMENT_CONFIRMED,
                    content="✅ <b>Спасибо за оплату!</b>\n\n"
                            "Ваша подписка активирована. Добро пожаловать в дискуссионный клуб по гидролатам! 🎉"
                ),
                BotMessage(
                    message_type=BotMessageType.SURVEY_REJECTED,
                    content="❌ <b>К сожалению, ваша анкета отклонена.</b>\n\n"
                            "Если у вас есть вопросы, пожалуйста, свяжитесь с администратором."
                )
            ]
            
            for msg in default_messages:
                session.add(msg)
            
            await session.commit()
            logger.info("✅ Стандартные сообщения инициализированы")
    
    async def update_message(self, message_type: BotMessageType, content: str) -> bool:
        """Обновить сообщение"""
        async with get_db_session() as session:
            result = await session.execute(
                select(BotMessage).where(BotMessage.message_type == message_type)
            )
            message = result.scalar_one_or_none()
            
            if not message:
                logger.warning(f"Сообщение {message_type} не найдено")
                return False
            
            message.content = content
            message.updated_at = datetime.utcnow()
            await session.commit()
            logger.info(f"Сообщение {message_type} обновлено")
            return True


# Глобальные экземпляры
survey_manager = SurveyManager()
payment_manager = PaymentManager()
promo_code_manager = PromoCodeManager()
admin_manager = AdminManager()
bot_message_manager = BotMessageManager()