# ============================================================================
# 🏥 HEALTH PLATFORM 360° PRO — С замерами тела и Excel-экспортом
# ============================================================================

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, timedelta, date
from io import BytesIO

st.set_page_config(page_title="Health Platform 360°", page_icon="🏥", layout="wide")

# ============================================================================
# PWA META-TEGS
# ============================================================================
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#2c5f8d">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="manifest" href="manifest.json">
""", unsafe_allow_html=True)

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


def set_background(bg_name):
    url = BACKGROUNDS.get(bg_name)
    if url:
        st.markdown(f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.88)), 
                        url('{url}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        </style>
        """, unsafe_allow_html=True)


# ============================================================================
# БАЗА ДАННЫХ (6 таблиц: + body_measurements)
# ============================================================================
@st.cache_resource
def init_db():
    conn = sqlite3.connect('health_platform_v9.db', check_same_thread=False)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY, surname TEXT, name TEXT, birth_date TEXT,
        gender TEXT, password_hash TEXT, created_at TEXT,
        background TEXT DEFAULT '🌌 Градиент (по умолчанию)'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT, date TEXT, height REAL, weight REAL, target_weight REAL,
        activity TEXT, bmi REAL, category TEXT, ideal_weight REAL,
        calories_maintain INT, calories_lose INT, custom_calories INT
    )''')

    # 🆕 НОВАЯ ТАБЛИЦА: замеры тела
    c.execute('''CREATE TABLE IF NOT EXISTS body_measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT, date TEXT,
        waist REAL, hips REAL, chest REAL,
        neck REAL, arm REAL,
        whr REAL, whr_category TEXT,
        body_fat REAL, body_fat_category TEXT
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

    conn.commit()
    return conn


conn = init_db()


