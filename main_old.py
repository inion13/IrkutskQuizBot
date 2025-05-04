import logging
import random
import os
import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import FSInputFile
from dotenv import load_dotenv

# Импортируем вопросы и факты
from irkutskfacts import facts
from questions import questions

logging.basicConfig(level=logging.INFO)

load_dotenv()

router = Router()

bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher()

# Кнопки
start_button = InlineKeyboardButton(text='Начать', callback_data='start')
fact_button = InlineKeyboardButton(text='Узнать факт', callback_data='fact')
quiz_button = InlineKeyboardButton(text='Начать квиз', callback_data='quiz')
stop_button = InlineKeyboardButton(text='Остановить', callback_data='stop')
start_keyboard = InlineKeyboardMarkup(inline_keyboard=[[start_button]])
confirm_quiz_button = InlineKeyboardButton(text='Начнём!', callback_data='confirm_quiz')
cancel_quiz_button = InlineKeyboardButton(text='Назад', callback_data='cancel_quiz')

confirm_quiz_keyboard = InlineKeyboardMarkup(inline_keyboard=[[confirm_quiz_button, cancel_quiz_button]])

# Основное меню
main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [fact_button, quiz_button],
    [stop_button]
])

# Хранилища состояний и баллов
user_scores = {}  # user_id -> int
user_states = {}  # user_id -> int (индекс вопроса)
user_question_variants = {}  # user_id -> {question_index -> [shuffled options]}
user_question_order = {}  # user_id -> [индексы вопросов]


# Генерация клавиатуры с вариантами ответа

def get_question_keyboard(user_id: int, question_index: int):
    options = questions[question_index]['options'][:]
    random.shuffle(options)
    if user_id not in user_question_variants:
        user_question_variants[user_id] = {}
    user_question_variants[user_id][question_index] = options
    keyboard = [
        [InlineKeyboardButton(text=opt, callback_data=f'quiz_{question_index}_{i}')]
        for i, opt in enumerate(options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_praise(score: int) -> str:
    if score == 5:
        return '🌟 Восхитительно! Все 5 из 5 — ты настоящий знаток Иркутска!'
    elif score == 4:
        return '👏 Отлично! У тебя 4 из 5 — почти идеально!'
    elif score == 3:
        return '👍 Неплохо! 3 из 5 — уже есть базовые знания!'
    elif score == 2:
        return '🙂 Тебе есть над чем поработать.'
    else:
        return '💡 Не расстраивайся! Зато теперь ты знаешь больше об Иркутске!'


@router.message(Command(commands=['start']))
async def start(message: Message):
    await message.answer(
        'Привет! 👋🏻\n\nМеня зовут Квиз-бот ☺️\nЯ могу рассказать тебе интересные факты о городе Иркутске '
        'или предложить пройти квиз.\n\nЧто ты хочешь сделать?',
        reply_markup=main_keyboard
    )


@router.message(Command(commands=['stop']))
async def stop(message: Message):
    await message.answer('Хорошо, если захочешь почитать ещё интересные факты или '
                         'пройти квиз — просто напиши мне!',
                         reply_markup=start_keyboard)


@router.message(Command(commands=['fact']))
async def send_fact(message: Message):
    fact = random.choice(facts)

    if isinstance(fact, dict):
        image_path = fact.get('image')

        if image_path and os.path.exists(image_path):
            image = FSInputFile(image_path)
            await message.answer_photo(
                photo=image,
                caption=fact['text'],
                reply_markup=main_keyboard
            )
        else:
            await message.answer(fact['text'], reply_markup=main_keyboard)
    else:
        await message.answer(fact, reply_markup=main_keyboard)


@router.message(Command(commands=['quiz']))
async def start_quiz_intro(message: Message):
    await message.answer(
        '🧠 Ты собираешься пройти квиз о городе Иркутске.\n\n'
        'Всего будет 5 случайных вопросов. За каждый правильный ответ ты получаешь 1 балл.\n'
        'В конце я подсчитаю, сколько баллов тебе удалось набрать.\nНачнём?',
        reply_markup=confirm_quiz_keyboard
    )


@router.callback_query()
async def handle_callback_query(callback_query: CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    command = callback_query.data
    user_id = callback_query.from_user.id

    if user_id not in user_states:
        user_states[user_id] = 0

    if command == 'start':
        await start(callback_query.message)

    elif command == 'stop':
        await stop(callback_query.message)

    elif command == 'fact':
        await send_fact(callback_query.message)

    elif command == 'quiz':
        await start_quiz_intro(callback_query.message)

    elif command == 'confirm_quiz':
        user_question_order[user_id] = random.sample(range(len(questions)), 5)
        user_states[user_id] = 0
        user_scores[user_id] = 0
        q_index = user_question_order[user_id][0]
        await callback_query.message.answer(
            questions[q_index]['question'], reply_markup=get_question_keyboard(user_id, q_index))

    elif command == 'cancel_quiz':
        await callback_query.message.answer(
            'Хорошо, возвращаю тебя в главное меню 👇', reply_markup=main_keyboard)

    elif command.startswith('quiz_'):
        _, q_index, opt_index = command.split("_")
        q_index = int(q_index)
        opt_index = int(opt_index)
        selected_option = user_question_variants[user_id][q_index][opt_index]
        correct_option = questions[q_index]['answer']

        if selected_option == correct_option:
            user_scores[user_id] += 1
            await callback_query.message.answer('✅ Верно!')
        else:
            await callback_query.message.answer(f'❌ Неверно.\n\nПравильный ответ: {correct_option}')

        user_states[user_id] += 1

        if user_states[user_id] < 5:
            next_q_index = user_question_order[user_id][user_states[user_id]]
            next_q = questions[next_q_index]
            await callback_query.message.answer(
                next_q['question'], reply_markup=get_question_keyboard(user_id, next_q_index))
        else:
            score = user_scores[user_id]
            praise = get_praise(score)
            await callback_query.message.answer(
                f'Квиз завершён! 🎉\nТвой результат: {score} из 5 баллов.\n{praise}', reply_markup=main_keyboard)

            del user_states[user_id]
            del user_scores[user_id]
            del user_question_variants[user_id]
            del user_question_order[user_id]


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
