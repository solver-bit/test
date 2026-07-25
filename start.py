import asyncio
import logging
import re
import json
import aiohttp
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN

# Настройки твоего проекта

ADMIN_ID = 8636218954
STATIC_WEBAPP_URL = "https://solver-bit.github.io/test/"  # Твой GitHub Pages

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()


class AdminStates(StatesGroup):
    waiting_for_price = State()
    waiting_for_new_name = State()
    waiting_for_new_price = State()


# Стартовый каталог, если в облаке Telegram еще совсем пусто
DEFAULT_CATALOG = [
    {"id": 1, "name": "Комплект оптики (Тип А)", "price": 1200.0},
    {"id": 2, "name": "Комплект оптики (Тип Б)", "price": 850.0},
    {"id": 3, "name": "Модуль доп. тюнинга", "price": 450.0},
    {"id": 4, "name": "Спойлер карбоновый", "price": 600.0},
    {"id": 5, "name": "Выхлопная система Спорт", "price": 2100.0}
]


# 🌌 ХАКЕРСКИЙ МЕТОД: Бот отправляет данные напрямую в CloudStorage твоего Mini App!
async def save_to_telegram_cloud(catalog_data: list):
    """Отправляет обновленный массив товаров в сервера Telegram CloudStorage"""
    # Переводим наш список товаров в текстовую строку JSON
    json_str = json.dumps(catalog_data)

    # Официальный URL Bot API для записи данных в CloudStorage приложения
    url = f"https://telegram.org{BOT_TOKEN}/setCloudStorage"
    payload = {
        "user_id": ADMIN_ID,
        "keys": ["nexus_catalog"],
        "values": [json_str]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            res = await response.json()
            if res.get("ok"):
                print("[NEXUS CLOUD] Каталог успешно синхронизирован с серверами Telegram!")
            else:
                print(f"[NEXUS CLOUD ERROR] Ошибка синхронизации: {res}")


@router.message(Command("start"))
async def start_cmd(message: types.Message):
    if not message or not message.from_user: return
    buttons = [[KeyboardButton(text="🛍️ Открыть витрину NEXUS", web_app=WebAppInfo(url=STATIC_WEBAPP_URL))]]
    if message.from_user.id == ADMIN_ID:
        buttons.append([KeyboardButton(text="🛠️ Панель управления")])
        keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

        # При первом старте админа — принудительно заливаем дефолтный каталог в облако
        await save_to_telegram_cloud(DEFAULT_CATALOG)

        await message.answer(
            "📊 <b>РАПОРТ NEXUS [ОБЛАЧНЫЙ РЕЖИМ]</b>\n\n🟢 Статус: Активен\n☁️ Синхронизация: Напрямую с серверами Telegram",
            reply_markup=keyboard, parse_mode="HTML")
    else:
        keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        await message.answer("👋 Привет! Нажми кнопку ниже для открытия облачной витрины:", reply_markup=keyboard)

@router.message(F.text == "🛠️ Панель управления")
@router.message(Command("admin"))
async def admin_button_click(message: types.Message):
    if not message or message.from_user.id != ADMIN_ID: return
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить цену товара", callback_data="c_edit_mode")],
        [InlineKeyboardButton(text="➕ Добавить новый товар", callback_data="c_add_mode")],
        [InlineKeyboardButton(text="❌ Удалить товар из базы", callback_data="c_del_mode")]
    ])
    await message.answer("<b>🛠️ Облачное меню NEXUS</b>\nВыберите действие:", reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data == "c_edit_mode")
