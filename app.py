# ============================================================================
# 🏥 HEALTH PLATFORM 360° v7.0 — FINAL OPTIMIZED
# Безопасность + Оптимизация + Синхронизация данных
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
# НАСТРОЙКА СТРАНИЦЫ
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
<link rel="manifest" href="manifest.json">
""", unsafe_allow_html=True)

# ============================================================================
# 🔐 БЕЗОПАСНОСТЬ
# ============================================================================
APP_PEPPER = "health_platform_2026_secure_key_change_in_production"


def hash_password(password: str, salt: str = None) -> tuple:
    """Безопасное хеширование с солью"""
    if salt is None:
        salt = secrets.token_hex(16)
    combined = f"{salt}{password}{APP_PEPPER}"
    return hashlib.sha256(combined.encode()).hexdigest(), salt


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """Проверка пароля (constant-time)"""
    computed_hash, _ = hash_password(password, stored_salt)
    return secrets.compare_digest(computed_hash, stored_hash)


def validate_email(email: str) -> bool:
    """Валидация email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple:
    """Проверка сложности пароля"""
    if len(password) < 8:
        return False, "Минимум 8 символов"
    if not re.search(r'[A-Za-z]', password):
        return False, "Нужны буквы"
    if not re.search(r'\d', password):
        return False, "Нужна цифра"
    return True, "OK"


def sanitize(text: str, max_len: int = 100) -> str:
    """Очистка ввода"""
    if not text:
        return ""
    return re.sub(r'[^\w\s\-.@]', '', text)[:max_len].strip()


# ============================================================================
# 🛡️ ЗАЩИТА ОТ БРУТФОРСА
# ============================================================================
def check_login_attempts(email: str) -> tuple:
    """Проверка блокировки"""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}

    attempts = st.session_state.login_attempts.get(email, {'count': 0, 'last': None})

    if attempts['last'] and attempts['count'] >= 5:
        diff = (datetime.now() - attempts['last']).total_seconds()
        if diff < 900:  # 15 минут
            return False, int(900 - diff)

    return True, 0


def record_failed_login(email: str):
    """Запись неудачной попытки"""
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}

    if email not in st.session_state.login_attempts:
        st.session_state.login_attempts[email] = {'count': 0, 'last': None}

    st.session_state.login_attempts[email]['count'] += 1
    st.session_state.login_attempts[email]['last'] = datetime.now()


def reset_login_attempts(email: str):
    """Сброс после успеха"""
    if 'login_attempts' in st.session_state and email in st.session_state.login_attempts:
        del st.session_state.login_attempts[email]


# ============================================================================
#  SESSION STATE (синхронизация данных)
# ============================================================================
if 'user_params' not in st.session_state:
    st.session_state.user_params = {
        'height_cm': None,
        'weight': None,
        'target_weight': None,
        'activity': 'Сидячий'
    }


def update_params(**kwargs):
    """Обновление параметров"""
    for key, value in kwargs.items():
        if key in st.session_state.user_params:
            st.session_state.user_params[key] = value


# ============================================================================
# 🎨 ФОНЫ (кэширование)
# ============================================================================
BACKGROUNDS = {
    "🌊 Море": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1920",
    "🏔️ Горы": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1920",
    "🌺 Маковое поле": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=1920",
    "️ Город": "https://images.unsplash.com/photo-1449034446853-66c86144b0ad?w=1920",
    "🌌 Градиент": None
}


@st.cache_data
def get_bg_css(bg_name: str) -> str:
    """Кэширование CSS фона"""
    url = BACKGROUNDS.get(bg_name)
    if url:
        return f"""<style>.stApp{{background:linear-gradient(rgba(255,255,255,0.88),rgba(255,255,255,0.88)),url('{url}');background-size:cover;background-position:center;background-attachment:fixed}}</style>"""
    return "<style>.stApp{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)}</style>"


def set_background(bg_name: str):
    st.markdown(get_bg_css(bg_name), unsafe_allow_html=True)


# ============================================================================
# 🗄️ БАЗА ДАННЫХ
# ============================================================================
@st.cache_resource
def init_db():
    """Инициализация БД с индексами"""
    conn = sqlite3.connect('health_platform_v8.db', check_same_thread=False)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY, surname TEXT, name TEXT, birth_date TEXT,
        gender TEXT, password_hash TEXT, password_salt TEXT,
        secret_question TEXT, secret_answer_hash TEXT, secret_answer_salt TEXT,
        created_at TEXT, background TEXT DEFAULT '🌌 Градиент'
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

    # Индексы для скорости
    for table in ['measurements', 'body_measurements', 'workouts', 'water', 'sleep']:
        c.execute(f'CREATE INDEX IF NOT EXISTS idx_{table}_email ON {table}(email)')

    conn.commit()
    return conn


