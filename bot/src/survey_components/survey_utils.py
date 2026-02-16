from aiogram.types import Message, CallbackQuery
from src.FormManager.FormManager import FormManager
from src.survey_components.survey_keyboards import (survey_menu_inline_keyboard as kb_survey,
                                                    survey_menu_inline_keyboard_empty as kb_survey_empty)

async def show_survey_menu(callback: CallbackQuery, form: FormManager):
    form_text = await form.get_form_for_admin()
    if form_text == 'Анкета пуста':
        await callback.message.edit_text(
            text=f'Меню анкеты:\n\n' + f'{form_text}',
            reply_markup=kb_survey_empty
        )
    else:
        await callback.message.edit_text(
            text=f'Меню анкеты:\n\n' + f'{form_text}',
            reply_markup=kb_survey
            )
    await callback.answer()

async def survey_int_validator(message: Message):
    try:
        return int(message.text.strip())
    except ValueError:
        await message.answer("Нужно ввести число (номер вопроса). Попробуй ещё раз.")
        return
