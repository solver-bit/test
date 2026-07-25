import aiosqlite

DB_PATH = "orders.db"


async def init_products_db():
    """Асинхронная инициализация таблиц базы данных SQLite"""
    async with aiosqlite.connect(DB_PATH) as conn:
        # Создаем таблицу заказов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_data TEXT NOT NULL,
                phone TEXT NOT NULL
            )
        """)

        # Создаем таблицу товаров
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)
        await conn.commit()

        # Проверяем количество товаров для автозаполнения
        async with conn.execute("SELECT COUNT(*) FROM products") as cursor:
            res = await cursor.fetchone()
            count = res[0] if res else 0
            if count == 0:
                start_items = [
                    ("Комплект оптики (Тип А)", 1200.0),
                    ("Комплект оптики (Тип Б)", 850.0),
                    ("Модуль доп. тюнинга", 450.0),
                    ("Спойлер карбоновый", 600.0),
                    ("Выхлопная система Спорт", 2100.0)
                ]
                await conn.executemany("INSERT INTO products (name, price) VALUES (?, ?)", start_items)
                await conn.commit()


async def save_order_to_db(user_id: int, order_data: str, phone: str):
    """Сохранение лога заказа клиента"""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO orders (user_id, order_data, phone) VALUES (?, ?, ?)",
            (user_id, order_data, phone)
        )
        await conn.commit()


async def get_all_products_from_db():
    """Возвращает список всех товаров в виде чистых словарей. Безопасно для JSON и хэндлеров."""
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT id, name, price FROM products") as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": int(r[0]),
                    "name": str(r[1]),
                    "price": float(r[2])
                })
            return result


async def update_product_price_in_db(product_id: int, new_price: float):
    """Обновление цены товара"""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, product_id))
        await conn.commit()


async def add_new_product_to_db(name: str, price: float):
    """Добавление нового товара"""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
        await conn.commit()


async def delete_product_from_db(product_id: int):
    """Удаление товара из базы данных"""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await conn.commit()
