from aiogram.fsm.state import State, StatesGroup

class Questionnaire(StatesGroup):
    Q1 = State()
    Q2 = State()
    Q3 = State()
