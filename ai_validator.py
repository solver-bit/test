import httpx
from config import OPENROUTER_API_KEY

API_URL = "https://openrouter.ai"


async def validate_with_ai(user_input: str, mode: str) -> str:
    """
    Возвращает 'VALID', 'INVALID' или 'SERVER_ERROR' в случае падения сети/лимитов.
    """
    if mode == "fio":
        system_prompt = (
            "Ты — строгий бэкенд-валидатор. Тебе присылают текст, который должен быть РЕАЛЬНЫМ ФИО человека и ГОРОДОМ доставки. "
            "Твоя задача — определить, имеет ли текст смысл, или это случайный набор букв, спам и бред. "
            "ПРАВИЛО: Такие строки как 'swdeefguh sudhf suhdf', 'wioruhn woeijubfth', 'asdasd asdasd', 'ываыва ываыва', 'Dhdjjd shjsd hsjd jdjdj' — это СЛУЧАЙНЫЙ БРЕД. "
            "Даже если в них только буквы, в них нет человеческого смысла. Это INVALID. "
            "Если текст похож на настоящее имя и город (например: 'Иванов Иван Минск', 'Дмитрий Петров Гомель') — это VALID. "
            "Ответь строго одним словом: VALID или INVALID. Никаких других символов и объяснений не пиши!"
        )
    else:
        system_prompt = (
            "Ты — валидатор телефонных номеров. Твоя задача — отсекать явный мусор, фейки и спам. "
            "Если переданный номер похож на реальный телефон — ответь строго VALID. "
            "Если это бред, случайные повторяющиеся цифры типа '+11111111111' или '+123456789012' — ответь строго INVALID. "
            "Пиши только VALID или INVALID."
        )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openrouter/free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.0
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url=API_URL, json=data, headers=headers, timeout=5.0)

            if response.status_code == 200:
                result = response.json()
                ai_answer = result['choices']['message']['content'].strip().upper()
                print(f"[AI SHIELD] Скрытый вердикт нейросети: '{ai_answer}'")

                if "VALID" in ai_answer and "INVALID" not in ai_answer:
                    return "VALID"
                else:
                    return "INVALID"
            else:
                # Если сработал лимит бесплатного тарифа (код 429 или 404)
                return "SERVER_ERROR"

    except Exception:
        # Если оборвался интернет или упал сервер
        return "SERVER_ERROR"
