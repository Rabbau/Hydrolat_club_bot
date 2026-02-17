from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, desc, func, select

from .database import get_db_session
from .models import (
    AdminUser,
    BotMessage,
    BotMessageType,
    PaymentPlan,
    PromoCode,
    Subscription,
    SubscriptionStatusEnum,
    SurveyStatusEnum,
    SurveySubmission,
)


class SurveyManager:
    async def submit_survey(self, user_id: int, answers: dict) -> bool:
        async with get_db_session() as session:
            survey = SurveySubmission(
                user_id=user_id,
                answers=answers,
                status=SurveyStatusEnum.PENDING_REVIEW,
            )
            session.add(survey)
            return True

    async def get_survey(self, user_id: int) -> Optional[SurveySubmission]:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission)
                .where(SurveySubmission.user_id == user_id)
                .order_by(desc(SurveySubmission.created_at))
            )
            return result.scalars().first()

    async def get_latest_survey(self, user_id: int) -> Optional[SurveySubmission]:
        return await self.get_survey(user_id)

    async def get_surveys_by_status(self, status: SurveyStatusEnum) -> List[SurveySubmission]:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission).where(SurveySubmission.status == status)
            )
            return result.scalars().all()

    async def approve_survey(self, survey_id: int, admin_id: int, discount: int = 0) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission).where(SurveySubmission.id == survey_id)
            )
            survey = result.scalar_one_or_none()
            if not survey:
                return False

            survey.status = SurveyStatusEnum.PENDING_PAYMENT
            survey.reviewer_id = admin_id
            survey.personal_discount = discount
            survey.updated_at = datetime.utcnow()
            return True

    async def reject_survey(self, survey_id: int, admin_id: int, comment: str = "") -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission).where(SurveySubmission.id == survey_id)
            )
            survey = result.scalar_one_or_none()
            if not survey:
                return False

            survey.status = SurveyStatusEnum.REJECTED
            survey.reviewer_id = admin_id
            survey.reviewer_comment = comment
            survey.updated_at = datetime.utcnow()
            return True

    async def apply_promo_code_to_latest_survey(
        self, user_id: int, code: str
    ) -> tuple[bool, str, int]:
        promo = await promo_code_manager.validate_promo_code(code, user_id)
        if not promo:
            return False, "Промокод недействителен или недоступен", 0

        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission)
                .where(SurveySubmission.user_id == user_id)
                .order_by(desc(SurveySubmission.created_at))
            )
            survey = result.scalars().first()
            if not survey:
                return False, "Сначала заполните анкету", 0
            if survey.status in (SurveyStatusEnum.PAID, SurveyStatusEnum.REJECTED):
                return False, "Для этой анкеты промокод уже нельзя применить", 0

            survey.promo_code_id = promo.id
            survey.promo_discount = promo.discount_percent
            survey.updated_at = datetime.utcnow()

        return True, f"Промокод применен: скидка {promo.discount_percent}%", promo.discount_percent

    async def get_status_counts(self) -> Dict[str, int]:
        async with get_db_session() as session:
            result = await session.execute(
                select(SurveySubmission.status, func.count()).group_by(SurveySubmission.status)
            )
            rows = result.all()

        counts: Dict[str, int] = {
            SurveyStatusEnum.PENDING_REVIEW: 0,
            SurveyStatusEnum.PENDING_PAYMENT: 0,
            SurveyStatusEnum.PAID: 0,
            SurveyStatusEnum.REJECTED: 0,
            SurveyStatusEnum.APPROVED: 0,
        }
        for status, count in rows:
            counts[str(status)] = int(count)
        return counts


class PaymentManager:
    async def create_payment_plan(
        self, name: str, duration_days: int, price: float, description: str = ""
    ) -> bool:
        async with get_db_session() as session:
            plan = PaymentPlan(
                name=name,
                duration_days=duration_days,
                price=price,
                description=description,
            )
            session.add(plan)
            return True

    async def get_payment_plans(self) -> List[PaymentPlan]:
        async with get_db_session() as session:
            result = await session.execute(
                select(PaymentPlan).where(PaymentPlan.is_active == True)
            )
            return result.scalars().all()

    async def delete_payment_plan(self, plan_id: int) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(PaymentPlan).where(PaymentPlan.id == plan_id)
            )
            plan = result.scalar_one_or_none()
            if not plan:
                return False
            plan.is_active = False
            return True

    async def create_subscription(
        self,
        user_id: int,
        plan_id: int,
        promo_code_id: int = None,
        custom_price: float = None,
    ) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(PaymentPlan).where(PaymentPlan.id == plan_id)
            )
            plan = result.scalar_one_or_none()
            if not plan:
                return False

            price = custom_price if custom_price is not None else plan.price
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=plan.duration_days)
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                start_date=start_date,
                end_date=end_date,
                price_paid=price,
                promo_code_id=promo_code_id,
                status=SubscriptionStatusEnum.ACTIVE,
            )
            session.add(subscription)
            return True

    async def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        async with get_db_session() as session:
            result = await session.execute(
                select(Subscription).where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.status == SubscriptionStatusEnum.ACTIVE,
                    )
                )
            )
            return result.scalar_one_or_none()

    async def get_active_subscriptions(self) -> List[Subscription]:
        async with get_db_session() as session:
            result = await session.execute(
                select(Subscription).where(
                    Subscription.status == SubscriptionStatusEnum.ACTIVE
                )
            )
            return result.scalars().all()