conn = init_db()


# ============================================================================
# 🔐 АВТОРИЗАЦИЯ
# ============================================================================
def register_user(email, surname, name, birth_date, gender, password, sec_q, sec_a) -> tuple:
    """Регистрация"""
    if not validate_email(email):
        return False, "Неверный email"

    is_valid, msg = validate_password(password)
    if not is_valid:
        return False, msg

    pwd_hash, pwd_salt = hash_password(password)
    ans_hash, ans_salt = hash_password(sec_a.lower().strip())

    try:
        conn.cursor().execute('''INSERT INTO users 
            (email, surname, name, birth_date, gender, password_hash, password_salt,
             secret_question, secret_answer_hash, secret_answer_salt, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                              (sanitize(email), sanitize(surname, 50), sanitize(name, 50), birth_date,
                               gender, pwd_hash, pwd_salt, sanitize(sec_q, 200), ans_hash, ans_salt,
                               datetime.now().strftime("%d.%m.%Y %H:%M")))
        conn.commit()
        return True, "Успешно"
    except sqlite3.IntegrityError:
        return False, "Email занят"


def login_user(email, password) -> tuple:
    """Вход"""
    allowed, remaining = check_login_attempts(email)
    if not allowed:
        return False, f"Заблокировано на {remaining // 60} мин", None

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email=?', (email,))
    user = cursor.fetchone()

    if not user or not verify_password(password, user[5], user[6]):
        record_failed_login(email)
        attempts = max(0, 5 - st.session_state.login_attempts.get(email, {}).get('count', 0))
        return False, f"Неверно. Осталось: {attempts}", None

    reset_login_attempts(email)
    return True, "OK", {
        'surname': user[1], 'name': user[2], 'birth_date': user[3],
        'gender': user[4], 'background': user[11] or '🌌 Градиент'
    }


def reset_password(email, sec_answer, new_pwd) -> tuple:
    """Сброс пароля"""
    is_valid, msg = validate_password(new_pwd)
    if not is_valid:
        return False, msg

    cursor = conn.cursor()
    cursor.execute('SELECT secret_answer_hash, secret_answer_salt FROM users WHERE email=?', (email,))
    result = cursor.fetchone()

    if not result or not verify_password(sec_answer.lower().strip(), result[0], result[1]):
        return False, "Неверный ответ"

    new_hash, new_salt = hash_password(new_pwd)
    cursor.execute('UPDATE users SET password_hash=?, password_salt=? WHERE email=?',
                   (new_hash, new_salt, email))
    conn.commit()
    return True, "Пароль изменён"


def get_secret_question(email: str) -> str:
    cursor = conn.cursor()
    cursor.execute('SELECT secret_question FROM users WHERE email=?', (email,))
    result = cursor.fetchone()
    return result[0] if result else ""


# ============================================================================
#  МЕДИЦИНСКИЕ ФУНКЦИИ (кэширование)
# ============================================================================
AGE_NORMS = [(25, 19, 24), (35, 20, 25), (45, 21, 26), (55, 22, 27), (65, 23, 28)]
AGE_FACTORS = [(30, 1.0), (40, 1.02), (50, 1.04), (60, 1.06), (float('inf'), 1.08)]

NUTRITION = {
    '18-29': {'protein': (1.0, 1.3), 'fat': (0.8, 1.0), 'carbs': (3.0, 4.0), 'fiber': 25},
    '30-49': {'protein': (1.0, 1.2), 'fat': (0.8, 1.0), 'carbs': (3.0, 4.0), 'fiber': 25},
    '50-64': {'protein': (1.0, 1.2), 'fat': (0.7, 0.9), 'carbs': (2.5, 3.5), 'fiber': 30},
    '65+': {'protein': (1.2, 1.5), 'fat': (0.7, 0.9), 'carbs': (2.5, 3.5), 'fiber': 30},
}

ACTIVITY_REC = {
    '18-64': {'aerobic': '150-300 мин/нед', 'strength': 'Силовые 2+ раза/нед'},
    '65+': {'aerobic': '150 мин/нед', 'strength': 'Силовые + баланс'}
}

SLEEP_NORMS = {'18-25': (7, 9), '26-64': (7, 9), '65+': (7, 8)}

GI_DATA = {
    'Низкий (≤55)': [('Гречка', 54), ('Овсянка', 55), ('Чечевица', 25), ('Яблоки', 38), ('Брокколи', 10)],
    'Средний (56-69)': [('Рис басмати', 58), ('Цельнозерновой хлеб', 65), ('Бананы', 60)],
    'Высокий (≥70)': [('Белый хлеб', 75), ('Белый рис', 83), ('Картофель фри', 75), ('Сахар', 68)]
}


@st.cache_data
def calc_age(birth_date):
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


@st.cache_data
def get_age_group(age):
    if age < 30: return '18-29'
    if age < 50: return '30-49'
    if age < 65: return '50-64'
    return '65+'


@st.cache_data
def get_sleep_group(age):
    return '18-25' if age < 26 else ('26-64' if age < 65 else '65+')


@st.cache_data
def get_activity_group(age):
    return '65+' if age >= 65 else '18-64'


@st.cache_data
def get_age_norm(age):
    for max_age, min_v, max_v in AGE_NORMS:
        if age < max_age:
            return min_v, max_v
    return 24, 29


@st.cache_data
def get_age_factor(age):
    for max_age, factor in AGE_FACTORS:
        if age < max_age:
            return factor
    return 1.08


@st.cache_data
def calc_ideal_weight(gender, height_inches, age_factor):
    formulas = {
        'devine': (50, 45.5, 2.3, 2.3),
        'robinson': (52, 49, 1.9, 1.7),
        'miller': (56.2, 53.1, 1.41, 1.36),
        'hamwi': (48, 45.5, 2.7, 2.2)
    }
    results = []
    for _, (m_b, f_b, m_m, f_m) in formulas.items():
        base = m_b if gender == 'м' else f_b
        mult = m_m if gender == 'м' else f_m
        r = base + mult * (height_inches - 60)
        if _ == 'hamwi':
            r *= age_factor
        results.append(r)
    return round(sum(results) / len(results), 1)


@st.cache_data
def calc_calories(gender, weight, height_cm, age, activity):
    bmr = (10 * weight + 6.25 * height_cm - 5 * age + 5) if gender == 'м' else \
        (10 * weight + 6.25 * height_cm - 5 * age - 161)
    mult = {'Сидячий': 1.2, 'Умеренный': 1.375, 'Активный': 1.55, 'Очень активный': 1.725}
    maintain = int(bmr * mult[activity])
    return maintain, max(maintain - 500, 1200)


@st.cache_data
def calc_water(weight, activity):
    base = weight * 30
    bonus = {'Сидячий': 0, 'Умеренный': 500, 'Активный': 1000, 'Очень активный': 1500}
    return int(base + bonus[activity])


@st.cache_data
def calc_whr(waist, hips, gender):
    if not hips or hips == 0:
        return None, None
    whr = round(waist / hips, 2)
    if gender == 'ж':
        cat = "Низкий " if whr < 0.80 else ("Умеренный 🟡" if whr < 0.85 else "Высокий 🔴")
    else:
        cat = "Низкий 🟢" if whr < 0.85 else ("Умеренный 🟡" if whr < 0.90 else "Высокий 🔴")
    return whr, cat


@st.cache_data
def calc_body_fat(waist, hips, neck, height_cm, gender):
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
        cat = "Атлетический 💪" if bf < 14 else ("Фитнес 🏃" if bf < 18 else ("Средний " if bf < 25 else "Выше ⚠️"))
    else:
        cat = "Атлетический 💪" if bf < 21 else ("Фитнес 🏃" if bf < 25 else ("Средний 📊" if bf < 32 else "Выше ⚠️"))
    return bf, cat


# ============================================================================
#  МОТИВАЦИЯ
# ============================================================================
MOTIVATION = {
    'first': ["🌟 Первый шаг — самый важный!", "🚀 Ты начала! Это уже победа!"],
    'progress': ["💪 Видишь результат? Так держать!", "🏆 Прогресс есть!"],
    'plateau': [" Плато — это нормально!", " Доверяй процессу!"],
    'goal': ["🎉 ЦЕЛЬ ДОСТИГНУТА!", "🏆 Ты молодец!"],
    'daily': ["💧 Пей воду!", "🥗 Добавь овощей!", "🚶 10 000 шагов!", "💪 Тренируйся!"]
}


@st.cache_data(ttl=3600)
def get_quote(category='daily'):
    return random.choice(MOTIVATION.get(category, MOTIVATION['daily']))


# ============================================================================
# 🔔 НАПОМИНАНИЯ
# ============================================================================
@st.cache_data(ttl=60)
def check_reminder(email):
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(date) FROM measurements WHERE email=?', (email,))
    last_w = cursor.fetchone()[0]
    cursor.execute('SELECT MAX(date) FROM body_measurements WHERE email=?', (email,))
    last_b = cursor.fetchone()[0]
    dates = [d for d in [last_w, last_b] if d]
    if not dates:
        return False, 0
    try:
        last = max(datetime.strptime(d, "%d.%m.%Y %H:%M") for d in dates)
        days = (datetime.now() - last).days
        return days >= 7, days
    except:
        return False, 0


@st.cache_data(ttl=60)
def check_status(email):
    cursor = conn.cursor()
    cursor.execute('SELECT weight FROM measurements WHERE email=? ORDER BY date DESC LIMIT 10', (email,))
    weights = [r[0] for r in cursor.fetchall()]
    if len(weights) < 2:
        return 'first'
    diff = weights[-1] - weights[0]
    cursor.execute('SELECT target_weight FROM measurements WHERE email=? ORDER BY date DESC LIMIT 1', (email,))
    target = cursor.fetchone()
    if target and target[0] and abs(weights[0] - target[0]) < 1:
        return 'goal'
    if diff > 0.5:
        return 'progress'
    elif abs(diff) <= 0.5:
        return 'plateau'
    return 'first'


def play_sound():
    st.markdown("""<script>
    function beep(){try{const a=new(window.AudioContext||window.webkitAudioContext)();const o=a.createOscillator();const g=a.createGain();o.connect(g);g.connect(a.destination);o.frequency.value=800;o.type='sine';g.gain.setValueAtTime(0.3,a.currentTime);g.gain.exponentialRampToValueAtTime(0.01,a.currentTime+0.5);o.start(a.currentTime);o.stop(a.currentTime+0.5);}catch(e){}}
    beep();
    </script>""", unsafe_allow_html=True)


def request_notify():
    st.markdown("""<script>
    if("Notification" in window && Notification.permission==="default"){Notification.requestPermission();}
    </script>""", unsafe_allow_html=True)


def show_notify(title, body):
    st.markdown(f"""<script>
    if("Notification" in window && Notification.permission==="granted"){{
        new Notification("{title.replace('"', '\\"')}",{body:"{body.replace('"', '\\"')}",icon:"https://cdn-icons-png.flaticon.com/512/3036/3036724.png"});
    }}
    </script>""", unsafe_allow_html=True)


# ============================================================================
# 📊 ЭКСПОРТ
# ============================================================================
@st.cache_data(ttl=300)
def get_history(email, table, limit=30):
    queries = {
        'measurements': '''SELECT date as 'Дата', weight as 'Вес', bmi as 'ИМТ', category as 'Категория' FROM measurements WHERE email=? ORDER BY date DESC LIMIT ?''',
        'body_measurements': '''SELECT date as 'Дата', waist as 'Талия', hips as 'Бёдра', chest as 'Грудь', whr as 'WHR', body_fat as '% жира' FROM body_measurements WHERE email=? ORDER BY date DESC LIMIT ?''',
        'workouts': '''SELECT date as 'Дата', exercise as 'Упражнение', sets as 'Подходы', reps as 'Повторения', weight_kg as 'Вес' FROM workouts WHERE email=? ORDER BY date DESC LIMIT ?''',
        'water': '''SELECT SUBSTR(date,1,10) as 'День', SUM(volume_ml) as 'Всего (мл)' FROM water WHERE email=? GROUP BY SUBSTR(date,1,10) ORDER BY date DESC LIMIT ?''',
        'sleep': '''SELECT date as 'Дата', hours as 'Часов', quality as 'Качество' FROM sleep WHERE email=? ORDER BY date DESC LIMIT ?'''
    }
    return pd.read_sql_query(queries[table], conn, params=(email, limit))


def export_excel(email):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for table, sheet in [('measurements', 'Вес'), ('body_measurements', 'Тело'), ('workouts', 'Тренировки'),
                             ('water', 'Вода'), ('sleep', 'Сон')]:
            df = get_history(email, table, 1000)
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet, index=False)
    output.seek(0)
    return output


# ============================================================================
# 🔐 ЭКРАН ВХОДА
# ============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    set_background("🌌 Градиент")

    st.markdown("""<div style='text-align:center;padding:40px 20px;'>
        <h1 style='color:#2c5f8d;font-size:48px'>🏥 Health Platform 360°</h1>
        <p style='color:#555;font-size:18px'>Твой персональный помощник</p>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔐 Вход", "📝 Регистрация", "🔑 Забыли пароль?"])

    with tab1:
        st.markdown("### 👋 С возвращением!")
        login_email = st.text_input("Email", key="login_email")
        login_pwd = st.text_input("Пароль", type="password", key="login_pwd")

        allowed, remaining = check_login_attempts(login_email)
        if not allowed and login_email:
            st.error(f"⚠️ Заблокировано на {remaining // 60} мин")
        elif st.button(" Войти", type="primary", use_container_width=True):
            success, msg, data = login_user(login_email, login_pwd)
            if success:
                st.session_state.logged_in = True
                st.session_state.user_email = login_email
                st.session_state.user_data = data
                st.rerun()
            else:
                st.error(msg)

    with tab2:
        st.markdown("### ✨ Регистрация")
        reg_email = st.text_input("Email", key="reg_email")
        c1, c2 = st.columns(2)
        with c1:
            reg_surname = st.text_input("Фамилия", key="reg_surname")
            reg_name = st.text_input("Имя", key="reg_name")
        with c2:
            reg_birth = st.date_input("Дата рождения", value=date(1990, 1, 1), min_value=date(1920, 1, 1),
                                      max_value=date.today(), key="reg_birth")
            reg_gender = st.radio("Пол", ["м", "ж"], horizontal=True, key="reg_gender")

        reg_pwd = st.text_input("Пароль (мин. 8 символов, буквы+цифры)", type="password", key="reg_pwd")
        reg_pwd2 = st.text_input("Повторите пароль", type="password", key="reg_pwd2")

        st.markdown("---")
        st.markdown("### 🔐 Секретный вопрос")
        questions = ["Кличка первого питомца?", "Название первой школы?", "Город рождения?", "Любимое блюдо детства?"]
        sec_q = st.selectbox("Вопрос", questions, key="sec_q")
        sec_a = st.text_input("Ответ (запомните!)", key="sec_a")

        if st.button("🎉 Зарегистрироваться", type="primary", use_container_width=True):
            if not all([reg_email, reg_surname, reg_name, reg_pwd, sec_a]):
                st.error("Заполните все поля")
            elif reg_pwd != reg_pwd2:
                st.error("Пароли не совпадают")
            else:
                success, msg = register_user(reg_email, reg_surname, reg_name, reg_birth.strftime("%d.%m.%Y"),
                                             reg_gender, reg_pwd, sec_q, sec_a)
                if success:
                    st.success(f"✅ {msg}! Войдите.")
                else:
                    st.error(f" {msg}")

    with tab3:
        st.markdown("### 🔑 Восстановление")
        reset_email = st.text_input("Email", key="reset_email")

        if reset_email:
            question = get_secret_question(reset_email)
            if question:
                st.info(f"📝 Вопрос: **{question}**")
                reset_ans = st.text_input("Ответ", key="reset_ans")
                reset_pwd = st.text_input("Новый пароль", type="password", key="reset_pwd")
                reset_pwd2 = st.text_input("Повторите", type="password", key="reset_pwd2")

                if st.button("🔄 Сменить пароль", type="primary"):
                    if reset_pwd != reset_pwd2:
                        st.error("Пароли не совпадают")
                    else:
                        success, msg = reset_password(reset_email, reset_ans, reset_pwd)
                        if success:
                            st.success(f"✅ {msg}!")
                        else:
                            st.error(f"❌ {msg}")
            else:
                st.warning("Пользователь не найден")

    st.stop()

# ============================================================================
# 🏠 ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================================
user_email = st.session_state.user_email
user_data = st.session_state.user_data

set_background(user_data.get('background', '🌌 Градиент'))

if 'notification_requested' not in st.session_state:
    request_notify()
    st.session_state.notification_requested = True

# 🔔 Проверка напоминаний
reminder_needed, days_passed = check_reminder(user_email)

if reminder_needed and not st.session_state.get('reminder_shown_today'):
    play_sound()
    show_notify("🏥 Health Platform", f"Прошло {days_passed} дней!")

    st.markdown(
        """<style>.reminder{background:linear-gradient(135deg,#667eea,#764ba2);padding:30px;border-radius:20px;color:white;text-align:center;margin:20px 0}</style>""",
        unsafe_allow_html=True)
    st.markdown(f"""<div class='reminder'><h2>⏰ Время замеры!</h2><p>Прошло <b>{days_passed} дней</b></p></div>""",
                unsafe_allow_html=True)

    if st.button("✅ Понятно!", type="primary", use_container_width=True):
        st.session_state.reminder_shown_today = True
        st.balloons()
        st.rerun()

    st.markdown("---")

# БОКОВОЕ МЕНЮ
st.sidebar.markdown("## 🏥 Health 360°")
st.sidebar.markdown(f"### 👤 {user_data['name']} {user_data['surname']}")
st.sidebar.caption(f"📧 {user_email}")
st.sidebar.markdown("---")

section = st.sidebar.radio("📋 Раздел", [
    "🏠 Главная", " Замеры тела", "🥗 Питание", "💪 Тренировки",
    " Вода", "😴 Сон", " История", "⚙️ Настройки"
])

try:
    birth_date = datetime.strptime(user_data['birth_date'], "%d.%m.%Y").date()
except:
    birth_date = date(1990, 1, 1)

age = calc_age(birth_date)
gender = user_data['gender']

# 🎯 Мотивация
status = check_status(user_email)
if status == 'goal':
    quote, color, bg = get_quote('goal'), "#4CAF50", "#E8F5E9"
elif status == 'progress':
    quote, color, bg = get_quote('progress'), "#2196F3", "#E3F2FD"
elif status == 'plateau':
    quote, color, bg = get_quote('plateau'), "#FF9800", "#FFF3E0"
else:
    if st.session_state.get('first_shown'):
        quote, color, bg = get_quote('daily'), "#9C27B0", "#F3E5F5"
    else:
        quote, color, bg = get_quote('first'), "#E91E63", "#FCE4EC"
        st.session_state.first_shown = True

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"""<div style='background:{bg};padding:15px;border-radius:10px;border-left:4px solid {color};margin:10px 0'><p style='color:{color};margin:0;font-size:14px'>{quote}</p></div>""",
    unsafe_allow_html=True)

# ============================================================================
# 🏠 ГЛАВНАЯ
# ============================================================================
if section == "🏠 Главная":
    st.warning("⚠️ Не заменяет консультацию врача")
    st.markdown(f"<h1 style='text-align:center'>👋 Привет, {user_data['name']}!</h1>", unsafe_allow_html=True)

    # Берём из session_state
    h_def = st.session_state.user_params['height_cm'] or 170.0
    w_def = st.session_state.user_params['weight'] or 70.0
    t_def = st.session_state.user_params['target_weight'] or 65.0
    a_def = st.session_state.user_params['activity'] or 'Сидячий'

    c1, c2 = st.columns([2, 1])
    with c1:
        height_cm = st.number_input("📏 Рост (см)", 100.0, 250.0, h_def, 0.1, key="main_height")
        weight = st.number_input("⚖️ Вес (кг)", 30.0, 300.0, w_def, 0.1, key="main_weight")
        target_weight = st.number_input(" Цель (кг)", 30.0, 300.0, t_def, 0.1, key="main_target")
        activity = st.selectbox("🏃 Активность", ["Сидячий", "Умеренный", "Активный", "Очень активный"],
                                index=["Сидячий", "Умеренный", "Активный", "Очень активный"].index(a_def),
                                key="main_activity")

    with c2:
        st.markdown("### 📊 Показатели")
        bmi = round(weight / ((height_cm / 100) ** 2), 1)
        norm_min, norm_max = get_age_norm(age)
        cal_m, cal_l = calc_calories(gender, weight, height_cm, age, activity)
        water_ml = calc_water(weight, activity)
        sl_min, sl_max = SLEEP_NORMS[get_sleep_group(age)]

        st.metric("📊 ИМТ", f"{bmi}")
        st.metric(" Калории", f"{cal_l} ккал")
        st.metric("💧 Вода", f"{water_ml} мл")
        st.metric("😴 Сон", f"{sl_min}-{sl_max} ч")

    if st.button("💾 Сохранить", type="primary"):
        # Сохраняем в session_state
        update_params(height_cm=height_cm, weight=weight, target_weight=target_weight, activity=activity)

        height_inches = height_cm / 2.54
        age_factor = get_age_factor(age)
        ideal = calc_ideal_weight(gender, height_inches, age_factor)

        if bmi < norm_min:
            cat = "Недостаточный"
        elif bmi <= norm_max:
            cat = "Норма"
        elif bmi < 30:
            cat = "Избыточный"
        else:
            cat = "Ожирение"

        conn.cursor().execute('''INSERT INTO measurements 
            (email, date, height, weight, target_weight, activity, bmi, category, ideal_weight, calories_maintain, calories_lose)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                              (user_email, datetime.now().strftime("%d.%m.%Y %H:%M"), height_cm, weight, target_weight,
                               activity, bmi, cat, ideal, cal_m, cal_l))
        conn.commit()
        st.success("✅ Сохранено!")
        st.balloons()

