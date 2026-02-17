from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.FormManager.FormManager import FormManager
from src.admin_components.admin_callbacks import AdminAction, AdminCallback
from src.admin_components.admin_utils import show_admin_main_menu
from src.survey_components.survey_callbacks import SurveyAction, SurveyCallback
from src.survey_components.survey_keyboards import (
    survey_menu_add_question_or_back_inline_keyboard as add_or_back_kb,
    survey_menu_back_inline_keyboard as back_kb,
    survey_menu_edit_back_or_next_inline_keyboard as back_or_next_kb,
    survey_menu_question_type_inline_keyboard as question_type_kb,
)
from src.survey_components.survey_states import SurveyFSM
from src.survey_components.survey_utils import show_survey_menu, survey_int_validator

survey_router = Router(name="survey_router")


@survey_router.callback_query(AdminCallback.filter(F.action == AdminAction.SURVEY_BACK))
async def survey_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_admin_main_menu(callback)


@survey_router.callback_query(SurveyCallback.filter(F.action == SurveyAction.BACK))
async def survey_menu_elements_back(
    callback: CallbackQuery, state: FSMContext, form: FormManager
):
    await state.clear()
    await show_survey_menu(callback, form)


@survey_router.callback_query(SurveyCallback.filter(F.action == SurveyAction.ADD_QUESTION))
async def add_question_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SurveyFSM.add_question)
    await callback.message.edit_text(
        text="Введите текст нового вопроса:",
        reply_markup=back_kb,
    )
    await callback.answer()


@survey_router.message(SurveyFSM.add_question)
async def add_question_type(message: Message, state: FSMContext):
    await state.update_data(add_question=message.text)
    await message.answer(text="Выберите тип ответа для вопроса:", reply_markup=question_type_kb)


@survey_router.callback_query(SurveyFSM.add_question, F.data.startswith("type:"))
async def add_question_process(
    callback: CallbackQuery, state: FSMContext, form: FormManager
):
    await state.update_data(add_question_type=callback.data)
    data = await state.get_data()
    question_text = data.get("add_question")
    question_type = data.get("add_question_type").split(":", 1)[1]
    await form.add_question(question_text, question_type)
    await callback.message.edit_text(
        text=f"Вопрос добавлен:\n\n{question_text}\n\nТип ответа: {question_type}",
        reply_markup=add_or_back_kb,
    )
    await state.clear()
    await callback.answer()


@survey_router.callback_query(SurveyCallback.filter(F.action == SurveyAction.DELETE_QUESTION))
async def delete_question_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SurveyFSM.delete_question)
    await callback.message.answer(
        text="Введите номер вопроса, который нужно удалить:",
        reply_markup=back_kb,
    )
    await callback.answer()


@survey_router.message(SurveyFSM.delete_question)
async def delete_question_process(message: Message, state: FSMContext, form: FormManager):
    if not message.text:
        await message.answer("Отправьте номер вопроса цифрами, например: 2")
        return

    question_id = await survey_int_validator(message)
    if question_id is None:
        return

    if await form.delete_question(question_id):
        await message.answer(
            text=f"Вопрос №{question_id} удален.",
            reply_markup=back_kb,
        )
    else:
        await message.answer(
            text=f"Вопрос №{question_id} не найден. Проверьте номер и попробуйте снова.",
            reply_markup=back_kb,
        )
    await state.clear()


@survey_router.callback_query(SurveyCallback.filter(F.action == SurveyAction.EDIT_QUESTION))
async def edit_question_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SurveyFSM.edit_question_id)
    await callback.message.edit_text(
        text="Введите номер вопроса для редактирования:",
        reply_markup=back_kb,
    )
    await callback.answer()


@survey_router.message(SurveyFSM.edit_question_id)
async def edit_question_id(message: Message, state: FSMContext, form: FormManager):
    question_id = await survey_int_validator(message)
    if question_id is None:
        return
    if not await form.get_question_by_id(question_id):
        await message.answer(
            text=f"Вопрос №{question_id} не найден. Попробуйте еще раз.",
            reply_markup=back_kb,
        )
        return
    await state.update_data(edit_question_id=question_id)
    await state.set_state(SurveyFSM.edit_question_text)
    await message.answer(
        text="Введите новый текст вопроса:",
        reply_markup=back_or_next_kb,
    )


@survey_router.callback_query(
    SurveyFSM.edit_question_text,
    SurveyCallback.filter(F.action == SurveyAction.QUESTION_TYPE),
)
async def skip_edit_question_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SurveyFSM.edit_question_type)
    await callback.message.edit_text(
        text="Выберите новый тип ответа:",
        reply_markup=question_type_kb,
    )
    await callback.answer()


@survey_router.message(SurveyFSM.edit_question_text)
async def edit_question_text(message: Message, state: FSMContext):
    await state.update_data(new_question_text=message.text)
    await state.set_state(SurveyFSM.edit_question_type)
    await message.answer(
        text="Выберите тип ответа:",
        reply_markup=question_type_kb,
    )


@survey_router.callback_query(SurveyFSM.edit_question_type, F.data.startswith("type:"))
async def edit_question_process(
    callback: CallbackQuery, state: FSMContext, form: FormManager
):
    data = await state.get_data()
    new_type = callback.data.split(":", 1)[1]
    await form.edit_question(
        question_id=data.get("edit_question_id"),
        new_text=data.get("new_question_text"),
        new_type=new_type,
    )
    await callback.message.edit_text(
        text=f"Вопрос №{data['edit_question_id']} успешно обновлен.",
        reply_markup=back_kb,
    )
    await state.clear()
    await callback.answer()
