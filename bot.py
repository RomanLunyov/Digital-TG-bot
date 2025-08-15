# -*- coding: utf-8 -*-

import logging
import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command

API_TOKEN = '7580490630:AAGqUEnqe0h_-uWsq1NHfVDEBgROinSqGYY'
ADMIN_IDS = [8349596696, 587738183]  # Список Telegram ID админов

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Хранилище товаров: {id: {"name": str, "desc": str, "price": int, "currency": str, "content": str, "pay_url": str, "category": str}}
products = {}
product_id_counter = 1
user_states = {}

main_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="🛍 Каталог")],
    [KeyboardButton(text="🧾 Мои покупки")],
    [KeyboardButton(text="⚙️ Админ-панель")]
])

admin_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="➕ Добавить товар")],
    [KeyboardButton(text="✏️ Изменить цену")],
    [KeyboardButton(text="🗑 Удалить товар")],
    [KeyboardButton(text="⬅️ Назад")]
])

currency_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[
    [KeyboardButton(text="RUB"), KeyboardButton(text="USD"), KeyboardButton(text="EUR")]
])

add_done_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="➕ Добавить ещё товар"), KeyboardButton(text="🏠 В главное меню")]
])

def get_categories():
    return sorted(set(prod["category"] for prod in products.values()))

def get_category_kb():
    cats = get_categories()
    keyboard = [[KeyboardButton(text=cat)] for cat in cats]
    keyboard.append([KeyboardButton(text="➕ Новая категория")])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

@router.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("👋 Добро пожаловать в магазин цифровых товаров!", reply_markup=main_kb)

