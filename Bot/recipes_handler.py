import aiohttp

import requests

from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.types import Message
from aiogram.utils.formatting import Bold, as_marked_section, as_list
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Router, types

from utils import recipes, translator
from utils import detail

router = Router()


class OrderRecipes(StatesGroup):
    choosing_category = State()
    choosing_recipes = State()


@router.message(StateFilter(None), Command("category_search_random"))
async def suggest_category(message: Message, command: CommandObject, state: FSMContext):
    if command.args is None:
        await message.answer("Ошибка: не переданы аргументы")
        return

    await state.set_data({'count': int(command.args)})

    builder = ReplyKeyboardBuilder()
    response = requests.get('https://www.themealdb.com/api/json/v1/1/list.php?c=list').json()['meals']
    for d in response:
        for v in d.values():
            builder.add(types.KeyboardButton(text=str(v)))
        builder.adjust(4)

    await message.answer(f"Выберите категорию:", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(OrderRecipes.choosing_category)


@router.message(OrderRecipes.choosing_category)
async def suggest_recipes(message: Message, state: FSMContext):
    async with aiohttp.ClientSession() as session:
        title_recipes = await recipes(session, state, message.text)
        response = as_list(
            as_marked_section(
                Bold(f"Как Вам такие варианты:"),
                *[f'{v}' for v in title_recipes]
            ),
        )
        kb = [[types.KeyboardButton(text="Покажи рецепты")]]
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb,
                                             resize_keyboard=True,
                                             )
        await message.answer(**response.as_kwargs(), reply_markup=keyboard)
        await state.set_state(OrderRecipes.choosing_recipes)


@router.message(OrderRecipes.choosing_recipes)
async def send_recipes(message: Message, state: FSMContext):
    async with aiohttp.ClientSession() as session:
        await detail(session, state)

    content = (await state.get_data())['content']
    for dict_recipe in content:
        v = dict_recipe['meals'][0]
        title = (translator.translate(v['strMeal'], dest='ru')).text
        instruction = (translator.translate(v['strInstructions'], dest='ru')).text
        await message.answer(
            f"{title}: {instruction}"
        )