class PromoCodeManager:
    async def create_promo_code(
        self,
        code: str,
        discount_percent: int,
        is_collective: bool = True,
        assigned_user_id: int = None,
        max_uses: int = None,
    ) -> bool:
        async with get_db_session() as session:
            promo = PromoCode(
                code=code.upper(),
                discount_percent=discount_percent,
                is_collective=is_collective,
                assigned_user_id=assigned_user_id,
                max_uses=max_uses,
            )
            session.add(promo)
            return True

    async def get_promo_code(self, code: str) -> Optional[PromoCode]:
        async with get_db_session() as session:
            result = await session.execute(
                select(PromoCode).where(
                    and_(PromoCode.code == code.upper(), PromoCode.is_active == True)
                )
            )
            return result.scalar_one_or_none()

    async def validate_promo_code(self, code: str, user_id: int) -> Optional[PromoCode]:
        promo = await self.get_promo_code(code)
        if not promo:
            return None
        if not promo.is_collective and promo.assigned_user_id != user_id:
            return None
        if promo.max_uses and promo.current_uses >= promo.max_uses:
            return None
        return promo

    async def use_promo_code(self, code: str) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(PromoCode).where(PromoCode.code == code.upper())
            )
            promo = result.scalar_one_or_none()
            if not promo:
                return False
            promo.current_uses += 1
            return True

    async def use_promo_code_by_id(self, promo_code_id: int) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(PromoCode).where(PromoCode.id == promo_code_id)
            )
            promo = result.scalar_one_or_none()
            if not promo:
                return False
            promo.current_uses += 1
            return True

    async def delete_promo_code(self, code: str) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(PromoCode).where(PromoCode.code == code.upper())
            )
            promo = result.scalar_one_or_none()
            if not promo:
                return False
            promo.is_active = False
            return True


class AdminManager:
    async def add_admin(
        self,
        admin_id: int,
        username: str = None,
        first_name: str = None,
        is_super_admin: bool = False,
    ) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.id == admin_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return False
            admin = AdminUser(
                id=admin_id,
                username=username,
                first_name=first_name,
                is_super_admin=is_super_admin,
            )
            session.add(admin)
            return True

    async def is_admin(self, user_id: int) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.id == user_id)
            )
            return result.scalar_one_or_none() is not None

    async def is_super_admin(self, user_id: int) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(AdminUser).where(
                    and_(AdminUser.id == user_id, AdminUser.is_super_admin == True)
                )
            )
            return result.scalar_one_or_none() is not None

    async def remove_admin(self, admin_id: int) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.id == admin_id)
            )
            admin = result.scalar_one_or_none()
            if not admin:
                return False
            await session.delete(admin)
            return True

    async def get_all_admins(self) -> List[AdminUser]:
        async with get_db_session() as session:
            result = await session.execute(select(AdminUser))
            return result.scalars().all()


class BotMessageManager:
    async def get_message(self, message_type: BotMessageType) -> Optional[BotMessage]:
        async with get_db_session() as session:
            result = await session.execute(
                select(BotMessage).where(BotMessage.message_type == message_type)
            )
            return result.scalar_one_or_none()

    async def get_all_messages(self) -> List[BotMessage]:
        async with get_db_session() as session:
            result = await session.execute(select(BotMessage))
            return result.scalars().all()

    async def init_default_messages(self) -> None:
        default_messages = [
            (
                BotMessageType.WELCOME,
                "👋 Добро пожаловать в дискуссионный клуб по гидролатам!\n\n"
                "Для вступления заполните анкету.",
            ),
            (
                BotMessageType.PAYMENT_DETAILS,
                "💳 <b>Реквизиты для оплаты:</b>\n\n"
                "Номер счета: 12345678901234567890\n"
                "Получатель: ООО Гидролаты\n"
                "БИК: 044525225\n\n"
                "После оплаты напишите администратору.",
            ),
            (
                BotMessageType.PAYMENT_CONFIRMED,
                "✅ <b>Спасибо за оплату!</b>\n\n"
                "Ваша подписка активирована. Добро пожаловать в клуб!",
            ),
            (
                BotMessageType.SURVEY_REJECTED,
                "❌ <b>К сожалению, ваша анкета отклонена.</b>\n\n"
                "Если есть вопросы, свяжитесь с администратором.",
            ),
            (
                BotMessageType.SURVEY_SUBMITTED,
                "Анкета отправлена на рассмотрение.\n\nСледите за статусом через кнопку «Статус профиля».",
            ),
            (
                BotMessageType.STATUS_EMPTY,
                "Анкета еще не заполнена.",
            ),
            (
                BotMessageType.PROMO_APPLIED,
                "✅ {text}",
            ),
            (
                BotMessageType.PROMO_INVALID,
                "❌ {text}",
            ),
            (
                BotMessageType.TARIFFS_HEADER,
                "<b>Доступные тарифы</b>",
            ),
        ]

        async with get_db_session() as session:
            for message_type, content in default_messages:
                result = await session.execute(
                    select(BotMessage).where(BotMessage.message_type == message_type)
                )
                existing = result.scalar_one_or_none()
                if existing is None:
                    session.add(BotMessage(message_type=message_type, content=content))

    async def update_message(self, message_type: BotMessageType, content: str) -> bool:
        async with get_db_session() as session:
            result = await session.execute(
                select(BotMessage).where(BotMessage.message_type == message_type)
            )
            message = result.scalar_one_or_none()
            if message is None:
                session.add(BotMessage(message_type=message_type, content=content))
                return True

            message.content = content
            message.updated_at = datetime.utcnow()
            return True


survey_manager = SurveyManager()
payment_manager = PaymentManager()
promo_code_manager = PromoCodeManager()
admin_manager = AdminManager()
bot_message_manager = BotMessageManager()
