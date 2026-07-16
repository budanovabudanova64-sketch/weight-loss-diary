# ============================================================================
# 🏥 HEALTH PLATFORM 360° PRO — ФИНАЛЬНАЯ ВЕРСИЯ v7
# Оптимизированная + Безопасная + Сброс пароля
# ============================================================================

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
import re
import random
from datetime import datetime, timedelta, date
from io import BytesIO
from functools import lru_cache

# ============================================================================
# НАСТРОЙКА СТРАНИЦЫ + PWA
# ============================================================================
st.set_page_config(
    page_title="Health Platform 360°",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#2c5f8d">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Health 360">
<link rel="manifest" href="manifest.json">
""", unsafe_allow_html=True)


# ============================================================================
# 🔐 БЕЗОПАСНОСТЬ: Хеширование паролей с солью
# ============================================================================
def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Безопасное хеширование с солью (SHA-256 + salt)"""
    if salt is None:
        salt = secrets.token_hex(16)  # 32 символа случайной соли
    # Комбинируем соль + пароль + pepper (секретный ключ приложения)
    pepper = "health_platform_2026_secret_key"
    combined = f"{salt}{password}{pepper}"
    hash_value = hashlib.sha256(combined.encode()).hexdigest()
    return hash_value, salt


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """Проверка пароля"""
    computed_hash, _ = hash_password(password, stored_salt)
    # Используем constant-time сравнение для защиты от timing attacks
    return secrets.compare_digest(computed_hash, stored_hash)


def validate_email(email: str) -> bool:
    """Валидация email формата"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Проверка сложности пароля"""
    if len(password) < 8:
        return False, "Минимум 8 символов"
    if not re.search(r'[A-Za-z]', password):
        return False, "Должны быть буквы"
    if not re.search(r'\d', password):
        return False, "Должна быть хотя бы одна цифра"
    return True, "Пароль надёжный"


def sanitize_input(text: str, max_length: int = 100) -> str:
    """Очистка ввода от потенциально опасных символов"""
    if not text:
        return ""
    # Удаляем все кроме букв, цифр, пробелов и базовой пунктуации
    cleaned = re.sub(r'[^\w\s\-.@]', '', text)
    return cleaned[:max_length].strip()


# ============================================================================
# 🛡️ ЗАЩИТА ОТ БРУТФОРСА
# ============================================================================
def check_login_attempts(email: str) -> tuple[bool, int]:
    """Проверка блокировки после неудачных попыток"""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}

    attempts = st.session_state.login_attempts.get(email, {'count': 0, 'last_attempt': None})

    if attempts['last_attempt']:
        time_diff = (datetime.now() - attempts['last_attempt']).total_seconds()
        if attempts['count'] >= 5 and time_diff < 900:  # 15 минут
            remaining = int(900 - time_diff)
            return False, remaining

    return True, 0


def record_failed_attempt(email: str):
    """Запись неудачной попытки входа"""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}

    if email not in st.session_state.login_attempts:
        st.session_state.login_attempts[email] = {'count': 0, 'last_attempt': None}

    st.session_state.login_attempts[email]['count'] += 1
    st.session_state.login_attempts[email]['last_attempt'] = datetime.now()


def reset_login_attempts(email: str):
    """Сброс счётчика после успешного входа"""
    if 'login_attempts' in st.session_state and email in st.session_state.login_attempts:
        del st.session_state.login_attempts[email]


# ============================================================================
# ФОНОВЫЕ ИЗОБРАЖЕНИЯ
# ============================================================================
BACKGROUNDS = {
    "🌊 Море": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1920",
    "🏔️ Горы": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1920",
    "🌺 Маковое поле": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=1920",
    "🏙️ Городской пейзаж": "https://images.unsplash.com/photo-1449034446853-66c86144b0ad?w=1920",
    "🌌 Градиент (по умолчанию)": None
}