# ============================================================================
# ФУНКЦИИ АВТОРИЗАЦИИ (упрощённые, без SMTP)
# ============================================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(email, surname, name, birth_date, gender, password):
    cursor = conn.cursor()
    try:
        cursor.execute('''INSERT INTO users 
            (email, surname, name, birth_date, gender, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (email, surname, name, birth_date, gender,
                        hash_password(password), datetime.now().strftime("%d.%m.%Y %H:%M")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def login_user(email, password):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email=? AND password_hash=?',
                   (email, hash_password(password)))
    return cursor.fetchone()


# ============================================================================
# 🆕 МЕДИЦИНСКИЕ ФУНКЦИИ ДЛЯ ЗАМЕРОВ ТЕЛА
# ============================================================================

def calculate_whr(waist, hips, gender):
    """Waist-to-Hip Ratio — индекс талия/бёдра (ВОЗ)"""
    if not hips or hips == 0:
        return None, None
    whr = round(waist / hips, 2)

    # Нормы ВОЗ по полу
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


def calculate_waist_risk(waist, gender):
    """Оценка риска по окружности талии (ВОЗ)"""
    if not waist:
        return None
    if gender == 'ж':
        if waist < 80: return "Норма 🟢"
        if waist < 88: return "Повышенный риск 🟡"
        return "Высокий риск 🔴 (абдоминальное ожирение)"
    else:
        if waist < 94: return "Норма 🟢"
        if waist < 102: return "Повышенный риск 🟡"
        return "Высокий риск 🔴 (абдоминальное ожирение)"


def calculate_body_fat_navy(waist, hips, neck, height_cm, gender):
    """% жира по формуле ВМС США (US Navy Method)"""
    if gender == 'м':
        if not all([waist, neck, height_cm]):
            return None, None
        # Формула для мужчин (в см)
        bf = 495 / (1.0324 - 0.19077 * (waist - neck) / 2.54 + 0.15456 * height_cm / 2.54) - 450
    else:
        if not all([waist, hips, neck, height_cm]):
            return None, None
        # Формула для женщин (в см)
        bf = 495 / (1.29579 - 0.35004 * (waist + hips - neck) / 2.54 + 0.22100 * height_cm / 2.54) - 450

    bf = round(bf, 1)

    # Классификация по ACE (American Council on Exercise)
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
# МЕДИЦИНСКИЕ ДАННЫЕ (остальные)
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
# ФУНКЦИИ РАСЧЁТА (остальные)
# ============================================================================
def calculate_age(birth_date):
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day): age -= 1
    return age


def get_age_group(age):
    if age < 30: return '18-29'
    if age < 50: return '30-49'
    if age < 65: return '50-64'
    return '65+'


def get_sleep_group(age):
    if age < 26: return '18-25'
    if age < 65: return '26-64'
    return '65+'


def get_activity_group(age):
    return '65+' if age >= 65 else '18-64'


def get_age_norm(age):
    for max_age, min_val, max_val in AGE_NORMS:
        if age < max_age: return min_val, max_val
    return 24, 29


def get_age_factor(age):
    for max_age, factor in AGE_FACTORS:
        if age < max_age: return factor
    return 1.08


def calculate_ideal_weight(gender, height_inches, age_factor):
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
    return sum(results) / len(results)


def calculate_calories(gender, weight, height_cm, age, activity):
    if gender == 'м':
        bmr = 10 * weight + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height_cm - 5 * age - 161
    mult = {'Сидячий': 1.2, 'Умеренный': 1.375, 'Активный': 1.55, 'Очень активный': 1.725}
    maintain = int(bmr * mult[activity])
    return maintain, max(maintain - 500, 1200)


def calculate_water(weight, activity):
    base = weight * 30
    bonus = {'Сидячий': 0, 'Умеренный': 500, 'Активный': 1000, 'Очень активный': 1500}
    return int(base + bonus[activity])


def export_to_excel(email):
    """Экспорт всей истории в Excel (включая замеры тела)"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Замеры веса
        df = pd.read_sql_query('''SELECT date as 'Дата', weight as 'Вес', bmi as 'ИМТ',
            category as 'Категория', custom_calories as 'Калории' FROM measurements
            WHERE email=? ORDER BY date''', conn, params=(email,))
        if not df.empty: df.to_excel(writer, sheet_name='Замеры веса', index=False)

        # Замеры тела
        df = pd.read_sql_query('''SELECT date as 'Дата', waist as 'Талия', hips as 'Бёдра',
            chest as 'Грудь', whr as 'WHR', whr_category as 'Категория WHR',
            body_fat as '% жира' FROM body_measurements
            WHERE email=? ORDER BY date''', conn, params=(email,))
        if not df.empty: df.to_excel(writer, sheet_name='Замеры тела', index=False)

        # Тренировки
        df = pd.read_sql_query('''SELECT date as 'Дата', exercise as 'Упражнение',
            sets as 'Подходы', reps as 'Повторения', weight_kg as 'Вес (кг)' FROM workouts
            WHERE email=? ORDER BY date''', conn, params=(email,))
        if not df.empty: df.to_excel(writer, sheet_name='Тренировки', index=False)

        # Вода
        df = pd.read_sql_query('''SELECT SUBSTR(date, 1, 10) as 'День',
            SUM(volume_ml) as 'Выпито (мл)', MAX(goal_ml) as 'Норма (мл)' FROM water
            WHERE email=? GROUP BY SUBSTR(date, 1, 10) ORDER BY date''', conn, params=(email,))
        if not df.empty: df.to_excel(writer, sheet_name='Вода', index=False)

        # Сон
        df = pd.read_sql_query('''SELECT date as 'Дата', hours as 'Часов',
            quality as 'Качество' FROM sleep
            WHERE email=? ORDER BY date''', conn, params=(email,))
        if not df.empty: df.to_excel(writer, sheet_name='Сон', index=False)

    output.seek(0)
    return output


# ============================================================================
# ЭКРАН АВТОРИЗАЦИИ (упрощённый, без email-подтверждения)
# ============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

if not st.session_state.logged_in:
    set_background("🌌 Градиент (по умолчанию)")

    st.markdown("""
    <div style='text-align: center; padding: 40px 20px;'>
        <h1 style='color: #2c5f8d; font-size: 48px;'>🏥 Health Platform 360°</h1>
        <p style='color: #555; font-size: 18px;'>Ваш персональный помощник для комплексного управления здоровьем</p>
    </div>
    """, unsafe_allow_html=True)

    auth_tab1, auth_tab2 = st.tabs(["🔐 Вход", "📝 Регистрация"])

    with auth_tab1:
        st.markdown("### 👋 С возвращением!")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Пароль", type="password", key="login_password")

        if st.button("🚪 Войти", type="primary", use_container_width=True):
            user = login_user(login_email, login_password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_email = login_email
                st.session_state.user_data = {
                    'surname': user[1], 'name': user[2], 'birth_date': user[3],
                    'gender': user[4], 'background': user[7] or '🌌 Градиент (по умолчанию)'
                }
                st.rerun()
            else:
                st.error("❌ Неверный email или пароль")

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
        reg_password = st.text_input("Пароль (мин. 6 символов)", type="password", key="reg_password")
        reg_password2 = st.text_input("Повторите пароль", type="password", key="reg_password2")

        if st.button("🎉 Зарегистрироваться", type="primary", use_container_width=True):
            if not all([reg_email, reg_surname, reg_name, reg_password]):
                st.error("❌ Заполните все поля")
            elif len(reg_password) < 6:
                st.error("❌ Пароль должен быть не менее 6 символов")
            elif reg_password != reg_password2:
                st.error("❌ Пароли не совпадают")
            elif "@" not in reg_email:
                st.error("❌ Неверный email")
            else:
                if register_user(reg_email, reg_surname, reg_name,
                                 reg_birth.strftime("%d.%m.%Y"), reg_gender, reg_password):
                    st.success("✅ Регистрация успешна! Теперь войдите.")
                else:
                    st.error("❌ Пользователь с таким email уже существует")

    st.stop()

# ============================================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================================
user_email = st.session_state.user_email
user_data = st.session_state.user_data

set_background(user_data.get('background', '🌌 Градиент (по умолчанию)'))

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
        ideal_weight = round(calculate_ideal_weight(gender, height_inches, age_factor), 1)

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

# ============================================================================
# 📏 🆕 ЗАМЕРЫ ТЕЛА (НОВЫЙ РАЗДЕЛ!)
# ============================================================================
elif section == "📏 Замеры тела":
    st.markdown("<h1>📏 Замеры тела</h1>", unsafe_allow_html=True)
    st.markdown("""
    **Зачем нужны замеры окружностей?**
    Вес на весах не показывает всю картину. Окружности помогают:
    - 🎯 Отличить потерю жира от потери мышц
    - 📊 Рассчитать индекс WHR (талия/бёдра) — маркер сердечно-сосудистых рисков
    - 💪 Оценить процент жира в организме
    """)

    st.markdown("---")
    st.markdown("### 📝 Ввести новые замеры")

    height_cm = st.number_input("📏 Рост (см)", 100.0, 250.0, 170.0, 0.1, key="body_height")

    c1, c2, c3 = st.columns(3)
    with c1:
        waist = st.number_input("🎯 Талия (см)", 40.0, 200.0, 75.0, 0.5,
                                help="Измеряйте в самом узком месте, на уровне пупка")
        hips = st.number_input("🍑 Бёдра (см)", 50.0, 200.0, 95.0, 0.5,
                               help="Измеряйте в самом широком месте ягодиц")
        chest = st.number_input("👚 Грудь (см)", 50.0, 200.0, 90.0, 0.5,
                                help="Измеряйте по самым выступающим точкам")
    with c2:
        neck = st.number_input("🦢 Шея (см)", 20.0, 60.0, 35.0, 0.5,
                               help="Измеряйте под кадыком (для расчёта % жира)")
        arm = st.number_input("💪 Рука (см)", 15.0, 60.0, 28.0, 0.5,
                              help="Измеряйте в самом широком месте бицепса")

    # Мгновенный расчёт при вводе
    if waist and hips:
        whr, whr_cat = calculate_whr(waist, hips, gender)
        waist_risk = calculate_waist_risk(waist, gender)
        bf, bf_cat = calculate_body_fat_navy(waist, hips, neck, height_cm, gender)

        st.markdown("---")
        st.markdown("### 📊 Мгновенный анализ")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("📐 WHR (талия/бёдра)", whr)
            st.caption(whr_cat)
        with c2:
            st.metric("⚠️ Риск по талии", waist_risk)
        with c3:
            if bf is not None:
                st.metric("🔥 % жира в организме", f"{bf}%")
                st.caption(bf_cat)

        # Рекомендации
        st.markdown("---")
        st.markdown("### 💡 Рекомендации по вашим замерам")

        if whr_cat and "Высокий" in whr_cat:
            st.error("""
            🔴 **Высокий WHR** — повышенный риск сердечно-сосудистых заболеваний.
            **Что делать:**
            - Снизить потребление простых углеводов и сахара
            - Увеличить аэробную нагрузку (ходьба, плавание) 150+ мин/нед
            - Добавить силовые тренировки для улучшения композиции тела
            """)
        elif whr_cat and "Умеренный" in whr_cat:
            st.warning("🟡 Умеренный WHR — стоит обратить внимание на питание и активность.")
        else:
            st.success("🟢 WHR в норме — отличный показатель!")

        if waist_risk and "Высокий" in waist_risk:
            st.error(
                f"🔴 Окружность талии {waist} см говорит об абдоминальном ожирении. Висцеральный жир повышает риск диабета 2 типа и гипертонии.")

        if bf is not None:
            if bf > 32 and gender == 'ж' or bf > 25 and gender == 'м':
                st.warning(f"📊 Процент жира {bf}% выше среднего. Фокус на силовые тренировки + дефицит калорий.")

    # Сохранение
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

    st.markdown("---")
    st.markdown("### 📈 История замеров")
    df = pd.read_sql_query('''SELECT date as 'Дата', waist as 'Талия', hips as 'Бёдра',
        chest as 'Грудь', whr as 'WHR', whr_category as 'Категория WHR',
        body_fat as '% жира' FROM body_measurements
        WHERE email=? ORDER BY date DESC LIMIT 14''', conn, params=(user_email,))

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

        # График динамики
        chart_df = df[['Дата', 'Талия', 'Бёдра', 'Грудь']].set_index('Дата')
        st.markdown("**Динамика окружностей:**")
        st.line_chart(chart_df)

        if 'WHR' in df.columns:
            whr_chart = df[['Дата', 'WHR']].set_index('Дата')
            st.markdown("**Динамика WHR:**")
            st.line_chart(whr_chart)
    else:
        st.info("Пока нет записей. Сделайте первый замер!")

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

    st.info(f"🤖 **Рекомендация формулы:** {cal_l} ккал/день (безопасный дефицит 500 ккал)")

    custom_calories = st.number_input(
        "✏️ Моя целевая калорийность (ккал):",
        min_value=800, max_value=4000, value=cal_l, step=50,
        help="Измените, если знаете особенности своего метаболизма"
    )

    if custom_calories < 1200:
        st.warning("""⚠️ **ВАЖНО:** Потребление менее 1200 ккал ниже безопасного минимума ВОЗ.
        Обязательно: проконсультируйтесь с врачом, принимайте витамины, следите за белком.""")
    elif custom_calories < 1400:
        st.info("💡 Умеренно низкая калорийность. Увеличьте долю белка и овощей.")
    else:
        st.success("✅ Безопасный диапазон калорий.")

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
            st.info("🔥 Метаболизм на пике. Формируйте здоровые привычки.")
        elif age_group == '30-49':
            st.info("⚠️ Метаболизм замедляется. Увеличьте долю белка.")
        elif age_group == '50-64':
            st.info("🦴 Важно: кальций, витамин D, омега-3.")
        else:
            st.info("👴 Нужно БОЛЬШЕ белка (1.2-1.5 г/кг) для сохранения мышц.")

        st.markdown(f"""
        - 💧 Вода: **{calculate_water(weight, activity)} мл**
        - 🥦 Клетчатка: **{norms['fiber']} г/день**
        - 🧂 Соль: не более **5 г** (ВОЗ)
        - 🍬 Сахар: не более **25 г** добавленного (ВОЗ)
        """)

    with tab2:
        foods = {
            'Белки': ['🐟 Рыба 2-3 раза/нед', '🍗 Куриная грудка', '🥚 Яйца', '🫘 Бобовые', '🥛 Творог'],
            'Углеводы': ['🌾 Гречка', '🍚 Бурый рис', '🥔 Батат', '🍞 Цельнозерновой хлеб'],
            'Жиры': ['🥑 Авокадо', '🫒 Оливковое масло', '🥜 Орехи 30г/день', '🐟 Жирная рыба'],
            'Овощи/Фрукты': ['🥬 5 порций в день', '🫐 Ягоды', '🍎 Сезонные фрукты']
        }
        cols = st.columns(4)
        for i, (cat, items) in enumerate(foods.items()):
            with cols[i]:
                st.markdown(f"**{cat}**")
                for item in items:
                    st.markdown(f"- {item}")

    with tab3:
        st.markdown("""
        - 🍞 **Белый хлеб, выпечка** (ГИ 75+)
        - 🍟 **Жареное, фастфуд**
        - 🍬 **Сладости, газировки**
        - 🥓 **Переработанное мясо** (сосиски, колбаса)
        - 🍺 **Алкоголь**
        - 🧂 **Избыток соли**
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
    🏃 **Аэробная нагрузка:** {rec['aerobic']}  
    🏋️ **Силовая:** {rec['strength']}
    """)
    st.markdown("**Примеры:** " + ", ".join(rec['examples']))

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

    st.markdown("---")
    st.markdown("### 📖 История")
    df = pd.read_sql_query('''SELECT date as 'Дата', exercise as 'Упражнение',
        sets as 'Подходы', reps as 'Повторения', weight_kg as 'Вес (кг)', notes as 'Заметки'
        FROM workouts WHERE email=? ORDER BY date DESC LIMIT 20''', conn, params=(user_email,))

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

    st.markdown(f"### 🎯 Норма: **{daily_goal} мл** ({round(daily_goal / 250, 1)} стаканов)")

    today = datetime.now().strftime("%d.%m.%Y")
    df_today = pd.read_sql_query('''SELECT SUM(volume_ml) as total FROM water
        WHERE email=? AND date LIKE ?''', conn, params=(user_email, f"{today}%"))
    drunk = int(df_today['total'].iloc[0] or 0)

    progress = min(drunk / daily_goal, 1.0)
    st.progress(progress, text=f"Выпито: {drunk} мл / {daily_goal} мл ({int(progress * 100)}%)")

    if progress >= 1.0:
        st.success("🎉 Норма выполнена!")
    elif progress >= 0.7:
        st.info("💪 Осталось немного!")

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
    df_hist = pd.read_sql_query('''SELECT SUBSTR(date, 1, 10) as 'День', 
        SUM(volume_ml) as 'Выпито (мл)', MAX(goal_ml) as 'Норма (мл)' FROM water
        WHERE email=? GROUP BY SUBSTR(date, 1, 10) ORDER BY date DESC LIMIT 14''',
                                conn, params=(user_email,))
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        st.line_chart(df_hist.set_index('День'))

# ============================================================================
# 😴 СОН
# ============================================================================
elif section == "😴 Сон":
    st.markdown("<h1>😴 Трекер сна</h1>", unsafe_allow_html=True)

    sl_group = get_sleep_group(age)
    sl_min, sl_max, sl_text = SLEEP_BY_AGE[sl_group]
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
                st.success(f"✅ Отлично! **{hours} ч** — в норме!")
            elif hours < sl_min:
                st.warning(f"⚠️ **{hours} ч** — меньше нормы")
            else:
                st.info(f"💤 **{hours} ч** — больше нормы")

    st.markdown("---")
    st.markdown("### 📊 История")
    df = pd.read_sql_query('''SELECT date as 'Дата', bedtime as 'Лёг', wake_time as 'Встал',
        hours as 'Часов', quality as 'Качество' FROM sleep
        WHERE email=? ORDER BY date DESC LIMIT 14''', conn, params=(user_email,))
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
        df = pd.read_sql_query('''SELECT date as 'Дата', weight as 'Вес', bmi as 'ИМТ',
            category as 'Категория', custom_calories as 'Калории' FROM measurements
            WHERE email=? ORDER BY date DESC''', conn, params=(user_email,))
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            if len(df) >= 2:
                st.line_chart(df[['Дата', 'Вес']].set_index('Дата'))
        else:
            st.info("Нет записей")

    with tab2:
        df = pd.read_sql_query('''SELECT date as 'Дата', waist as 'Талия', hips as 'Бёдра',
            chest as 'Грудь', whr as 'WHR', body_fat as '% жира' FROM body_measurements
            WHERE email=? ORDER BY date DESC LIMIT 30''', conn, params=(user_email,))
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            chart = df[['Дата', 'Талия', 'Бёдра', 'Грудь']].set_index('Дата')
            st.line_chart(chart)
        else:
            st.info("Нет записей")

    with tab3:
        df = pd.read_sql_query('''SELECT date as 'Дата', exercise as 'Упражнение',
            sets as 'Подх', reps as 'Повт', weight_kg as 'Вес' FROM workouts
            WHERE email=? ORDER BY date DESC LIMIT 30''', conn, params=(user_email,))
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Нет записей")

    with tab4:
        df = pd.read_sql_query('''SELECT SUBSTR(date, 1, 10) as 'День',
            SUM(volume_ml) as 'Всего (мл)' FROM water
            WHERE email=? GROUP BY SUBSTR(date, 1, 10) ORDER BY date DESC LIMIT 14''',
                               conn, params=(user_email,))
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.line_chart(df.set_index('День'))
        else:
            st.info("Нет записей")

    with tab5:
        df = pd.read_sql_query('''SELECT date as 'Дата', hours as 'Часов',
            quality as 'Качество' FROM sleep
            WHERE email=? ORDER BY date DESC LIMIT 14''', conn, params=(user_email,))
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.line_chart(df[['Дата', 'Часов']].set_index('Дата'))
        else:
            st.info("Нет записей")

# ============================================================================
# ⚙️ НАСТРОЙКИ (упрощённые, без SMTP)
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

    # Экспорт в Excel
    st.markdown("### 📊 Экспорт всей истории в Excel")
    st.caption("Скачайте полную историю всех замеров, тренировок, воды и сна в одном файле.")

    if st.button("📥 Сформировать Excel-отчёт", type="primary"):
        excel_file = export_to_excel(user_email)
        st.download_button(
            label="💾 Скачать файл",
            data=excel_file,
            file_name=f"health_report_{user_data['surname']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.success("✅ Файл готов! Нажмите кнопку выше для скачивания.")

    st.markdown("---")

    # PWA инструкция
    st.markdown("### 📱 Установить как приложение (PWA)")
    st.markdown("""
    **На iPhone (Safari):**
    1. Откройте это приложение в Safari
    2. Нажмите кнопку "Поделиться" (квадрат со стрелкой)
    3. Выберите "На экран «Домой»"
    4. Нажмите "Добавить"

    **На Android (Chrome):**
    1. Откройте это приложение в Chrome
    2. Нажмите меню (⋮) в правом верхнем углу
    3. Выберите "Добавить на главный экран"
    4. Нажмите "Установить"

    Теперь приложение будет открываться как обычное приложение на вашем телефоне! 🎉
    """)

    st.markdown("---")

    # Выход
    if st.button("🚪 Выйти из аккаунта"):
        for key in ['logged_in', 'user_email', 'user_data']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()