@router.message(F.text == "🛍 Каталог")
async def show_categories(msg: types.Message):
    cats = get_categories()
    if not cats:
        await msg.answer("Каталог пуст.")
        return
    keyboard = [
        [InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")]
        for cat in cats
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await msg.answer("Выберите категорию:", reply_markup=kb)

@router.callback_query(F.data.startswith("cat_"))
async def show_catalog(call: types.CallbackQuery):
    cat = call.data[4:]
    items = [ (pid, prod) for pid, prod in products.items() if prod["category"] == cat ]
    if not items:
        await call.message.answer("В этой категории нет товаров.")
        await call.answer()
        return
    text = f"🛒 <b>Категория: {cat}</b>\n\n"
    keyboard = [
        [InlineKeyboardButton(text=f"Купить: {prod['name']}", callback_data=f"buy_{pid}")]
        for pid, prod in items
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
    for pid, prod in items:
        text += (
            f"🔹 <b>{prod['name']}</b>\n"
            f"📝 {prod['desc']}\n"
            f"💵 <b>Цена:</b> {prod['price']} {prod['currency']}\n\n"
        )
    await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Доступ запрещён.")
        return
    await msg.answer("Админ-панель:", reply_markup=admin_kb)

@router.message(F.text == "➕ Добавить товар")
async def add_product_start(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Доступ запрещён.")
        return
    user_states[msg.from_user.id] = {"step": "category"}
    await msg.answer("Выберите категорию или создайте новую:", reply_markup=get_category_kb())

@router.message(lambda m: m.from_user.id in ADMIN_IDS and user_states.get(m.from_user.id, {}).get("step") == "category")
async def add_product_category(msg: types.Message):
    if msg.text == "➕ Новая категория":
        user_states[msg.from_user.id]["step"] = "new_category"
        await msg.answer("Введите название новой категории:", reply_markup=types.ReplyKeyboardRemove())
        return
    cats = get_categories()
    if msg.text not in cats:
        await msg.answer("Выберите категорию из списка или создайте новую.", reply_markup=get_category_kb())
        return
    user_states[msg.from_user.id]["category"] = msg.text
    user_states[msg.from_user.id]["step"] = "name"
    await msg.answer("Введите название товара:", reply_markup=types.ReplyKeyboardRemove())

@router.message(lambda m: m.from_user.id in ADMIN_IDS and user_states.get(m.from_user.id, {}).get("step") == "new_category")
async def add_product_new_category(msg: types.Message):
    user_states[msg.from_user.id]["category"] = msg.text
    user_states[msg.from_user.id]["step"] = "name"
    await msg.answer("Введите название товара:")

@router.message(lambda m: m.from_user.id in ADMIN_IDS and user_states.get(m.from_user.id, {}).get("step") == "name")
async def add_product_name(msg: types.Message):
    user_states[msg.from_user.id]["name"] = msg.text
    user_states[msg.from_user.id]["step"] = "desc"
    await msg.answer("Введите краткое описание товара:")

@router.message(lambda m: m.from_user.id in ADMIN_IDS and user_states.get(m.from_user.id, {}).get("step") == "desc")
async def add_product_desc(msg: types.Message):
    user_states[msg.from_user.id]["desc"] = msg.text
    user_states[msg.from_user.id]["step"] = "currency"
    await msg.answer("Выберите валюту товара:", reply_markup=currency_kb)

@router.message(lambda m: m.from_user.id in ADMIN_IDS and user_states.get(m.from_user.id, {}).get("step") == "currency")
async def add_product_currency(msg: types.Message):
    currency = msg.text.upper()
    if currency not in ["RUB", "USD", "EUR"]:
        await msg.answer("Пожалуйста, выберите валюту из предложенных вариантов.", reply_markup=currency_kb)
        return
    user_states[msg.from_user.id]["currency"] = currency
    user_states[msg.from_user.id]["step"] = "price"
    await msg.answer("Введите цену товара (только число):", reply_markup=types.ReplyKeyboardRemove())

@router.message(lambda m: m.from_user.id in ADMIN_IDS and user_states.get(m.from_user.id, {}).get("step") == "price")
async def add_product_price(msg: types.Message):
    try:
        price = int(msg.text)
        user_states[msg.from_user.id]["price"] = price
        user_states[msg.from_user.id]["step"] = "content"
        await msg.answer("Введите цифровой контент (например, ключ, ссылку и т.д.):")
    except ValueError:
        await msg.answer("Введите корректное число.")

@router.message(lambda m: m.from_user.id in ADMIN_IDS and user_states.get(m.from_user.id, {}).get("step") == "content")
async def add_product_content(msg: types.Message):
    user_states[msg.from_user.id]["content"] = msg.text
    user_states[msg.from_user.id]["step"] = "pay_url"
    await msg.answer("Введите ссылку на оплату (например, ЮMoney, Qiwi, PayPal):")

@router.message(lambda m: m.from_user.id in ADMIN_IDS and user_states.get(m.from_user.id, {}).get("step") == "pay_url")
async def add_product_pay_url(msg: types.Message):
    global product_id_counter
    state = user_states[msg.from_user.id]
    products[product_id_counter] = {
        "name": state["name"],
        "desc": state["desc"],
        "price": state["price"],
        "currency": state["currency"],
        "content": state["content"],
        "pay_url": msg.text,
        "category": state["category"]
    }
    save_products()
    await msg.answer(
        f"Товар '{state['name']}' добавлен в каталог!\n\n"
        "Что вы хотите сделать дальше?",
        reply_markup=add_done_kb
    )
    product_id_counter += 1
    user_states.pop(msg.from_user.id)

@router.message(F.text == "➕ Добавить ещё товар")
async def add_product_start_more(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Доступ запрещён.")
        return
    user_states[msg.from_user.id] = {"step": "category"}
    await msg.answer("Выберите категорию или создайте новую:", reply_markup=get_category_kb())

@router.message(F.text == "🏠 В главное меню")
async def back_to_main(msg: types.Message):
    await msg.answer("Главное меню", reply_markup=main_kb)

@router.message(F.text == "⬅️ Назад")
async def back(msg: types.Message):
    await msg.answer("Главное меню", reply_markup=main_kb)

# --- Изменение цены товара ---
@router.message(F.text == "✏️ Изменить цену")
async def change_price_start(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Доступ запрещён.")
        return
    if not products:
        await msg.answer("Нет товаров для изменения.")
        return
    keyboard = [
        [InlineKeyboardButton(text=f"{prod['name']} ({prod['category']})", callback_data=f"editprice_{pid}")]
        for pid, prod in products.items()
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await msg.answer("Выберите товар для изменения цены:", reply_markup=kb)

@router.callback_query(F.data.startswith("editprice_"))
async def change_price_choose(call: types.CallbackQuery):
    pid = int(call.data.split("_")[1])
    prod = products.get(pid)
    if not prod:
        await call.answer("Товар не найден.", show_alert=True)
        return
    user_states[call.from_user.id] = {"step": "edit_price", "pid": pid}
    await call.message.answer(f"Введите новую цену для товара '{prod['name']}':")
    await call.answer()

@router.message(lambda m: m.from_user.id in ADMIN_IDS and user_states.get(m.from_user.id, {}).get("step") == "edit_price")
async def change_price_set(msg: types.Message):
    try:
        price = int(msg.text)
        pid = user_states[msg.from_user.id]["pid"]
        products[pid]["price"] = price
        save_products()
        await msg.answer(f"Цена товара '{products[pid]['name']}' изменена на {price} {products[pid]['currency']}.", reply_markup=admin_kb)
        user_states.pop(msg.from_user.id)
    except Exception:
        await msg.answer("Введите корректное число.")

# --- Удаление товара ---
@router.message(F.text == "🗑 Удалить товар")
async def delete_product_start(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Доступ запрещён.")
        return
    if not products:
        await msg.answer("Нет товаров для удаления.")
        return
    keyboard = [
        [InlineKeyboardButton(text=f"{prod['name']} ({prod['category']})", callback_data=f"deltovar_{pid}")]
        for pid, prod in products.items()
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await msg.answer("Выберите товар для удаления:", reply_markup=kb)

@router.callback_query(F.data.startswith("deltovar_"))
async def delete_product_confirm(call: types.CallbackQuery):
    pid = int(call.data.split("_")[1])
    prod = products.get(pid)
    if not prod:
        await call.answer("Товар не найден.", show_alert=True)
        return
    del products[pid]
    save_products()
    await call.message.answer(f"Товар '{prod['name']}' удалён.", reply_markup=admin_kb)
    await call.answer("Удалено.")

# --- Покупка и подтверждение ---
user_purchases = {}

@router.callback_query(F.data.startswith("buy_"))
async def buy_product(call: types.CallbackQuery):
    pid = int(call.data.split("_")[1])
    prod = products.get(pid)
    if not prod:
        await call.answer("Товар не найден.", show_alert=True)
        return
    await call.message.answer(
        f"Для покупки товара <b>{prod['name']}</b> ({prod['desc']}) оплатите {prod['price']} {prod['currency']} по ссылке:\n{prod['pay_url']}\n\n"
        "После оплаты пришлите сюда скриншот чека или номер транзакции.",
        parse_mode="HTML"
    )
    user_states[call.from_user.id] = {"waiting_payment": pid}
    await call.answer()

pending_payments = {}  # user_id: {"pid": int, "photo_id": str, "message_id": int}

@router.message(F.content_type == types.ContentType.PHOTO)
async def handle_payment_proof(msg: types.Message):
    state = user_states.get(msg.from_user.id)
    if state and "waiting_payment" in state:
        pid = state["waiting_payment"]
        prod = products.get(pid)
        if prod:
            pending_payments[msg.from_user.id] = {
                "pid": pid,
                "photo_id": msg.photo[-1].file_id,
                "message_id": msg.message_id
            }
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{msg.from_user.id}_{pid}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_{msg.from_user.id}_{pid}")
            )
            for admin_id in ADMIN_IDS:
                await bot.send_photo(
                    admin_id,
                    msg.photo[-1].file_id,
                    caption=(
                        f"Поступил чек на оплату!\n"
                        f"Пользователь: @{msg.from_user.username or msg.from_user.id}\n"
                        f"Товар: {prod['name']} ({prod['desc']})\n"
                        f"Цена: {prod['price']} {prod['currency']}\n"
                        f"User ID: {msg.from_user.id}"
                    ),
                    reply_markup=kb
                )
            await msg.answer("Чек отправлен на проверку админу. Ожидайте подтверждения.")
        else:
            await msg.answer("Ошибка: товар не найден.")
    else:
        await msg.answer("Вы не совершали покупку. Для покупки выберите товар в каталоге.")

@router.callback_query(lambda c: c.data.startswith("approve_") or c.data.startswith("decline_"))
async def process_payment_decision(call: types.CallbackQuery):
    action, user_id, pid = call.data.split("_")
    user_id = int(user_id)
    pid = int(pid)
    prod = products.get(pid)
    if not prod:
        await call.answer("Товар не найден.", show_alert=True)
        return

    if action == "approve":
        user_purchases.setdefault(user_id, []).append(prod)
        user_states.pop(user_id, None)
        pending_payments.pop(user_id, None)
        await bot.send_message(
            user_id,
            f"✅ Оплата подтверждена администратором!\nВот ваш товар:\n\n<code>{prod['content']}</code>",
            parse_mode="HTML"
        )
        try:
            await call.message.edit_caption(call.message.caption + "\n\n✅ Оплата подтверждена. Товар выдан.", reply_markup=None)
        except Exception:
            pass
        await call.answer("Покупка подтверждена.")
    elif action == "decline":
        user_states.pop(user_id, None)
        pending_payments.pop(user_id, None)
        await bot.send_message(
            user_id,
            "❌ Оплата не подтверждена администратором. Если вы считаете это ошибкой, свяжитесь с поддержкой."
        )
        try:
            await call.message.edit_caption(call.message.caption + "\n\n❌ Оплата отклонена.", reply_markup=None)
        except Exception:
            pass
        await call.answer("Покупка отклонена.")

@router.message(F.text == "🧾 Мои покупки")
async def my_purchases(msg: types.Message):
    items = user_purchases.get(msg.from_user.id, [])
    if not items:
        await msg.answer("У вас нет покупок.")
        return
    text = "🧾 <b>Ваши покупки:</b>\n\n"
    for i, prod in enumerate(items, 1):
        text += f"{i}. <b>{prod['name']}</b> ({prod['desc']}) — <code>{prod['content']}</code>\n"
    await msg.answer(text, parse_mode="HTML")

CATALOG_FILE = "products.json"

def save_products():
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def load_products():
    global products, product_id_counter
    if os.path.exists(CATALOG_FILE):
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            products.update({int(k): v for k, v in loaded.items()})
        if products:
            product_id_counter = max(products.keys()) + 1

async def main():
    load_products()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())