@st.cache_data
def get_background_css(bg_name: str) -> str:
    """Кэширование CSS для фона"""
    url = BACKGROUNDS.get(bg_name)
    if url:
        return f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.88)), 
                        url('{url}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """
    else:
        return """
        <style>
        .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        </style>
        """


def set_background(bg_name: str):
    st.markdown(get_background_css(bg_name), unsafe_allow_html=True)


# ============================================================================
# БАЗА ДАННЫХ (v7 — с солью для паролей + секретный вопрос)
# ============================================================================
@st.cache_resource
def init_db():
    conn = sqlite3.connect('health_platform_v7.db', check_same_thread=False)
    c = conn.cursor()

    # Таблица пользователей (с salt и secret_question)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY, 
        surname TEXT, 
        name TEXT, 
        birth_date TEXT,
        gender TEXT, 
        password_hash TEXT, 
        password_salt TEXT,
        secret_question TEXT,
        secret_answer_hash TEXT,
        secret_answer_salt TEXT,
        created_at TEXT,
        background TEXT DEFAULT '🌌 Градиент (по умолчанию)',
        failed_attempts INTEGER DEFAULT 0,
        locked_until TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT, date TEXT, height REAL, weight REAL, target_weight REAL,
        activity TEXT, bmi REAL, category TEXT, ideal_weight REAL,
        calories_maintain INT, calories_lose INT, custom_calories INT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS body_measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT, date TEXT,
        waist REAL, hips REAL, chest REAL, neck REAL, arm REAL,
        whr REAL, whr_category TEXT, body_fat REAL, body_fat_category TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT, date TEXT, exercise TEXT, sets INT, reps INT, 
        weight_kg REAL, notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS water (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT, date TEXT, glasses INT, volume_ml REAL, goal_ml REAL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sleep (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT, date TEXT, bedtime TEXT, wake_time TEXT, 
        hours REAL, quality TEXT, notes TEXT
    )''')

    # Индексы для ускорения запросов
    c.execute('CREATE INDEX IF NOT EXISTS idx_measurements_email ON measurements(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_body_measurements_email ON body_measurements(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_workouts_email ON workouts(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_water_email ON water(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sleep_email ON sleep(email)')

    conn.commit()
    return conn


conn = init_db()


# ============================================================================
# ФУНКЦИИ АВТОРИЗАЦИИ (с защитой)
# ============================================================================
def register_user(email: str, surname: str, name: str, birth_date: str,
                  gender: str, password: str, secret_question: str, secret_answer: str) -> tuple[bool, str]:
    """Регистрация с валидацией"""
    # Валидация
    if not validate_email(email):
        return False, "Неверный формат email"

    is_strong, msg = validate_password_strength(password)
    if not is_strong:
        return False, msg

    # Хеширование
    pwd_hash, pwd_salt = hash_password(password)
    ans_hash, ans_salt = hash_password(secret_answer.lower().strip())

    cursor = conn.cursor()
    try:
        cursor.execute('''INSERT INTO users 
            (email, surname, name, birth_date, gender, password_hash, password_salt,
             secret_question, secret_answer_hash, secret_answer_salt, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (sanitize_input(email, 100),
                        sanitize_input(surname, 50),
                        sanitize_input(name, 50),
                        birth_date,
                        gender,
                        pwd_hash,
                        pwd_salt,
                        sanitize_input(secret_question, 200),
                        ans_hash,
                        ans_salt,
                        datetime.now().strftime("%d.%m.%Y %H:%M")))
        conn.commit()
        return True, "Регистрация успешна"
    except sqlite3.IntegrityError:
        return False, "Пользователь с таким email уже существует"


def login_user(email: str, password: str) -> tuple[bool, str, any]:
    """Вход с защитой от брутфорса"""
    # Проверка блокировки
    is_allowed, remaining = check_login_attempts(email)
    if not is_allowed:
        return False, f"⚠️ Аккаунт заблокирован. Подождите {remaining // 60} минут.", None

    cursor = conn.cursor()
    cursor.execute('''SELECT email, surname, name, birth_date, gender, 
                      password_hash, password_salt, background 
                      FROM users WHERE email=?''', (email,))
    user = cursor.fetchone()

    if not user:
        record_failed_attempt(email)
        return False, "❌ Неверный email или пароль", None

    # Проверка пароля
    if not verify_password(password, user[5], user[6]):
        record_failed_attempt(email)
        attempts = st.session_state.login_attempts.get(email, {}).get('count', 0)
        remaining_attempts = max(0, 5 - attempts)
        return False, f"❌ Неверный пароль. Осталось попыток: {remaining_attempts}", None

    # Успешный вход
    reset_login_attempts(email)
    user_data = {
        'surname': user[1],
        'name': user[2],
        'birth_date': user[3],
        'gender': user[4],
        'background': user[7] or '🌌 Градиент (по умолчанию)'
    }
    return True, "Вход выполнен", user_data


def reset_password(email: str, secret_answer: str, new_password: str) -> tuple[bool, str]:
    """Сброс пароля через секретный вопрос"""
    # Валидация нового пароля
    is_strong, msg = validate_password_strength(new_password)
    if not is_strong:
        return False, msg

    cursor = conn.cursor()
    cursor.execute('''SELECT secret_answer_hash, secret_answer_salt FROM users WHERE email=?''', (email,))
    result = cursor.fetchone()

    if not result:
        return False, "Пользователь не найден"

    # Проверка ответа на секретный вопрос
    if not verify_password(secret_answer.lower().strip(), result[0], result[1]):
        return False, "Неверный ответ на секретный вопрос"

    # Обновление пароля
    new_hash, new_salt = hash_password(new_password)
    cursor.execute('''UPDATE users SET password_hash=?, password_salt=? WHERE email=?''',
                   (new_hash, new_salt, email))
    conn.commit()
    return True, "Пароль успешно изменён"


def get_secret_question(email: str) -> str:
    """Получить секретный вопрос для сброса пароля"""
    cursor = conn.cursor()
    cursor.execute('SELECT secret_question FROM users WHERE email=?', (email,))
    result = cursor.fetchone()
    return result[0] if result else ""


# ============================================================================
# 🎯 ОПТИМИЗИРОВАННЫЕ МЕДИЦИНСКИЕ ФУНКЦИИ (с кэшированием)
# ============================================================================
@st.cache_data
def calculate_whr(waist: float, hips: float, gender: str) -> tuple[float, str]:
    if not hips or hips == 0:
        return None, None
    whr = round(waist / hips, 2)
    if gender == 'ж':
        if whr < 0.80:
            cat = "Низкий риск 🟢"
        elif whr < 0.85:
            cat = "Умеренный риск 🟡"
        else:
            cat = "Высокий риск 🔴"
    else:
        if whr < 0.85:
            cat = "Низкий риск 🟢"
        elif whr < 0.90:
            cat = "Умеренный риск 🟡"
        else:
            cat = "Высокий риск 🔴"
    return whr, cat


@st.cache_data
def calculate_waist_risk(waist: float, gender: str) -> str:
    if not waist:
        return None
    if gender == 'ж':
        if waist < 80: return "Норма 🟢"
        if waist < 88: return "Повышенный риск 🟡"
        return "Высокий риск 🔴"
    else:
        if waist < 94: return "Норма 🟢"
        if waist < 102: return "Повышенный риск 🟡"
        return "Высокий риск 🔴"


@st.cache_data
def calculate_body_fat_navy(waist: float, hips: float, neck: float, height_cm: float, gender: str) -> tuple[float, str]:
    if gender == 'м':
        if not all([waist, neck, height_cm]):
            return None, None
        bf = 495 / (1.0324 - 0.19077 * (waist - neck) / 2.54 + 0.15456 * height_cm / 2.54) - 450
    else:
        if not all([waist, hips, neck, height_cm]):
            return None, None
        bf = 495 / (1.29579 - 0.35004 * (waist + hips - neck) / 2.54 + 0.22100 * height_cm / 2.54) - 450
    bf = round(bf, 1)
    if gender == 'м':
        if bf < 6:
            cat = "Соревновательный уровень 🏆"
        elif bf < 14:
            cat = "Атлетический 💪"
        elif bf < 18:
            cat = "Фитнес 🏃"
        elif bf < 25:
            cat = "Средний уровень 📊"
        else:
            cat = "Выше среднего ⚠️"
    else:
        if bf < 14:
            cat = "Соревновательный уровень 🏆"
        elif bf < 21:
            cat = "Атлетический 💪"
        elif bf < 25:
            cat = "Фитнес 🏃"
        elif bf < 32:
            cat = "Средний уровень 📊"
        else:
            cat = "Выше среднего ⚠️"
    return bf, cat


# ============================================================================
# 🎯 МОТИВАЦИОННЫЕ ФРАЗЫ
# ============================================================================
MOTIVATION_QUOTES = {
    'first_visit': [
        "🌟 Первый шаг — самый важный. Ты уже молодец, что начала!",
        "🚀 Путь в 1000 км начинается с одного шага!",
        "💎 Забота о себе — лучшая инвестиция!",
        "🌱 Каждое большое изменение начинается с маленького решения.",
    ],
    'progress': [
        "💪 Видишь результат? Твоё тело говорит 'спасибо'!",
        "🏆 Прогресс есть! Продолжай!",
        "✨ Ты становишься лучшей версией себя!",
        "🔥 Дисциплина — мост между целями и достижениями!",
    ],
    'plateau': [
        "🌊 Плато — подготовка к новому рывку!",
        "💎 Тело перестраивается. Доверяй процессу!",
        "🏔️ Самые красивые виды после трудного подъёма!",
        "🧘 Терпение — ключ к долгосрочным результатам!",
    ],
    'goal_achieved': [
        "🎉 ЦЕЛЬ ДОСТИГНУТА! Ты — героиня!",
        "🏆 Ты доказала, что можешь всё!",
        "👑 Это твоя победа! Запомни это чувство!",
    ],
    'daily_random': [
        "💧 Не забудь про воду!",
        "🥗 Добавь овощей в рацион!",
        "🚶 10 000 шагов — цель на сегодня!",
        "😴 Хороший сон = хороший результат!",
        "🧘 5 минут растяжки изменят день!",
        "💪 Каждая тренировка делает сильнее!",
    ]
}


@st.cache_data(ttl=3600)  # Кэш на 1 час
def get_motivation_quote(category: str = 'daily_random') -> str:
    quotes = MOTIVATION_QUOTES.get(category, MOTIVATION_QUOTES['daily_random'])
    return random.choice(quotes)


# ============================================================================
# 🔔 ОПТИМИЗИРОВАННЫЕ ПРОВЕРКИ (с кэшированием)
# ============================================================================
@st.cache_data(ttl=60)  # Кэш на 1 минуту
def check_reminder_needed(email: str) -> tuple[bool, int]:
    """Проверка напоминания (кэшируется на 1 минуту)"""
    cursor = conn.cursor()
    cursor.execute('''SELECT MAX(date) FROM measurements WHERE email=?''', (email,))
    last_weight = cursor.fetchone()[0]
    cursor.execute('''SELECT MAX(date) FROM body_measurements WHERE email=?''', (email,))
    last_body = cursor.fetchone()[0]
    dates = [d for d in [last_weight, last_body] if d]
    if not dates:
        return False, 0
    try:
        last_date = max(datetime.strptime(d, "%d.%m.%Y %H:%M") for d in dates)
        days_passed = (datetime.now() - last_date).days
        return days_passed >= 7, days_passed
    except:
        return False, 0


@st.cache_data(ttl=60)
def check_progress(email: str) -> str:
    """Определение статуса (кэшируется)"""
    cursor = conn.cursor()
    cursor.execute('''SELECT weight FROM measurements WHERE email=? 
                      ORDER BY date DESC LIMIT 10''', (email,))
    weights = [row[0] for row in cursor.fetchall()]
    if len(weights) < 2:
        return 'first_visit'
    first_weight = weights[-1]
    last_weight = weights[0]
    diff = first_weight - last_weight
    cursor.execute('''SELECT target_weight FROM measurements WHERE email=? 
                      ORDER BY date DESC LIMIT 1''', (email,))
    target = cursor.fetchone()
    if target and target[0] and abs(last_weight - target[0]) < 1:
        return 'goal_achieved'
    if diff > 0.5:
        return 'progress'
    elif abs(diff) <= 0.5:
        return 'plateau'
    return 'first_visit'


def play_reminder_sound():
    st.markdown("""
    <script>
    function playBeep() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
            setTimeout(() => {
                const osc2 = audioContext.createOscillator();
                const gain2 = audioContext.createGain();
                osc2.connect(gain2);
                gain2.connect(audioContext.destination);
                osc2.frequency.value = 1000;
                osc2.type = 'sine';
                gain2.gain.setValueAtTime(0.3, audioContext.currentTime);
                gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                osc2.start(audioContext.currentTime);
                osc2.stop(audioContext.currentTime + 0.5);
            }, 300);
        } catch(e) { console.log('Audio error:', e); }
    }
    playBeep();
    </script>
    """, unsafe_allow_html=True)


def request_notification_permission():
    st.markdown("""
    <script>
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }
    </script>
    """, unsafe_allow_html=True)


def show_notification(title: str, body: str):
    # Экранирование для безопасности
    title_escaped = title.replace('"', '\\"').replace("'", "\\'")
    body_escaped = body.replace('"', '\\"').replace("'", "\\'")
    st.markdown(f"""
    <script>
    if ("Notification" in window && Notification.permission === "granted") {{
        new Notification("{title_escaped}", {{
            body: "{body_escaped}",
            icon: "https://cdn-icons-png.flaticon.com/512/3036/3036724.png"
        }});
    }}
    </script>
    """, unsafe_allow_html=True)


# ============================================================================
# МЕДИЦИНСКИЕ ДАННЫЕ (константы)
# ============================================================================
AGE_NORMS = [(25, 19, 24), (35, 20, 25), (45, 21, 26), (55, 22, 27), (65, 23, 28)]
AGE_FACTORS = [(30, 1.0), (40, 1.02), (50, 1.04), (60, 1.06), (float('inf'), 1.08)]
NUTRITION_BY_AGE = {
    '18-29': {'protein': (1.0, 1.3), 'fat': (0.8, 1.0), 'carbs': (3.0, 4.0), 'fiber': 25},
    '30-49': {'protein': (1.0, 1.2), 'fat': (0.8, 1.0), 'carbs': (3.0, 4.0), 'fiber': 25},
    '50-64': {'protein': (1.0, 1.2), 'fat': (0.7, 0.9), 'carbs': (2.5, 3.5), 'fiber': 30},
    '65+': {'protein': (1.2, 1.5), 'fat': (0.7, 0.9), 'carbs': (2.5, 3.5), 'fiber': 30},
}
ACTIVITY_BY_AGE = {
    '18-64': {
        'aerobic': '150-300 мин умеренной ИЛИ 75-150 мин интенсивной в неделю',
        'strength': 'Силовые 2+ раза в неделю на все группы мышц',
        'examples': ['Ходьба быстрым шагом', 'Плавание', 'Велосипед', 'Танцы', 'Бег']
    },
    '65+': {
        'aerobic': '150-300 мин умеренной активности',
        'strength': 'Силовые 2+ раза + баланс 3+ раза',
        'examples': ['Скандинавская ходьба', 'Тай-чи', 'Йога', 'Плавание']
    }
}
SLEEP_BY_AGE = {
    '18-25': (7, 9, 'Оптимально 7-9 часов'),
    '26-64': (7, 9, 'Оптимально 7-9 часов'),
    '65+': (7, 8, 'Оптимально 7-8 часов'),
}
GI_PRODUCTS = {
    'Низкий ГИ (≤55)': [('Гречка', 54), ('Овсянка', 55), ('Чечевица', 25), ('Яблоки', 38), ('Брокколи', 10),
                        ('Миндаль', 15), ('Творог', 30)],
    'Средний ГИ (56-69)': [('Рис басмати', 58), ('Цельнозерновой хлеб', 65), ('Бананы', 60), ('Свёкла варёная', 64)],
    'Высокий ГИ (≥70)': [('Белый хлеб', 75), ('Белый рис', 83), ('Картофель фри', 75), ('Финики', 103), ('Пиво', 110),
                         ('Сахар', 68)]
}


# ============================================================================
# ФУНКЦИИ РАСЧЁТА (с кэшированием)
# ============================================================================
@st.cache_data
def calculate_age(birth_date: date) -> int:
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day): age -= 1
    return age


@st.cache_data
def get_age_group(age: int) -> str:
    if age < 30: return '18-29'
    if age < 50: return '30-49'
    if age < 65: return '50-64'
    return '65+'


@st.cache_data
def get_sleep_group(age: int) -> str:
    if age < 26: return '18-25'
    if age < 65: return '26-64'
    return '65+'


@st.cache_data
def get_activity_group(age: int) -> str:
    return '65+' if age >= 65 else '18-64'


@st.cache_data
def get_age_norm(age: int) -> tuple[int, int]:
    for max_age, min_val, max_val in AGE_NORMS:
        if age < max_age: return min_val, max_val
    return 24, 29


@st.cache_data
def get_age_factor(age: int) -> float:
    for max_age, factor in AGE_FACTORS:
        if age < max_age: return factor
    return 1.08


@st.cache_data
def calculate_ideal_weight(gender: str, height_inches: float, age_factor: float) -> float:
    formulas = {
        'devine': (50, 45.5, 2.3, 2.3), 'robinson': (52, 49, 1.9, 1.7),
        'miller': (56.2, 53.1, 1.41, 1.36), 'hamwi': (48, 45.5, 2.7, 2.2)
    }
    results = []
    for name, (m_b, f_b, m_m, f_m) in formulas.items():
        b = m_b if gender == 'м' else f_b
        m = m_m if gender == 'м' else f_m
        r = b + m * (height_inches - 60)
        if name == 'hamwi': r *= age_factor
        results.append(r)
    return round(sum(results) / len(results), 1)


@st.cache_data
def calculate_calories(gender: str, weight: float, height_cm: float, age: int, activity: str) -> tuple[int, int]:
    if gender == 'м':
        bmr = 10 * weight + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height_cm - 5 * age - 161
    mult = {'Сидячий': 1.2, 'Умеренный': 1.375, 'Активный': 1.55, 'Очень активный': 1.725}
    maintain = int(bmr * mult[activity])
    return maintain, max(maintain - 500, 1200)


@st.cache_data
def calculate_water(weight: float, activity: str) -> int:
    base = weight * 30
    bonus = {'Сидячий': 0, 'Умеренный': 500, 'Активный': 1000, 'Очень активный': 1500}
    return int(base + bonus[activity])


@st.cache_data(ttl=300)  # Кэш на 5 минут
def get_user_history(email: str, table: str, limit: int = 30) -> pd.DataFrame:
    """Универсальная функция для получения истории (кэшируется)"""
    queries = {
        'measurements': '''SELECT date as 'Дата', weight as 'Вес', bmi as 'ИМТ',
            category as 'Категория', custom_calories as 'Калории' FROM measurements
            WHERE email=? ORDER BY date DESC LIMIT ?''',
        'body_measurements': '''SELECT date as 'Дата', waist as 'Талия', hips as 'Бёдра',
            chest as 'Грудь', whr as 'WHR', body_fat as '% жира' FROM body_measurements
            WHERE email=? ORDER BY date DESC LIMIT ?''',
        'workouts': '''SELECT date as 'Дата', exercise as 'Упражнение',
            sets as 'Подх', reps as 'Повт', weight_kg as 'Вес' FROM workouts
            WHERE email=? ORDER BY date DESC LIMIT ?''',
        'water': '''SELECT SUBSTR(date, 1, 10) as 'День',
            SUM(volume_ml) as 'Всего (мл)' FROM water
            WHERE email=? GROUP BY SUBSTR(date, 1, 10) ORDER BY date DESC LIMIT ?''',
        'sleep': '''SELECT date as 'Дата', hours as 'Часов',
            quality as 'Качество' FROM sleep
            WHERE email=? ORDER BY date DESC LIMIT ?'''
    }
    return pd.read_sql_query(queries[table], conn, params=(email, limit))


def export_to_excel(email: str) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for table, sheet_name in [
            ('measurements', 'Замеры веса'),
            ('body_measurements', 'Замеры тела'),
            ('workouts', 'Тренировки'),
            ('water', 'Вода'),
            ('sleep', 'Сон')
        ]:
            df = get_user_history(email, table, limit=1000)
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output


# ============================================================================
# ЭКРАН АВТОРИЗАЦИИ (с сбросом пароля)
# ============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    set_background("🌌 Градиент (по умолчанию)")

    st.markdown("""
    <div style='text-align: center; padding: 40px 20px;'>
        <h1 style='color: #2c5f8d; font-size: 48px;'>🏥 Health Platform 360°</h1>
        <p style='color: #555; font-size: 18px;'>Ваш персональный помощник для здоровья</p>
    </div>
    """, unsafe_allow_html=True)

    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔐 Вход", "📝 Регистрация", "🔑 Забыли пароль?"])

    # ВХОД
    with auth_tab1:
        st.markdown("### 👋 С возвращением!")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Пароль", type="password", key="login_password")

        # Проверка блокировки
        is_allowed, remaining = check_login_attempts(login_email)
        if not is_allowed and login_email:
            st.error(f"⚠️ Слишком много попыток. Подождите {remaining // 60} минут.")
        else:
            if st.button("🚪 Войти", type="primary", use_container_width=True):
                success, message, user_data = login_user(login_email, login_password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_email = login_email
                    st.session_state.user_data = user_data
                    st.rerun()
                else:
                    st.error(message)

    # РЕГИСТРАЦИЯ
    with auth_tab2:
        st.markdown("### ✨ Создайте аккаунт")
        reg_email = st.text_input("Email", key="reg_email")
        col1, col2 = st.columns(2)
        with col1:
            reg_surname = st.text_input("Фамилия", key="reg_surname")
            reg_name = st.text_input("Имя", key="reg_name")
        with col2:
            reg_birth = st.date_input("Дата рождения", value=date(1990, 1, 1),
                                      min_value=date(1920, 1, 1), max_value=date.today(),
                                      key="reg_birth")
            reg_gender = st.radio("Пол", ["м", "ж"], horizontal=True, key="reg_gender")

        reg_password = st.text_input("Пароль (мин. 8 символов, буквы + цифры)",
                                     type="password", key="reg_password")
        reg_password2 = st.text_input("Повторите пароль", type="password", key="reg_password2")

        # Секретный вопрос для сброса пароля
        st.markdown("---")
        st.markdown("### 🔐 Секретный вопрос (для сброса пароля)")
        st.caption("⚠️ Выберите вопрос и запомните ответ — это единственный способ восстановить доступ!")

        secret_questions = [
            "Кличка вашего первого питомца?",
            "Название вашей первой школы?",
            "Город, где вы родились?",
            "Любимое блюдо из детства?",
            "Имя лучшего друга из детства?"
        ]
        secret_question = st.selectbox("Выберите секретный вопрос", secret_questions, key="secret_q")
        secret_answer = st.text_input("Ваш ответ (не забудьте!)", key="secret_a")

        if st.button("🎉 Зарегистрироваться", type="primary", use_container_width=True):
            if not all([reg_email, reg_surname, reg_name, reg_password, secret_answer]):
                st.error("❌ Заполните все поля")
            elif reg_password != reg_password2:
                st.error("❌ Пароли не совпадают")
            elif len(secret_answer.strip()) < 2:
                st.error("❌ Ответ на секретный вопрос слишком короткий")
            else:
                success, message = register_user(
                    reg_email, reg_surname, reg_name,
                    reg_birth.strftime("%d.%m.%Y"), reg_gender,
                    reg_password, secret_question, secret_answer
                )
                if success:
                    st.success(f"✅ {message}! Теперь войдите.")
                    st.info("💡 Запомните ответ на секретный вопрос — он нужен для сброса пароля!")
                else:
                    st.error(f"❌ {message}")

    # СБРОС ПАРОЛЯ
    with auth_tab3:
        st.markdown("### 🔑 Восстановление доступа")
        st.caption("Введите email и ответ на секретный вопрос, который вы указали при регистрации.")

        reset_email = st.text_input("Email аккаунта", key="reset_email")

        if reset_email:
            question = get_secret_question(reset_email)
            if question:
                st.info(f"📝 Ваш секретный вопрос: **{question}**")
                reset_answer = st.text_input("Ваш ответ", key="reset_answer")
                reset_password_new = st.text_input("Новый пароль (мин. 8 символов)",
                                                   type="password", key="reset_pwd")
                reset_password_new2 = st.text_input("Повторите новый пароль",
                                                    type="password", key="reset_pwd2")

                if st.button("🔄 Сменить пароль", type="primary"):
                    if reset_password_new != reset_password_new2:
                        st.error("❌ Пароли не совпадают")
                    else:
                        success, message = reset_password(reset_email, reset_answer, reset_password_new)
                        if success:
                            st.success(f"✅ {message}! Теперь войдите с новым паролем.")
                        else:
                            st.error(f"❌ {message}")
            else:
                st.warning("⚠️ Пользователь с таким email не найден")

    st.stop()

# ============================================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ (после авторизации)
# ============================================================================
user_email = st.session_state.user_email
user_data = st.session_state.user_data

set_background(user_data.get('background', '🌌 Градиент (по умолчанию)'))

if 'notification_requested' not in st.session_state:
    request_notification_permission()
    st.session_state.notification_requested = True

# 🔔 ПРОВЕРКА НАПОМИНАНИЙ
reminder_needed, days_passed = check_reminder_needed(user_email)

if reminder_needed and not st.session_state.get('reminder_shown_today'):
    play_reminder_sound()
    show_notification(
        "🏥 Health Platform 360°",
        f"Прошло {days_passed} дней с последнего замера."
    )

    st.markdown("""
    <style>
    .reminder-modal {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        margin: 20px 0;
    }
    .reminder-modal h2 { color: white !important; margin: 0 0 15px 0; }
    .reminder-modal p { font-size: 18px; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='reminder-modal'>
        <h2>⏰ Время позаботиться о себе!</h2>
        <p>Прошло <b>{days_passed} дней</b> с последнего замера.</p>
        <p>Регулярные измерения — ключ к успеху! 🎯</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("✅ Понятно, взвешусь сегодня!", type="primary", use_container_width=True):
        st.session_state.reminder_shown_today = True
        st.success("🎉 Отлично!")
        st.balloons()
        st.rerun()

    st.markdown("---")

# БОКОВОЕ МЕНЮ
st.sidebar.markdown("## 🏥 Health Platform 360°")
st.sidebar.markdown(f"### 👤 {user_data['name']} {user_data['surname']}")
st.sidebar.caption(f"📧 {user_email}")
st.sidebar.markdown("---")

section = st.sidebar.radio("📋 Раздел", [
    "🏠 Главная", "📏 Замеры тела", "🥗 Питание", "💪 Тренировки",
    "💧 Вода", "😴 Сон", "📊 История", "⚙️ Настройки"
])

try:
    birth_date = datetime.strptime(user_data['birth_date'], "%d.%m.%Y").date()
except:
    birth_date = date(1990, 1, 1)

age = calculate_age(birth_date)
gender = user_data['gender']

# 🎯 МОТИВАЦИОННЫЙ БЛОК
progress_status = check_progress(user_email)

if progress_status == 'goal_achieved':
    quote = get_motivation_quote('goal_achieved')
    quote_color, quote_bg = "#4CAF50", "#E8F5E9"
elif progress_status == 'progress':
    quote = get_motivation_quote('progress')
    quote_color, quote_bg = "#2196F3", "#E3F2FD"
elif progress_status == 'plateau':
    quote = get_motivation_quote('plateau')
    quote_color, quote_bg = "#FF9800", "#FFF3E0"
else:
    if st.session_state.get('first_visit_shown'):
        quote = get_motivation_quote('daily_random')
        quote_color, quote_bg = "#9C27B0", "#F3E5F5"
    else:
        quote = get_motivation_quote('first_visit')
        quote_color, quote_bg = "#E91E63", "#FCE4EC"
        st.session_state.first_visit_shown = True

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style='background: {quote_bg}; padding: 15px; border-radius: 10px; 
            border-left: 4px solid {quote_color}; margin: 10px 0;'>
    <p style='color: {quote_color}; margin: 0; font-size: 14px; font-weight: 500;'>
        {quote}
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# 🏠 ГЛАВНАЯ
# ============================================================================
if section == "🏠 Главная":
    st.warning("⚠️ Приложение носит информационный характер и не заменяет консультацию врача.")
    st.markdown(f"<h1 style='text-align:center;'>👋 Привет, {user_data['name']}!</h1>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        height_cm = st.number_input("📏 Рост (см)", 100.0, 250.0, 170.0, 0.1, key="main_height")
        weight = st.number_input("⚖️ Текущий вес (кг)", 30.0, 300.0, 70.0, 0.1, key="main_weight")
        target_weight = st.number_input("🎯 Целевой вес (кг)", 30.0, 300.0, 65.0, 0.1, key="main_target")
        activity = st.selectbox("🏃 Активность", ["Сидячий", "Умеренный", "Активный", "Очень активный"],
                                key="main_activity")

    with col2:
        st.markdown("### 📊 Быстрые показатели")
        height_m = height_cm / 100
        bmi = round(weight / (height_m ** 2), 1)
        norm_min, norm_max = get_age_norm(age)
        cal_m, cal_l = calculate_calories(gender, weight, height_cm, age, activity)
        water_ml = calculate_water(weight, activity)
        sleep_min, sleep_max, _ = SLEEP_BY_AGE[get_sleep_group(age)]

        st.metric("📊 ИМТ", f"{bmi}")
        st.metric("🔥 Калории", f"{cal_l} ккал")
        st.metric("💧 Вода", f"{water_ml} мл")
        st.metric("😴 Сон", f"{sleep_min}-{sleep_max} ч")

    if st.button("💾 Сохранить замер", type="primary"):
        height_inches = height_cm / 2.54
        age_factor = get_age_factor(age)
        ideal_weight = calculate_ideal_weight(gender, height_inches, age_factor)

        if bmi < norm_min:
            cat = "Недостаточный вес"
        elif bmi <= norm_max:
            cat = "Норма"
        elif bmi < 30:
            cat = "Избыточный вес"
        else:
            cat = "Ожирение"

        cursor = conn.cursor()
        cursor.execute('''INSERT INTO measurements 
            (email, date, height, weight, target_weight, activity, bmi, category, 
             ideal_weight, calories_maintain, calories_lose)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (user_email, datetime.now().strftime("%d.%m.%Y %H:%M"),
                        height_cm, weight, target_weight, activity, bmi, cat,
                        ideal_weight, cal_m, cal_l))
        conn.commit()
        st.success("✅ Замер сохранён!")
        st.balloons()

# ============================================================================
# 📏 ЗАМЕРЫ ТЕЛА
# ============================================================================
elif section == "📏 Замеры тела":
    st.markdown("<h1>📏 Замеры тела</h1>", unsafe_allow_html=True)
    st.markdown("""
    **Зачем нужны замеры окружностей?**
    - 🎯 Отличить потерю жира от потери мышц
    - 📊 Рассчитать индекс WHR — маркер сердечно-сосудистых рисков
    - 💪 Оценить процент жира в организме
    """)

    st.markdown("---")
    st.markdown("### 📝 Ввести новые замеры")

    height_cm = st.number_input("📏 Рост (см)", 100.0, 250.0, 170.0, 0.1, key="body_height")

    c1, c2, c3 = st.columns(3)
    with c1:
        waist = st.number_input("🎯 Талия (см)", 40.0, 200.0, 75.0, 0.5, key="b_waist")
        hips = st.number_input("🍑 Бёдра (см)", 50.0, 200.0, 95.0, 0.5, key="b_hips")
        chest = st.number_input("👚 Грудь (см)", 50.0, 200.0, 90.0, 0.5, key="b_chest")
    with c2:
        neck = st.number_input("🦢 Шея (см)", 20.0, 60.0, 35.0, 0.5, key="b_neck")
        arm = st.number_input("💪 Рука (см)", 15.0, 60.0, 28.0, 0.5, key="b_arm")

    if waist and hips:
        whr, whr_cat = calculate_whr(waist, hips, gender)
        waist_risk = calculate_waist_risk(waist, gender)
        bf, bf_cat = calculate_body_fat_navy(waist, hips, neck, height_cm, gender)

        st.markdown("---")
        st.markdown("### 📊 Мгновенный анализ")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("📐 WHR", whr)
            st.caption(whr_cat)
        with c2:
            st.metric("⚠️ Риск по талии", waist_risk)
        with c3:
            if bf is not None:
                st.metric("🔥 % жира", f"{bf}%")
                st.caption(bf_cat)

        st.markdown("---")
        st.markdown("### 💡 Рекомендации")

        if whr_cat and "Высокий" in whr_cat:
            st.error("🔴 Высокий WHR — повышенный риск ССЗ. Увеличьте аэробную нагрузку.")
        elif whr_cat and "Умеренный" in whr_cat:
            st.warning("🟡 Умеренный WHR — обратите внимание на питание.")
        else:
            st.success("🟢 WHR в норме!")

    if st.button("💾 Сохранить замеры", type="primary"):
        if waist and hips:
            whr, whr_cat = calculate_whr(waist, hips, gender)
            bf, bf_cat = calculate_body_fat_navy(waist, hips, neck, height_cm, gender)

            cursor = conn.cursor()
            cursor.execute('''INSERT INTO body_measurements 
                (email, date, waist, hips, chest, neck, arm, whr, whr_category, body_fat, body_fat_category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (user_email, datetime.now().strftime("%d.%m.%Y %H:%M"),
                            waist, hips, chest, neck, arm, whr, whr_cat, bf, bf_cat))
            conn.commit()
            st.success("✅ Замеры сохранены!")
            st.balloons()

    st.markdown("---")
    st.markdown("### 📈 История замеров")
    df = get_user_history(user_email, 'body_measurements', 14)

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        chart_df = df[['Дата', 'Талия', 'Бёдра', 'Грудь']].set_index('Дата')
        st.line_chart(chart_df)
    else:
        st.info("Пока нет записей")

# ============================================================================
# 🥗 ПИТАНИЕ
# ============================================================================
elif section == "🥗 Питание":
    st.markdown("<h1>🥗 Персональное питание</h1>", unsafe_allow_html=True)

    height_cm = st.number_input("Рост (см)", 100.0, 250.0, 170.0, 0.1, key="food_height")
    weight = st.number_input("Вес (кг)", 30.0, 300.0, 70.0, 0.1, key="food_weight")
    activity = st.selectbox("Активность", ["Сидячий", "Умеренный", "Активный", "Очень активный"], key="food_activity")

    age_group = get_age_group(age)
    cal_m, cal_l = calculate_calories(gender, weight, height_cm, age, activity)
    norms = NUTRITION_BY_AGE[age_group]

    st.info(f"🤖 **Рекомендация:** {cal_l} ккал/день")

    custom_calories = st.number_input(
        "✏️ Моя целевая калорийность (ккал):",
        min_value=800, max_value=4000, value=cal_l, step=50, key="food_custom_cal"
    )

    if custom_calories < 1200:
        st.warning("⚠️ Менее 1200 ккал — ниже безопасного минимума ВОЗ.")
    elif custom_calories < 1400:
        st.info("💡 Умеренно низкая калорийность.")
    else:
        st.success("✅ Безопасный диапазон.")

    target_protein = round((custom_calories * 0.30) / 4, 1)
    target_fat = round((custom_calories * 0.30) / 9, 1)
    target_carbs = round((custom_calories * 0.40) / 4, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎯 Цель", f"{custom_calories} ккал")
    c2.metric("🥩 Белки", f"{target_protein} г")
    c3.metric("🥑 Жиры", f"{target_fat} г")
    c4.metric("🍞 Углеводы", f"{target_carbs} г")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Принципы", "✅ Что есть", "❌ Исключить", "📊 ГИ"])

    with tab1:
        st.markdown(f"### 🎯 Возрастная группа: **{age_group}**")
        if age_group == '18-29':
            st.info("🔥 Метаболизм на пике.")
        elif age_group == '30-49':
            st.info("⚠️ Метаболизм замедляется.")
        elif age_group == '50-64':
            st.info("🦴 Важно: кальций, витамин D.")
        else:
            st.info("👴 Нужно БОЛЬШЕ белка.")

        st.markdown(f"""
        - 💧 Вода: **{calculate_water(weight, activity)} мл**
        - 🥦 Клетчатка: **{norms['fiber']} г/день**
        - 🧂 Соль: не более **5 г**
        - 🍬 Сахар: не более **25 г**
        """)

    with tab2:
        foods = {
            'Белки': ['🐟 Рыба', '🍗 Курица', '🥚 Яйца', '🫘 Бобовые', '🥛 Творог'],
            'Углеводы': ['🌾 Гречка', '🍚 Бурый рис', '🥔 Батат', '🍞 Цельнозерновой хлеб'],
            'Жиры': ['🥑 Авокадо', '🫒 Оливковое масло', '🥜 Орехи', '🐟 Жирная рыба'],
            'Овощи': ['🥬 5 порций/день', '🫐 Ягоды', '🍎 Фрукты']
        }
        cols = st.columns(4)
        for i, (cat, items) in enumerate(foods.items()):
            with cols[i]:
                st.markdown(f"**{cat}**")
                for item in items:
                    st.markdown(f"- {item}")

    with tab3:
        st.markdown("""
        - 🍞 Белый хлеб, выпечка
        - 🍟 Жареное, фастфуд
        - 🍬 Сладости, газировки
        - 🥓 Переработанное мясо
        - 🍺 Алкоголь
        - 🧂 Избыток соли
        """)

    with tab4:
        st.markdown("### 📊 Гликемический индекс")
        for level, products in GI_PRODUCTS.items():
            st.markdown(f"#### {level}")
            df = pd.DataFrame(products, columns=['Продукт', 'ГИ'])
            st.dataframe(df, use_container_width=True, hide_index=True)

# ============================================================================
# 💪 ТРЕНИРОВКИ
# ============================================================================
elif section == "💪 Тренировки":
    st.markdown("<h1>💪 Тренировочный дневник</h1>", unsafe_allow_html=True)

    act_group = get_activity_group(age)
    rec = ACTIVITY_BY_AGE[act_group]

    st.info(f"""
    🏃 **Аэробная:** {rec['aerobic']}  
    🏋️ **Силовая:** {rec['strength']}
    """)

    st.markdown("---")
    st.markdown("### 📝 Записать тренировку")

    c1, c2, c3 = st.columns(3)
    with c1:
        exercise = st.text_input("Упражнение", key="ex_name")
        sets = st.number_input("Подходы", 1, 20, 3, key="ex_sets")
    with c2:
        reps = st.number_input("Повторения", 1, 100, 12, key="ex_reps")
        weight_kg = st.number_input("Вес (кг)", 0.0, 500.0, 0.0, 0.5, key="ex_weight")
    with c3:
        notes = st.text_input("Заметки", key="ex_notes")
        if st.button("💾 Сохранить", type="primary", use_container_width=True):
            if exercise:
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO workouts 
                    (email, date, exercise, sets, reps, weight_kg, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                               (user_email, datetime.now().strftime("%d.%m.%Y %H:%M"),
                                exercise, sets, reps, weight_kg, notes))
                conn.commit()
                st.success(f"✅ Записано: {exercise} — {sets}x{reps}")
                st.balloons()

    st.markdown("---")
    st.markdown("### 📖 История")
    df = get_user_history(user_email, 'workouts', 20)

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Пока нет записей")

# ============================================================================
# 💧 ВОДА
# ============================================================================
elif section == "💧 Вода":
    st.markdown("<h1>💧 Водный баланс</h1>", unsafe_allow_html=True)

    weight = st.number_input("Вес (кг)", 30.0, 300.0, 70.0, 0.1, key="water_weight")
    activity = st.selectbox("Активность", ["Сидячий", "Умеренный", "Активный", "Очень активный"], key="water_activity")
    daily_goal = calculate_water(weight, activity)

    st.markdown(f"### 🎯 Норма: **{daily_goal} мл**")

    today = datetime.now().strftime("%d.%m.%Y")
    df_today = pd.read_sql_query('''SELECT SUM(volume_ml) as total FROM water
        WHERE email=? AND date LIKE ?''', conn, params=(user_email, f"{today}%"))
    drunk = int(df_today['total'].iloc[0] or 0)

    progress = min(drunk / daily_goal, 1.0)
    st.progress(progress, text=f"Выпито: {drunk} мл / {daily_goal} мл ({int(progress * 100)}%)")

    if progress >= 1.0:
        st.success("🎉 Норма выполнена!")

    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        glasses = st.number_input("Стаканов", 1, 20, 1, key="w_glasses")
    with c2:
        vol = st.number_input("Объём (мл)", 100, 1000, 250, 50, key="w_vol")
    with c3:
        if st.button("💧 Выпить", type="primary", use_container_width=True):
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO water 
                (email, date, glasses, volume_ml, goal_ml)
                VALUES (?, ?, ?, ?, ?)''',
                           (user_email, datetime.now().strftime("%d.%m.%Y %H:%M"),
                            glasses, glasses * vol, daily_goal))
            conn.commit()
            st.success(f"✅ Записано: {glasses * vol} мл")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📊 История")
    df_hist = get_user_history(user_email, 'water', 14)
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        st.line_chart(df_hist.set_index('День'))

# ============================================================================
# 😴 СОН
# ============================================================================
elif section == "😴 Сон":
    st.markdown("<h1>😴 Трекер сна</h1>", unsafe_allow_html=True)

    sl_group = get_sleep_group(age)
    sl_min, sl_max, _ = SLEEP_BY_AGE[sl_group]
    st.markdown(f"### 🎯 Норма: **{sl_min}-{sl_max} часов**")

    c1, c2, c3 = st.columns(3)
    with c1:
        bedtime = st.time_input("Во сколько лёг", key="sl_bed")
    with c2:
        wake_time = st.time_input("Во сколько встал", key="sl_wake")
    with c3:
        quality = st.selectbox("Качество",
                               ["Отличное 😴", "Хорошее 🙂", "Нормальное 😐", "Плохое 😫"], key="sl_quality")
    notes = st.text_input("Заметки", key="sl_notes")

    if st.button("💾 Сохранить", type="primary"):
        if bedtime and wake_time:
            bed_dt = datetime.combine(date.today(), bedtime)
            wake_dt = datetime.combine(date.today(), wake_time)
            if wake_dt <= bed_dt: wake_dt += timedelta(days=1)
            hours = round((wake_dt - bed_dt).total_seconds() / 3600, 1)

            cursor = conn.cursor()
            cursor.execute('''INSERT INTO sleep 
                (email, date, bedtime, wake_time, hours, quality, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (user_email, datetime.now().strftime("%d.%m.%Y %H:%M"),
                            bedtime.strftime("%H:%M"), wake_time.strftime("%H:%M"),
                            hours, quality, notes))
            conn.commit()

            if sl_min <= hours <= sl_max:
                st.success(f"✅ **{hours} ч** — в норме!")
            elif hours < sl_min:
                st.warning(f"⚠️ **{hours} ч** — меньше нормы")
            else:
                st.info(f"💤 **{hours} ч** — больше нормы")

    st.markdown("---")
    st.markdown("### 📊 История")
    df = get_user_history(user_email, 'sleep', 14)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.line_chart(df[['Дата', 'Часов']].set_index('Дата'))

# ============================================================================
# 📊 ИСТОРИЯ
# ============================================================================
elif section == "📊 История":
    st.markdown("<h1>📊 Полная история</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚖️ Вес", "📏 Тело", "💪 Тренировки", "💧 Вода", "😴 Сон"])

    with tab1:
        df = get_user_history(user_email, 'measurements', 30)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            if len(df) >= 2:
                st.line_chart(df[['Дата', 'Вес']].set_index('Дата'))
        else:
            st.info("Нет записей")

    with tab2:
        df = get_user_history(user_email, 'body_measurements', 30)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            chart = df[['Дата', 'Талия', 'Бёдра', 'Грудь']].set_index('Дата')
            st.line_chart(chart)
        else:
            st.info("Нет записей")

    with tab3:
        df = get_user_history(user_email, 'workouts', 30)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Нет записей")

    with tab4:
        df = get_user_history(user_email, 'water', 14)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.line_chart(df.set_index('День'))
        else:
            st.info("Нет записей")

    with tab5:
        df = get_user_history(user_email, 'sleep', 14)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.line_chart(df[['Дата', 'Часов']].set_index('Дата'))
        else:
            st.info("Нет записей")

# ============================================================================
# ⚙️ НАСТРОЙКИ
# ============================================================================
elif section == "⚙️ Настройки":
    st.markdown("<h1>⚙️ Настройки</h1>", unsafe_allow_html=True)

    # Смена фона
    st.markdown("### 🎨 Фон приложения")
    new_bg = st.selectbox("Выберите фон", list(BACKGROUNDS.keys()),
                          index=list(BACKGROUNDS.keys()).index(
                              user_data.get('background', '🌌 Градиент (по умолчанию)')))
    if st.button("💾 Применить фон"):
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET background=? WHERE email=?', (new_bg, user_email))
        conn.commit()
        st.session_state.user_data['background'] = new_bg
        st.success("✅ Фон изменён!")
        st.rerun()

    st.markdown("---")

    # Мотивация
    st.markdown("### 💪 Мотивация")
    if st.button("🎲 Новая мотивирующая фраза"):
        st.session_state.motivation_refresh = True
        st.rerun()

    if st.session_state.get('motivation_refresh'):
        new_quote = get_motivation_quote('daily_random')
        st.success(f"✨ {new_quote}")
        st.session_state.motivation_refresh = False

    st.markdown("---")

    # Экспорт в Excel
    st.markdown("### 📊 Экспорт в Excel")
    if st.button("📥 Сформировать Excel-отчёт", type="primary"):
        excel_file = export_to_excel(user_email)
        st.download_button(
            label="💾 Скачать файл",
            data=excel_file,
            file_name=f"health_report_{user_data['surname']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("---")

    # PWA инструкция
    st.markdown("### 📱 Установить как приложение (PWA)")
    st.markdown("""
    **iPhone (Safari):** Поделиться → На экран «Домой»  
    **Android (Chrome):** Меню (⋮) → Добавить на главный экран
    """)

    st.markdown("---")

    # Выход
    if st.button("🚪 Выйти из аккаунта"):
        for key in ['logged_in', 'user_email', 'user_data']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()