# ============================================================================
# 📏 ЗАМЕРЫ ТЕЛА
# ============================================================================
elif section == "📏 Замеры тела":
    st.markdown("<h1>📏 Замеры тела</h1>", unsafe_allow_html=True)
    st.markdown("**Зачем?** Отличить жир от мышц, рассчитать WHR, % жира")
    st.markdown("---")

    h_def = st.session_state.user_params['height_cm'] or 170.0
    height_cm = st.number_input("📏 Рост (см)", 100.0, 250.0, h_def, 0.1, key="body_height")

    c1, c2, c3 = st.columns(3)
    with c1:
        waist = st.number_input("🎯 Талия (см)", 40.0, 200.0, 75.0, 0.5, key="b_waist")
        hips = st.number_input("🍑 Бёдра (см)", 50.0, 200.0, 95.0, 0.5, key="b_hips")
        chest = st.number_input("👚 Грудь (см)", 50.0, 200.0, 90.0, 0.5, key="b_chest")
    with c2:
        neck = st.number_input("🦢 Шея (см)", 20.0, 60.0, 35.0, 0.5, key="b_neck")
        arm = st.number_input("💪 Рука (см)", 15.0, 60.0, 28.0, 0.5, key="b_arm")

    if waist and hips:
        whr, whr_cat = calc_whr(waist, hips, gender)
        bf, bf_cat = calc_body_fat(waist, hips, neck, height_cm, gender)

        st.markdown("---")
        st.markdown("### 📊 Анализ")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("📐 WHR", whr, whr_cat)
        with c2:
            if bf:
                st.metric("🔥 % жира", f"{bf}%", bf_cat)

        if whr_cat and "Высокий" in whr_cat:
            st.error("🔴 Высокий WHR — риск ССЗ. Увеличьте активность.")
        elif whr_cat and "Умеренный" in whr_cat:
            st.warning("🟡 Умеренный WHR")
        else:
            st.success("🟢 WHR в норме")

    if st.button("💾 Сохранить", type="primary"):
        if waist and hips:
            whr, whr_cat = calc_whr(waist, hips, gender)
            bf, bf_cat = calc_body_fat(waist, hips, neck, height_cm, gender)

            conn.cursor().execute('''INSERT INTO body_measurements 
                (email, date, waist, hips, chest, neck, arm, whr, whr_category, body_fat, body_fat_category)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                                  (user_email, datetime.now().strftime("%d.%m.%Y %H:%M"), waist, hips, chest, neck, arm,
                                   whr, whr_cat, bf, bf_cat))
            conn.commit()
            st.success("✅ Сохранено!")
            st.balloons()

    st.markdown("---")
    st.markdown("### 📈 История")
    df = get_history(user_email, 'body_measurements', 14)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        if len(df) >= 2:
            st.line_chart(df[['Дата', 'Талия', 'Бёдра', 'Грудь']].set_index('Дата'))
    else:
        st.info("Нет записей")

# ============================================================================
# 🥗 ПИТАНИЕ
# ============================================================================
elif section == " Питание":
    st.markdown("<h1>🥗 Питание</h1>", unsafe_allow_html=True)

    h_def = st.session_state.user_params['height_cm'] or 170.0
    w_def = st.session_state.user_params['weight'] or 70.0
    a_def = st.session_state.user_params['activity'] or 'Сидячий'

    height_cm = st.number_input("Рост (см)", 100.0, 250.0, h_def, 0.1, key="food_height")
    weight = st.number_input("Вес (кг)", 30.0, 300.0, w_def, 0.1, key="food_weight")
    activity = st.selectbox("Активность", ["Сидячий", "Умеренный", "Активный", "Очень активный"],
                            index=["Сидячий", "Умеренный", "Активный", "Очень активный"].index(a_def),
                            key="food_activity")

    age_group = get_age_group(age)
    cal_m, cal_l = calc_calories(gender, weight, height_cm, age, activity)
    norms = NUTRITION[age_group]

    st.info(f" **Рекомендация:** {cal_l} ккал/день")

    custom_cal = st.number_input("✏️ Моя калорийность:", min_value=800, max_value=4000, value=cal_l, step=50,
                                 key="food_custom")

    if custom_cal < 1200:
        st.warning("⚠️ Менее 1200 ккал — ниже минимума ВОЗ")
    elif custom_cal < 1400:
        st.info(" Умеренно низко")
    else:
        st.success("✅ Безопасно")

    protein = round((custom_cal * 0.30) / 4, 1)
    fat = round((custom_cal * 0.30) / 9, 1)
    carbs = round((custom_cal * 0.40) / 4, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(" Цель", f"{custom_cal} ккал")
    c2.metric("🥩 Белки", f"{protein} г")
    c3.metric("🥑 Жиры", f"{fat} г")
    c4.metric("🍞 Углеводы", f"{carbs} г")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Принципы", "✅ Что есть", "❌ Исключить", "📊 ГИ"])

    with tab1:
        st.markdown(f"### 🎯 Группа: **{age_group}**")
        if age_group == '18-29':
            st.info("🔥 Метаболизм на пике")
        elif age_group == '30-49':
            st.info("⚠️ Метаболизм замедляется")
        elif age_group == '50-64':
            st.info("🦴 Важно: кальций, D, омега-3")
        else:
            st.info("👴 Нужно больше белка")

        st.markdown(f"""
        - 💧 Вода: **{calc_water(weight, activity)} мл**
        - 🥦 Клетчатка: **{norms['fiber']} г/день**
        - 🧂 Соль: ≤ **5 г**
        -  Сахар: ≤ **25 г**
        """)

    with tab2:
        foods = {
            'Белки': [' Рыба', '🍗 Курица', '🥚 Яйца', '🫘 Бобовые'],
            'Углеводы': ['🌾 Гречка', '🍚 Бурый рис', '🥔 Батат'],
            'Жиры': ['🥑 Авокадо', '🫒 Масло', '🥜 Орехи'],
            'Овощи': [' 5 порций', '🫐 Ягоды', '🍎 Фрукты']
        }
        cols = st.columns(4)
        for i, (cat, items) in enumerate(foods.items()):
            with cols[i]:
                st.markdown(f"**{cat}**")
                for item in items:
                    st.markdown(f"- {item}")

    with tab3:
        st.markdown("- 🍞 Белый хлеб\n- 🍟 Жареное\n- 🍬 Сладости\n-  Колбасы\n- 🍺 Алкоголь")

    with tab4:
        for level, products in GI_DATA.items():
            st.markdown(f"#### {level}")
            df = pd.DataFrame(products, columns=['Продукт', 'ГИ'])
            st.dataframe(df, use_container_width=True, hide_index=True)

# ============================================================================
# 💪 ТРЕНИРОВКИ
# ============================================================================
elif section == " Тренировки":
    st.markdown("<h1>💪 Тренировки</h1>", unsafe_allow_html=True)

    act_group = get_activity_group(age)
    rec = ACTIVITY_REC[act_group]

    st.info(f"🏃 **Аэробная:** {rec['aerobic']}\n️ **Силовая:** {rec['strength']}")
    st.markdown("---")

    st.markdown("### 📝 Записать")
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
                conn.cursor().execute(
                    '''INSERT INTO workouts (email, date, exercise, sets, reps, weight_kg, notes) VALUES (?,?,?,?,?,?,?)''',
                    (user_email, datetime.now().strftime("%d.%m.%Y %H:%M"), exercise, sets, reps, weight_kg, notes))
                conn.commit()
                st.success(f"✅ {exercise} — {sets}x{reps}")
                st.balloons()

    st.markdown("---")
    st.markdown("### 📖 История")
    df = get_history(user_email, 'workouts', 20)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Нет записей")

# ============================================================================
# 💧 ВОДА
# ============================================================================
elif section == " Вода":
    st.markdown("<h1>💧 Вода</h1>", unsafe_allow_html=True)

    w_def = st.session_state.user_params['weight'] or 70.0
    a_def = st.session_state.user_params['activity'] or 'Сидячий'

    weight = st.number_input("Вес (кг)", 30.0, 300.0, w_def, 0.1, key="water_weight")
    activity = st.selectbox("Активность", ["Сидячий", "Умеренный", "Активный", "Очень активный"],
                            index=["Сидячий", "Умеренный", "Активный", "Очень активный"].index(a_def),
                            key="water_activity")
    daily_goal = calc_water(weight, activity)

    st.markdown(f"### 🎯 Норма: **{daily_goal} мл**")

    today = datetime.now().strftime("%d.%m.%Y")
    df_today = pd.read_sql_query('SELECT SUM(volume_ml) as total FROM water WHERE email=? AND date LIKE ?', conn,
                                 params=(user_email, f"{today}%"))
    drunk = int(df_today['total'].iloc[0] or 0)

    progress = min(drunk / daily_goal, 1.0)
    st.progress(progress, text=f"Выпито: {drunk} мл / {daily_goal} мл ({int(progress * 100)}%)")

    if progress >= 1.0:
        st.success(" Норма выполнена!")

    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        glasses = st.number_input("Стаканов", 1, 20, 1, key="w_glasses")
    with c2:
        vol = st.number_input("Объём (мл)", 100, 1000, 250, 50, key="w_vol")
    with c3:
        if st.button("💧 Выпить", type="primary", use_container_width=True):
            conn.cursor().execute('''INSERT INTO water (email, date, glasses, volume_ml, goal_ml) VALUES (?,?,?,?,?)''',
                                  (user_email, datetime.now().strftime("%d.%m.%Y %H:%M"), glasses, glasses * vol,
                                   daily_goal))
            conn.commit()
            st.success(f"✅ {glasses * vol} мл")
            st.rerun()

    st.markdown("---")
    st.markdown("###  История")
    df = get_history(user_email, 'water', 14)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.line_chart(df.set_index('День'))

# ============================================================================
# 😴 СОН
# ============================================================================
elif section == "😴 Сон":
    st.markdown("<h1>😴 Сон</h1>", unsafe_allow_html=True)

    sl_group = get_sleep_group(age)
    sl_min, sl_max = SLEEP_NORMS[sl_group]
    st.markdown(f"### 🎯 Норма: **{sl_min}-{sl_max} часов**")

    c1, c2, c3 = st.columns(3)
    with c1:
        bedtime = st.time_input("Во сколько лёг", key="sl_bed")
    with c2:
        wake_time = st.time_input("Во сколько встал", key="sl_wake")
    with c3:
        quality = st.selectbox("Качество", ["Отличное ", "Хорошее 🙂", "Нормальное 😐", "Плохое 😫"], key="sl_quality")
    notes = st.text_input("Заметки", key="sl_notes")

    if st.button("💾 Сохранить", type="primary"):
        if bedtime and wake_time:
            bed_dt = datetime.combine(date.today(), bedtime)
            wake_dt = datetime.combine(date.today(), wake_time)
            if wake_dt <= bed_dt: