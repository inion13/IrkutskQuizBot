import logging
import random
import os
import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv()
router = Router()

bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher()

# Словарь с вопросами и ответами для викторины
quiz_questions = {
    "Какое национальное блюдо Японии?": ["Суши", "Пицца", "Паста", "Спагетти"],
    "Как называется самая длинная река в мире?": ["Амазонка", "Нил", "Миссисипи", "Янцзы"],
    "Сколько планет в Солнечной системе?": ["Восемь", "Девять", "Семь", "Десять"]
}

# Словарь для отслеживания баллов пользователей
user_scores = {}


@router.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_scores:
        user_scores[user_id] = 0
    await message.reply("Привет! Давайте начнем викторину. Я задам вам несколько вопросов, "
                        "и вы выберете правильный ответ, "
                        "нажимая на соответствующие кнопки.")


@router.callback_query()
async def handle_callback_query(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    question, user_answer = callback_query.data.split("_", maxsplit=1)
    correct_answer = quiz_questions[question][0]

    if user_answer == correct_answer:
        user_scores[user_id] += 1
        await bot.send_message(user_id, f"Правильно! Вы заработали балл. Ваш текущий счет: {user_scores[user_id]}")
    else:
        await bot.send_message(user_id, f"Неправильно! Правильный ответ: {correct_answer}")

    # Задаем следующий вопрос
    await handle_message(callback_query.message)


@router.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    if not quiz_questions:
        await send_quiz_results(message)
        return

    question = random.choice(list(quiz_questions.keys()))
    answers = quiz_questions.pop(question)

    correct_answer = answers[0]  # Правильный ответ всегда первый в списке
    random.shuffle(answers)  # Перемешиваем ответы, чтобы правильный ответ не всегда был первым

    kb = [
        [types.KeyboardButton(text=answers[0], callback_data=f"{question}_{answers[0]}"),
         types.KeyboardButton(text=answers[1], callback_data=f"{question}_{answers[1]}")],
        [types.KeyboardButton(text=answers[2], callback_data=f"{question}_{answers[2]}"),
         types.KeyboardButton(text=answers[3], callback_data=f"{question}_{answers[3]}")]
    ]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=kb)

    await message.reply(f"Вопрос: {question}", reply_markup=keyboard)


@router.message()
async def send_quiz_results(message: types.Message):
    user_id = message.from_user.id
    await message.reply('Поздравляем! Вы завершили викторину.\n'
                        f'Ваш результат: {user_scores[user_id]} баллов.\n'
                        f'Для повторного прохождения викторины нажмите /start',
                        reply_markup=None)

    user_scores[user_id] = 0
    quiz_questions.update({
        "Какое национальное блюдо Японии?": ["Суши", "Пицца", "Паста", "Спагетти"],
        "Как называется самая длинная река в мире?": ["Амазонка", "Нил", "Миссисипи", "Янцзы"],
        "Сколько планет в Солнечной системе?": ["Восемь", "Девять", "Семь", "Десять"],
    })


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
