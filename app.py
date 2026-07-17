# ============================================================================
# 🏥 HEALTH PLATFORM 360° — С мотивацией и напоминаниями
# ============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sqlite3
import random
from datetime import datetime, timedelta, date
from io import BytesIO

st.set_page_config(page_title="Health Platform 360°", page_icon="🏥", layout="wide")

# PWA
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#2c5f8d">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="manifest" href="manifest.json">
""", unsafe_allow_html=True)

# ============================================================================
# 🎨 ФОНЫ
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
# 💪 МОТИВАЦИОННЫЕ ФРАЗЫ (30 штук!)
# ============================================================================
MOTIVATION_QUOTES = [
    "🌟 Маленькие шаги каждый день приводят к большим переменам!",
    "💪 Твоё тело способно на гораздо большее, чем ты думаешь. Уговори его!",
    "🎯 Не сравнивай себя с другими. Сравнивай себя с собой вчерашним.",
    "🔥 Дисциплина — это мост между целями и достижениями.",
    "🌱 Каждый день — это новый шанс стать лучше.",
    "💎 Трудности — это не препятствия, а ступеньки к успеху.",
    "🏆 Победитель — это просто мечтатель, который не сдался.",
    "🌈 После самого тёмного часа всегда наступает рассвет.",
    "🚀 Ты не обязан быть великим, чтобы начать. Но ты должен начать, чтобы стать великим.",
    "💫 Твоё единственное ограничение — это ты сам.",
    "🍎 Здоровье — это не destination, а образ жизни.",
    "🎯 Сосредоточься на прогрессе, а не на совершенстве.",
    "🌟 Успех — это сумма маленьких усилий, повторяемых день за днём.",
    "💪 Боль временна. Гордость — навсегда.",
    "🔥 Не жди подходящего момента. Создай его.",
    "🌱 Тело — это храм. Но некоторые относятся к нему как к сараю. Будь другим!",
    "🎯 Цель без плана — это просто желание.",
    "💎 Ты сильнее, чем думаешь. Проверь себя!",
    "🏆 Сегодняшние усилия — завтрашние результаты.",
    "🌈 Каждый шаг вперёд — это победа. Празднуй их!",
    "🚀 Путь в 1000 ли начинается с первого шага. Ты его уже сделал!",
    "💫 Не бойся идти медленно, бойся стоять на месте.",
    "🍎 Ешь то, что любит твоё тело, а не то, что любят твои вкусовые рецепторы.",
    "🎯 Фокус на процессе, а результат придёт сам.",
    "💪 Сложнее всего начать. Дальше — легче.",
    "🌟 Ты — автор своей истории. Пиши её красиво!",
    "🔥 Пот — это слёзы жира. Продолжай!",
    "🌱 Здоровье — это инвестиция, а не расход.",
    "💎 Верь в себя. Ты уже на правильном пути!",
    "🏆 Через год ты будешь благодарить себя за то, что начал сегодня."
]


def get_random_quote():
    return random.choice(MOTIVATION_QUOTES)


# ============================================================================
# 🔔 ФУНКЦИЯ НАПОМИНАНИЯ (будильник)
# ============================================================================
def play_reminder_sound():
    """Проигрывает звук напоминания через Web Audio API"""
    components.html("""
    <script>
    function playBeep() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            // Мелодия из 3 звуков
            const notes = [800, 1000, 800];
            notes.forEach((freq, i) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = freq;
                gain.gain.value = 0.3;
                osc.start(ctx.currentTime + i * 0.2);
                osc.stop(ctx.currentTime + i * 0.2 + 0.15);
            });
        } catch(e) { console.log('Audio error:', e); }
    }
    playBeep();
    </script>
    """, height=0)


def check_reminder(last_weigh_date_str):
    """Проверяет, нужно ли напомнить о замерах"""
    if not last_weigh_date_str:
        return True, "Вы ещё не делали замеры. Начните прямо сейчас!"

    try:
        last_date = datetime.strptime(last_weigh_date_str, "%d.%m.%Y").date()
        days_passed = (date.today() - last_date).days

        if days_passed >= 7:
            return True, f"Прошло {days_passed} дней с последнего замера. Пора обновить данные!"
        elif days_passed >= 5:
            return False, f"До следующего замера осталось {7 - days_passed} дней."
        else:
            return False, f"Отлично! Следующий замер через {7 - days_passed} дней."
    except:
        return True, "Не удалось определить дату последнего замера."


# ============================================================================
# 💾 БАЗА ДАННЫХ
# ============================================================================
@st.cache_resource
def init_db():
    conn = sqlite3.connect('health_platform_v6.db', check_same_thread=False)
    c = conn.cursor()

    # Единый профиль (одна запись)
    c.execute('''CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        surname TEXT, name TEXT, birth_date TEXT, gender TEXT,
        height REAL, weight REAL, target_weight REAL, activity TEXT,
        background TEXT, last_weigh_date TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, weight REAL, bmi REAL, category TEXT, custom_calories INT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS body_measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, waist REAL, hips REAL, chest REAL, neck REAL, arm REAL,
        whr REAL, whr_category TEXT, body_fat REAL, body_fat_category TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, exercise TEXT, sets INT, reps INT, weight_kg REAL, notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS water (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, glasses INT, volume_ml REAL, goal_ml REAL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sleep (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, bedtime TEXT, wake_time TEXT, hours REAL, quality TEXT, notes TEXT
    )''')

    conn.commit()
    return conn


conn = init_db()


def get_profile():
    """Получить профиль из БД"""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM profile WHERE id = 1')
    return cursor.fetchone()


def save_profile(surname, name, birth_date, gender, height, weight, target_weight, activity, background):
    """Сохранить/обновить профиль"""
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM profile WHERE id = 1')
    exists = cursor.fetchone()[0]

    if exists:
        cursor.execute('''UPDATE profile SET 
            surname=?, name=?, birth_date=?, gender=?, height=?, weight=?, 
            target_weight=?, activity=?, background=?, last_weigh_date=?
            WHERE id = 1''',
                       (surname, name, birth_date, gender, height, weight, target_weight,
                        activity, background, datetime.now().strftime("%d.%m.%Y")))
    else:
        cursor.execute('''INSERT INTO profile 
            (id, surname, name, birth_date, gender, height, weight, target_weight, 
             activity, background, last_weigh_date)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (surname, name, birth_date, gender, height, weight, target_weight,
                        activity, background, datetime.now().strftime("%d.%m.%Y")))
    conn.commit()


# ============================================================================
# 🧮 МЕДИЦИНСКИЕ ФУНКЦИИ
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


def calculate_whr(waist, hips, gender):
    if not hips or hips == 0: return None, None
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


def calculate_waist_risk(waist, gender):
    if not waist: return None
    if gender == 'ж':
        if waist < 80: return "Норма 🟢"
        if waist < 88: return "Повышенный риск 🟡"
        return "Высокий риск 🔴"
    else:
        if waist < 94: return "Норма 🟢"
        if waist < 102: return "Повышенный риск 🟡"
        return "Высокий риск 🔴"


def calculate_body_fat_navy(waist, hips, neck, height_cm, gender):
    if gender == 'м':
        if not all([waist, neck, height_cm]): return None, None
        bf = 495 / (1.0324 - 0.19077 * (waist - neck) / 2.54 + 0.15456 * height_cm / 2.54) - 450
    else:
        if not all([waist, hips, neck, height_cm]): return None, None
        bf = 495 / (1.29579 - 0.35004 * (waist + hips - neck) / 2.54 + 0.22100 * height_cm / 2.54) - 450
    bf = round(bf, 1)
    if gender == 'м':
        if bf < 6:
            cat = "Соревновательный 🏆"
        elif bf < 14:
            cat = "Атлетический 💪"
        elif bf < 18:
            cat = "Фитнес 🏃"
        elif bf < 25:
            cat = "Средний 📊"
        else:
            cat = "Выше среднего ⚠️"
    else:
        if bf < 14:
            cat = "Соревновательный 🏆"
        elif bf < 21:
            cat = "Атлетический 💪"
        elif bf < 25:
            cat = "Фитнес 🏃"
        elif bf < 32:
            cat = "Средний 📊"
        else:
            cat = "Выше среднего ⚠️"
    return bf, cat


def export_to_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df = pd.read_sql_query('''SELECT date as 'Дата', weight as 'Вес', bmi as 'ИМТ',
            category as 'Категория' FROM measurements ORDER BY date''', conn)
        if not df.empty: df.to_excel(writer, sheet_name='Замеры веса', index=False)

        df = pd.read_sql_query('''SELECT date as 'Дата', waist as 'Талия', hips as 'Бёдра',
            chest as 'Грудь', whr as 'WHR', body_fat as '% жира' FROM body_measurements ORDER BY date''', conn)
        if not df.empty: df.to_excel(writer, sheet_name='Замеры тела', index=False)

        df = pd.read_sql_query('''SELECT date as 'Дата', exercise as 'Упражнение',
            sets as 'Подходы', reps as 'Повторения', weight_kg as 'Вес (кг)' FROM workouts ORDER BY date''', conn)
        if not df.empty: df.to_excel(writer, sheet_name='Тренировки', index=False)

        df = pd.read_sql_query('''SELECT SUBSTR(date, 1, 10) as 'День',
            SUM(volume_ml) as 'Выпито (мл)' FROM water
            GROUP BY SUBSTR(date, 1, 10) ORDER BY date''', conn)
        if not df.empty: df.to_excel(writer, sheet_name='Вода', index=False)

        df = pd.read_sql_query('''SELECT date as 'Дата', hours as 'Часов',
            quality as 'Качество' FROM sleep ORDER BY date''', conn)
        if not df.empty: df.to_excel(writer, sheet_name='Сон', index=False)

    output.seek(0)
    return output


# ============================================================================
# 🚀 ГЛАВНАЯ ЛОГИКА ПРИЛОЖЕНИЯ
# ============================================================================

profile = get_profile()

# ============================================================================
# 📝 ЭКРАН ПЕРВИЧНОЙ НАСТРОЙКИ (если профиль пуст)
# ============================================================================
if profile is None:
    set_background("🌌 Градиент (по умолчанию)")

    st.markdown("""
    <div style='text-align: center; padding: 40px 20px;'>
        <h1 style='color: #2c5f8d;'>🏥 Добро пожаловать в Health Platform 360°!</h1>
        <p style='color: #555; font-size: 18px;'>Давай познакомимся и настроим твой персональный помощник</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📝 Заполни свой профиль")
    st.caption("Эти данные будут использоваться во всех разделах приложения")

    col1, col2 = st.columns(2)
    with col1:
        surname = st.text_input("👤 Фамилия", placeholder="Иванов")
        name = st.text_input("👤 Имя", placeholder="Иван")
        birth_date = st.date_input("🎂 Дата рождения", value=date(1990, 1, 1),
                                   min_value=date(1920, 1, 1), max_value=date.today())
        gender = st.radio("⚧ Пол", ["м", "ж"], horizontal=True)

    with col2:
        height = st.number_input("📏 Рост (см)", 100.0, 250.0, 170.0, 0.1)
        weight = st.number_input("⚖️ Текущий вес (кг)", 30.0, 300.0, 70.0, 0.1)
        target_weight = st.number_input("🎯 Целевой вес (кг)", 30.0, 300.0, 65.0, 0.1)
        activity = st.selectbox("🏃 Уровень активности",
                                ["Сидячий", "Умеренный", "Активный", "Очень активный"])

    background = st.selectbox("🎨 Выбери фон приложения", list(BACKGROUNDS.keys()))

    if st.button("🚀 Начать!", type="primary", use_container_width=True):
        if not surname or not name:
            st.error("❌ Заполни имя и фамилию!")
        else:
            save_profile(surname, name, birth_date.strftime("%d.%m.%Y"), gender,
                         height, weight, target_weight, activity, background)
            st.success("✅ Профиль создан! Добро пожаловать!")
            st.balloons()
            st.rerun()

    st.stop()

