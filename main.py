import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
import uvicorn

# Импортируем роутер и функции БД
from handlers.start import router as main_router
from database import get_all_products_from_db, init_products_db

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def start_bot():
    print("[SYSTEM] Telegram-бот успешно асинхронно запущен.")
    await dp.start_polling(bot)


# 🌌 ИСПРАВЛЕНО: Безопасный менеджер жизненного цикла для предотвращения RuntimeError
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Инициализируем базу данных
    print("[SYSTEM] Инициализация базы данных...")
    await init_products_db()

    # 2. ИСПРАВЛЕНО: Подключаем роутер строго внутри lifespan ОДИН раз за цикл процесса
    if main_router not in dp.sub_routers:
        dp.include_router(main_router)

    # 3. Запускаем опрос сервера ботом
    bot_task = asyncio.create_task(start_bot())

    yield

    # Действия при остановке сервера: отменяем задачу и закрываем сессию
    bot_task.cancel()
    await bot.session.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/products")
async def get_products_api():
    products = await get_all_products_from_db()
    return products


if __name__ == "__main__":
    # Запуск сервера uvicorn без расширения файла в названии модуля
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
