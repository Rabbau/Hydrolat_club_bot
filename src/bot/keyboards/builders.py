from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard():
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Подать заявку")]], resize_keyboard=True)
    return kb