# ============================================================================
# 🏠 ОСНОВНОЕ ПРИЛОЖЕНИЕ (профиль есть)
# ============================================================================

# Распаковываем профиль
_, surname, name, birth_date_str, gender, height_cm, weight, target_weight, activity, background, last_weigh_date = profile

try:
    birth_date = datetime.strptime(birth_date_str, "%d.%m.%Y").date()
except:
    birth_date = date(1990, 1, 1)

age = calculate_age(birth_date)

# Применяем фон
set_background(background)

# Боковое меню
st.sidebar.markdown(f"## 🏥 Health Platform 360°")
st.sidebar.markdown(f"### 👋 Привет, {name}!")
st.sidebar.caption(f"🎂 {age} лет | ⚧ {'М' if gender == 'м' else 'Ж'}")
st.sidebar.caption(f"📏 {height_cm} см | ⚖️ {weight} кг")
st.sidebar.markdown("---")

section = st.sidebar.radio("📋 Раздел", [
    "🏠 Главная", "👤 Профиль", "📏 Замеры тела", "🥗 Питание",
    "💪 Тренировки", "💧 Вода", "😴 Сон", "📊 История", "⚙️ Настройки"
])

# ============================================================================
# 🏠 ГЛАВНАЯ (с мотивацией и напоминанием)
# ============================================================================
if section == "🏠 Главная":
    st.warning("⚠️ Приложение носит информационный характер и не заменяет консультацию врача.")

    # Мотивационная фраза
    if 'quote' not in st.session_state:
        st.session_state.quote = get_random_quote()

    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 15px; text-align: center; color: white;'>
        <h2 style='margin: 0;'>👋 Привет, {name}!</h2>
        <p style='font-size: 20px; margin: 10px 0;'>{st.session_state.quote}</p>
        <button onclick="window.location.reload()" style='background: white; color: #667eea; 
                padding: 8px 20px; border: none; border-radius: 20px; cursor: pointer; font-weight: bold;'>
            🔄 Новая мотивация
        </button>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 🔔 Напоминание о замерах
    need_reminder, reminder_msg = check_reminder(last_weigh_date)

    if need_reminder:
        play_reminder_sound()
        st.balloons()
        st.markdown(f"""
        <div style='background: #FFC107; padding: 20px; border-radius: 15px; 
                    border-left: 8px solid #FF9800;'>
            <h2 style='margin: 0; color: #333;'>🔔 ВРЕМЯ ЗАМЕРОВ!</h2>
            <p style='font-size: 18px; margin: 10px 0; color: #333;'>{reminder_msg}</p>
            <p style='color: #555;'>💡 Регулярные замеры помогают отслеживать прогресс и корректировать программу.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⚖️ Внести вес", use_container_width=True):
                st.session_state.quick_weigh = True
                st.rerun()
        with col2:
            if st.button("📏 Замеры тела", use_container_width=True):
                st.session_state.go_to_body = True
                st.rerun()
        with col3:
            if st.button("🔄 Новая мотивация", use_container_width=True):
                st.session_state.quote = get_random_quote()
                st.rerun()
    else:
        st.success(f"✅ {reminder_msg}")
        if st.button("🔄 Новая мотивация"):
            st.session_state.quote = get_random_quote()
            st.rerun()

    st.markdown("---")

    # Быстрый ввод веса (если нажали кнопку)
    if st.session_state.get('quick_weigh'):
        st.markdown("### ⚖️ Быстрый ввод веса")
        new_weight = st.number_input("Новый вес (кг)", 30.0, 300.0, weight, 0.1, key="quick_w")
        if st.button("💾 Сохранить вес", type="primary"):
            height_m = height_cm / 100
            bmi = round(new_weight / (height_m ** 2), 1)
            norm_min, norm_max = get_age_norm(age)
            if bmi < norm_min:
                cat = "Недостаточный вес"
            elif bmi <= norm_max:
                cat = "Норма"
            elif bmi < 30:
                cat = "Избыточный вес"
            else:
                cat = "Ожирение"

            cursor = conn.cursor()
            cursor.execute('''INSERT INTO measurements (date, weight, bmi, category)
                VALUES (?, ?, ?, ?)''',
                           (datetime.now().strftime("%d.%m.%Y %H:%M"), new_weight, bmi, cat))
            conn.commit()

            # Обновляем профиль
            save_profile(surname, name, birth_date_str, gender, height_cm,
                         new_weight, target_weight, activity, background)

            st.success(f"✅ Вес {new_weight} кг сохранён! ИМТ: {bmi}")
            st.session_state.quick_weigh = False
            st.balloons()
            st.rerun()

    # Быстрые показатели
    st.markdown("### 📊 Твои текущие показатели")
    height_m = height_cm / 100
    bmi = round(weight / (height_m ** 2), 1)
    norm_min, norm_max = get_age_norm(age)
    cal_m, cal_l = calculate_calories(gender, weight, height_cm, age, activity)
    water_ml = calculate_water(weight, activity)
    sleep_min, sleep_max, _ = SLEEP_BY_AGE[get_sleep_group(age)]
    ideal_weight = round(calculate_ideal_weight(gender, height_cm / 2.54, get_age_factor(age)), 1)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📊 ИМТ", f"{bmi}")
    c2.metric("🔥 Калории", f"{cal_l} ккал")
    c3.metric("💧 Вода", f"{water_ml} мл")
    c4.metric("😴 Сон", f"{sleep_min}-{sleep_max} ч")
    c5.metric("⚖️ Идеал", f"{ideal_weight} кг")

    # Динамика веса
    df = pd.read_sql_query('''SELECT date as 'Дата', weight as 'Вес' FROM measurements
        ORDER BY date DESC LIMIT 10''', conn)
    if not df.empty and len(df) >= 2:
        st.markdown("### 📈 Динамика веса")
        st.line_chart(df[['Дата', 'Вес']].set_index('Дата'))

# ============================================================================
# 👤 ПРОФИЛЬ
# ============================================================================
elif section == "👤 Профиль":
    st.markdown("<h1>👤 Мой профиль</h1>", unsafe_allow_html=True)
    st.caption("Эти данные используются во всех разделах приложения")

    col1, col2 = st.columns(2)
    with col1:
        new_surname = st.text_input("Фамилия", value=surname)
        new_name = st.text_input("Имя", value=name)
        new_birth = st.date_input("Дата рождения", value=birth_date,
                                  min_value=date(1920, 1, 1), max_value=date.today())
        new_gender = st.radio("Пол", ["м", "ж"], horizontal=True,
                              index=0 if gender == 'м' else 1)

    with col2:
        new_height = st.number_input("Рост (см)", 100.0, 250.0, height_cm, 0.1)
        new_weight = st.number_input("Текущий вес (кг)", 30.0, 300.0, weight, 0.1)
        new_target = st.number_input("Целевой вес (кг)", 30.0, 300.0, target_weight, 0.1)
        new_activity = st.selectbox("Активность",
                                    ["Сидячий", "Умеренный", "Активный", "Очень активный"],
                                    index=["Сидячий", "Умеренный", "Активный", "Очень активный"].index(activity))

    if st.button("💾 Сохранить изменения", type="primary"):
        save_profile(new_surname, new_name, new_birth.strftime("%d.%m.%Y"), new_gender,
                     new_height, new_weight, new_target, new_activity, background)
        st.success("✅ Профиль обновлён!")
        st.rerun()

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

    if st.session_state.get('go_to_body'):
        st.info("👇 Заполни замеры ниже")
        st.session_state.go_to_body = False

    st.markdown("---")
    st.markdown("### 📝 Ввести новые замеры")

    c1, c2, c3 = st.columns(3)
    with c1:
        waist = st.number_input("🎯 Талия (см)", 40.0, 200.0, 75.0, 0.5)
        hips = st.number_input("🍑 Бёдра (см)", 50.0, 200.0, 95.0, 0.5)
        chest = st.number_input("👚 Грудь (см)", 50.0, 200.0, 90.0, 0.5)
    with c2:
        neck = st.number_input("🦢 Шея (см)", 20.0, 60.0, 35.0, 0.5)
        arm = st.number_input("💪 Рука (см)", 15.0, 60.0, 28.0, 0.5)
    with c3:
        st.markdown("**Как измерять:**")
        st.markdown("""
        - 🎯 **Талия** — в самом узком месте, на уровне пупка
        - 🍑 **Бёдра** — в самом широком месте ягодиц
        - 👚 **Грудь** — по самым выступающим точкам
        - 🦢 **Шея** — под кадыком
        - 💪 **Рука** — в самом широком месте бицепса
        """)

    # Мгновенный расчёт
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

        # Рекомендации
        if whr_cat and "Высокий" in whr_cat:
            st.error("🔴 Высокий WHR — повышенный риск ССЗ. Увеличь аэробную нагрузку и снизь простые углеводы.")
        elif whr_cat and "Умеренный" in whr_cat:
            st.warning("🟡 Умеренный WHR — стоит обратить внимание на питание.")
        else:
            st.success("🟢 WHR в норме!")

    if st.button("💾 Сохранить замеры", type="primary"):
        if waist and hips:
            whr, whr_cat = calculate_whr(waist, hips, gender)
            bf, bf_cat = calculate_body_fat_navy(waist, hips, neck, height_cm, gender)

            cursor = conn.cursor()
            cursor.execute('''INSERT INTO body_measurements 
                (date, waist, hips, chest, neck, arm, whr, whr_category, body_fat, body_fat_category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (datetime.now().strftime("%d.%m.%Y %H:%M"),
                            waist, hips, chest, neck, arm, whr, whr_cat, bf, bf_cat))
            conn.commit()
            st.success("✅ Замеры сохранены!")
            st.balloons()

    st.markdown("---")
    st.markdown("### 📈 История замеров")
    df = pd.read_sql_query('''SELECT date as 'Дата', waist as 'Талия', hips as 'Бёдра',
        chest as 'Грудь', whr as 'WHR', body_fat as '% жира' FROM body_measurements
        ORDER BY date DESC LIMIT 14''', conn)

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        chart_df = df[['Дата', 'Талия', 'Бёдра', 'Грудь']].set_index('Дата')
        st.line_chart(chart_df)
    else:
        st.info("Пока нет записей. Сделайте первый замер!")

# ============================================================================
# 🥗 ПИТАНИЕ
# ============================================================================
elif section == "🥗 Питание":
    st.markdown("<h1>🥗 Персональное питание</h1>", unsafe_allow_html=True)

    age_group = get_age_group(age)
    cal_m, cal_l = calculate_calories(gender, weight, height_cm, age, activity)
    norms = NUTRITION_BY_AGE[age_group]

    st.info(f"🤖 **Рекомендация формулы:** {cal_l} ккал/день (безопасный дефицит 500 ккал)")

    custom_calories = st.number_input(
        "✏️ Моя целевая калорийность (ккал):",
        min_value=800, max_value=4000, value=cal_l, step=50
    )

    if custom_calories < 1200:
        st.warning("⚠️ **ВАЖНО:** Менее 1200 ккал — ниже безопасного минимума ВОЗ. Проконсультируйтесь с врачом!")
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
                    (date, exercise, sets, reps, weight_kg, notes)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                               (datetime.now().strftime("%d.%m.%Y %H:%M"),
                                exercise, sets, reps, weight_kg, notes))
                conn.commit()
                st.success(f"✅ Записано: {exercise} — {sets}x{reps}")
                st.balloons()

    st.markdown("---")
    st.markdown("### 📖 История")
    df = pd.read_sql_query('''SELECT date as 'Дата', exercise as 'Упражнение',
        sets as 'Подходы', reps as 'Повторения', weight_kg as 'Вес (кг)'
        FROM workouts ORDER BY date DESC LIMIT 20''', conn)

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Пока нет записей")

# ============================================================================
# 💧 ВОДА
# ============================================================================
elif section == "💧 Вода":
    st.markdown("<h1>💧 Водный баланс</h1>", unsafe_allow_html=True)

    daily_goal = calculate_water(weight, activity)
    st.markdown(f"### 🎯 Норма: **{daily_goal} мл** ({round(daily_goal / 250, 1)} стаканов)")

    today = datetime.now().strftime("%d.%m.%Y")
    df_today = pd.read_sql_query('''SELECT SUM(volume_ml) as total FROM water
        WHERE date LIKE ?''', conn, params=(f"{today}%",))
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
            cursor.execute('''INSERT INTO water (date, glasses, volume_ml, goal_ml)
                VALUES (?, ?, ?, ?)''',
                           (datetime.now().strftime("%d.%m.%Y %H:%M"),
                            glasses, glasses * vol, daily_goal))
            conn.commit()
            st.success(f"✅ Записано: {glasses * vol} мл")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📊 История")
    df_hist = pd.read_sql_query('''SELECT SUBSTR(date, 1, 10) as 'День', 
        SUM(volume_ml) as 'Выпито (мл)' FROM water
        GROUP BY SUBSTR(date, 1, 10) ORDER BY date DESC LIMIT 14''', conn)
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
                (date, bedtime, wake_time, hours, quality, notes)
                VALUES (?, ?, ?, ?, ?, ?)''',
                           (datetime.now().strftime("%d.%m.%Y %H:%M"),
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
        hours as 'Часов', quality as 'Качество' FROM sleep ORDER BY date DESC LIMIT 14''', conn)
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
            category as 'Категория' FROM measurements ORDER BY date DESC''', conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            if len(df) >= 2:
                st.line_chart(df[['Дата', 'Вес']].set_index('Дата'))
        else:
            st.info("Нет записей")

    with tab2:
        df = pd.read_sql_query('''SELECT date as 'Дата', waist as 'Талия', hips as 'Бёдра',
            chest as 'Грудь', whr as 'WHR', body_fat as '% жира' FROM body_measurements
            ORDER BY date DESC LIMIT 30''', conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            chart = df[['Дата', 'Талия', 'Бёдра', 'Грудь']].set_index('Дата')
            st.line_chart(chart)
        else:
            st.info("Нет записей")

    with tab3:
        df = pd.read_sql_query('''SELECT date as 'Дата', exercise as 'Упражнение',
            sets as 'Подх', reps as 'Повт', weight_kg as 'Вес' FROM workouts
            ORDER BY date DESC LIMIT 30''', conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Нет записей")

    with tab4:
        df = pd.read_sql_query('''SELECT SUBSTR(date, 1, 10) as 'День',
            SUM(volume_ml) as 'Всего (мл)' FROM water
            GROUP BY SUBSTR(date, 1, 10) ORDER BY date DESC LIMIT 14''', conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.line_chart(df.set_index('День'))
        else:
            st.info("Нет записей")

    with tab5:
        df = pd.read_sql_query('''SELECT date as 'Дата', hours as 'Часов',
            quality as 'Качество' FROM sleep ORDER BY date DESC LIMIT 14''', conn)
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
                          index=list(BACKGROUNDS.keys()).index(background))
    if st.button("💾 Применить фон"):
        save_profile(surname, name, birth_date_str, gender, height_cm, weight,
                     target_weight, activity, new_bg)
        st.success("✅ Фон изменён!")
        st.rerun()

    st.markdown("---")

    # Экспорт в Excel
    st.markdown("### 📊 Экспорт всей истории в Excel")
    st.caption("Скачайте полную историю всех замеров в одном файле.")

    if st.button("📥 Сформировать Excel-отчёт", type="primary"):
        excel_file = export_to_excel()
        st.download_button(
            label="💾 Скачать файл",
            data=excel_file,
            file_name=f"health_report_{surname}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.success("✅ Файл готов!")

    st.markdown("---")

    # PWA
    st.markdown("### 📱 Установить как приложение (PWA)")
    st.markdown("""
    **На iPhone (Safari):**
    1. Откройте приложение в Safari
    2. Нажмите "Поделиться" → "На экран «Домой»"
    3. Нажмите "Добавить"

    **На Android (Chrome):**
    1. Откройте приложение в Chrome
    2. Нажмите меню (⋮) → "Добавить на главный экран"
    3. Нажмите "Установить"
    """)

    st.markdown("---")

    # Сброс
    st.markdown("### ⚠️ Опасная зона")
    if st.button("🗑️ Сбросить все данные"):
        st.warning("Это удалит ВСЕ ваши данные. Вы уверены?")
        if st.button("❗ ДА, удалить всё"):
            cursor = conn.cursor()
            cursor.execute('DELETE FROM measurements')
            cursor.execute('DELETE FROM body_measurements')
            cursor.execute('DELETE FROM workouts')
            cursor.execute('DELETE FROM water')
            cursor.execute('DELETE FROM sleep')
            cursor.execute('DELETE FROM profile')
            conn.commit()
            st.success("Все данные удалены. Перезагрузите страницу.")