async def admin_select_edit_price(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    builder = InlineKeyboardBuilder()
    for prod in DEFAULT_CATALOG:
        builder.button(text=f"💰 {prod['name']} ({prod['price']} BYN)", callback_data=f"c_ed_{prod['id']}")
    builder.adjust(1)
    await callback.message.edit_text("<b>✏️ Изменение цен</b>\nВыберите товар:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("c_ed_"))
async def process_edit_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    product_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_prod_id=product_id)
    await state.set_state(AdminStates.waiting_for_price)
    await callback.message.edit_text("🔢 Введите <b>новую цену</b> в BYN:", parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_for_price)
async def save_new_price(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID or not message.text: return
    try:
        new_price = float(message.text.replace(",", ".").strip())
        if new_price <= 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите положительное число.")
        return
    user_data = await state.get_data()
    for prod in DEFAULT_CATALOG:
        if prod['id'] == user_data['edit_prod_id']:
            prod['price'] = new_price
            # СИНХРОНИЗАЦИЯ: отправляем измененный каталог в сервера Telegram
            await save_to_telegram_cloud(DEFAULT_CATALOG)
            await message.answer(f"✅ Цена <b>{prod['name']}</b> изменена на <b>{new_price} BYN</b> в Облаке!", parse_mode="HTML")
            break
    await state.clear()

@router.callback_query(F.data == "c_del_mode")
async def admin_select_delete(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    builder = InlineKeyboardBuilder()
    for prod in DEFAULT_CATALOG:
        builder.button(text=f"🗑️ {prod['name']}", callback_data=f"c_dl_{prod['id']}")
    builder.adjust(1)
    await callback.message.edit_text("<b>🔴 Удаление товаров</b>\nВыберите позицию:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("c_dl_"))
async def process_delete_product(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    product_id = int(callback.data.split("_")[-1])
    global DEFAULT_CATALOG
    DEFAULT_CATALOG = [p for p in DEFAULT_CATALOG if p['id'] != product_id]
    # СИНХРОНИЗАЦИЯ: сохраняем удаление в сервера Telegram
    await save_to_telegram_cloud(DEFAULT_CATALOG)
    await callback.message.edit_text("💥 Компонент удален из облачного ассортимента витрины!")
    await callback.answer()

@router.callback_query(F.data == "c_add_mode")
async def admin_start_add_product(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_new_name)
    await callback.message.edit_text("✍️ Введите <b>название</b> для нового товара:")
    await callback.answer()

@router.message(AdminStates.waiting_for_new_name)
async def admin_get_new_name(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID or not message.text: return
    name_input = message.text.strip()
    if len(name_input) < 3:
        await message.answer("⚠️ Слишком короткое название! Введите еще раз.")
        return
    await state.update_data(new_prod_name=name_input)
    await state.set_state(AdminStates.waiting_for_new_price)
    await message.answer(f"📦 Название: <b>{name_input}</b>\nТеперь введите <b>стоимость в BYN</b>:", parse_mode="HTML")

@router.message(AdminStates.waiting_for_new_price)
async def admin_get_new_price(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID or not message.text: return
    try:
        price_input = float(message.text.replace(",", ".").strip())
        if price_input <= 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите положительное число.")
        return
    user_data = await state.get_data()
    prod_name = user_data['new_prod_name']
    new_id = max([p['id'] for p in DEFAULT_CATALOG]) + 1 if DEFAULT_CATALOG else 1
    DEFAULT_CATALOG.append({"id": new_id, "name": prod_name, "price": price_input})
    # СИНХРОНИЗАЦИЯ: сохраняем новый товар в сервера Telegram
    await save_to_telegram_cloud(DEFAULT_CATALOG)
    await state.clear()
    await message.answer(f"✅ Товар успешно добавлен!\n<b>{prod_name}</b> — <b>{price_input} BYN</b>", parse_mode="HTML")

@router.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    if not message.web_app_data or not message.from_user or not message.bot: return
    try:
        goods, fio_city, phone = message.web_app_data.data.split("|||")
    except Exception:
        await message.answer("⚠️ Ошибка декодирования пакета.")
        return
    phone_clean = "".join(c for c in phone if c.isdigit())
    if len(fio_city.strip()) < 5:
        await message.answer("⚠️ Ошибка валидации данных доставки.")
        return
    if len(phone_clean) < 9:
        await message.answer("⚠️ Неверный формат номера телефона.")
        return
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    order_report_to_admin = (
        f"🔔 <b>НОВЫЙ ЗАКАЗ В NEXUS!</b>\n\n"
        f"👤 <b>Покупатель:</b> {message.from_user.full_name}\n"
        f"📍 <b>Доставка:</b> <code>{fio_city}</code>\n"
        f"📞 <b>Телефон:</b> <code>+{phone_clean}</code>\n\n"
        f"📦 <b>Корзина:</b>\n{goods}"
    )
    if message.from_user.id != ADMIN_ID:
        await message.bot.send_message(chat_id=ADMIN_ID, text=order_report_to_admin, parse_mode="HTML")
    success_text = f"🎉 <b>Заявка принята!</b>\n\n📦 <b>Компоненты:</b> {goods}\n📍 <b>Доставка:</b> {fio_city}\n📞 <b>Телефон:</b> +{phone_clean}"
    await message.answer(success_text, parse_mode="HTML")

async def main():
    logging.basicConfig(level=logging.INFO)
    dp.include_router(router)
    print("[SYSTEM] Облачный Telegram-бот NEXUS запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
