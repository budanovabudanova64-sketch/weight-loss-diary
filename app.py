# ============================================================================
# 🏥 HEALTH PLATFORM 360° — Комплексная платформа здоровья
# ============================================================================

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
import re

st.set_page_config(page_title="Health Platform 360°", page_icon="🏥", layout="wide")


# ============================================================================
# 1. БАЗА ДАННЫХ (4 таблицы)
# ============================================================================
@st.cache_resource
def init_db():
    conn = sqlite3.connect('health_platform_v3.db', check_same_thread=False)
    c = conn.cursor()

    # Таблица основных замеров
    c.execute('''CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, surname TEXT, name TEXT, birth_date TEXT,
        gender TEXT, height REAL, weight REAL, target_weight REAL,
        activity TEXT, bmi REAL, category TEXT, ideal_weight REAL,
        calories_maintain INT, calories_lose INT, protein REAL, fat REAL, carbs REAL
    )''')

    # Тренировочный дневник
    c.execute('''CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, surname TEXT, name TEXT, birth_date TEXT,
        exercise TEXT, sets INT, reps INT, weight_kg REAL, notes TEXT
    )''')

    # Трекер воды
    c.execute('''CREATE TABLE IF NOT EXISTS water (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, surname TEXT, name TEXT, birth_date TEXT,
        glasses INT, volume_ml REAL, goal_ml REAL
    )''')

    # Трекер сна
    c.execute('''CREATE TABLE IF NOT EXISTS sleep (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, surname TEXT, name TEXT, birth_date TEXT,
        bedtime TEXT, wake_time TEXT, hours REAL, quality TEXT, notes TEXT
    )''')

    conn.commit()
    return conn


conn = init_db()

# ============================================================================
# 2. МЕДИЦИНСКИЕ ДАННЫЕ (по возрастам и ВОЗ)
# ============================================================================

# Нормы БЖУ по возрастам (г на кг веса) — данные ВОЗ и Российских рекомендаций
NUTRITION_BY_AGE = {
    '18-29': {'protein': (1.0, 1.3), 'fat': (0.8, 1.0), 'carbs': (3.0, 4.0), 'fiber': 25},
    '30-49': {'protein': (1.0, 1.2), 'fat': (0.8, 1.0), 'carbs': (3.0, 4.0), 'fiber': 25},
    '50-64': {'protein': (1.0, 1.2), 'fat': (0.7, 0.9), 'carbs': (2.5, 3.5), 'fiber': 30},
    '65+': {'protein': (1.2, 1.5), 'fat': (0.7, 0.9), 'carbs': (2.5, 3.5), 'fiber': 30},
}

# Рекомендации ВОЗ по физической нагрузке
ACTIVITY_BY_AGE = {
    '18-64': {
        'aerobic': '150-300 мин умеренной ИЛИ 75-150 мин интенсивной в неделю',
        'strength': 'Силовые тренировки 2+ раза в неделю на все группы мышц',
        'examples': ['Ходьба быстрым шагом', 'Плавание', 'Велосипед', 'Танцы', 'Бег трусцой']
    },
    '65+': {
        'aerobic': '150-300 мин умеренной активности в неделю',
        'strength': 'Силовые 2+ раза в неделю + упражнения на БАЛАНС 3+ раза',
        'examples': ['Скандинавская ходьба', 'Тай-чи', 'Йога', 'Плавание', 'Гимнастика']
    }
}

# Нормы сна по возрастам (National Sleep Foundation)
SLEEP_BY_AGE = {
    '18-25': (7, 9, 'Оптимально 7-9 часов'),
    '26-64': (7, 9, 'Оптимально 7-9 часов'),
    '65+': (7, 8, 'Оптимально 7-8 часов'),
}

# Гликемический индекс (из прошлой версии)
GI_PRODUCTS = {
    'Низкий ГИ (≤55)': [('Гречка', 54), ('Овсянка', 55), ('Чечевица', 25), ('Яблоки', 38), ('Брокколи', 10),
                        ('Миндаль', 15), ('Творог', 30)],
    'Средний ГИ (56-69)': [('Рис басмати', 58), ('Цельнозерновой хлеб', 65), ('Бананы', 60), ('Свёкла варёная', 64)],
    'Высокий ГИ (≥70)': [('Белый хлеб', 75), ('Белый рис', 83), ('Картофель фри', 75), ('Финики', 103), ('Пиво', 110),
                         ('Сахар', 68)]
}

# ============================================================================
# 3. ФУНКЦИИ РАСЧЁТА
# ============================================================================
AGE_NORMS = [(25, 19, 24), (35, 20, 25), (45, 21, 26), (55, 22, 27), (65, 23, 28)]
AGE_FACTORS = [(30, 1.0), (40, 1.02), (50, 1.04), (60, 1.06), (float('inf'), 1.08)]


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
    """Расчёт нормы воды: 30 мл/кг + поправка на активность"""
    base = weight * 30
    bonus = {'Сидячий': 0, 'Умеренный': 500, 'Активный': 1000, 'Очень активный': 1500}
    return int(base + bonus[activity])


# ============================================================================
# 4. БОКОВОЕ МЕНЮ НАВИГАЦИИ
# ============================================================================
st.sidebar.markdown("## 🏥 Health Platform 360°")
st.sidebar.markdown("---")
section = st.sidebar.radio("📋 Раздел", [
    "🏠 Главная",
    "🥗 Питание",
    "💪 Тренировки",
    "💧 Вода",
    "😴 Сон",
    "📊 История"
])

# ============================================================================
# 5. ОБЩИЙ БЛОК ПРОФИЛЯ (используется везде)
# ============================================================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 👤 Твой профиль")
with st.sidebar:
    surname = st.text_input("Фамилия", placeholder="Иванов").strip().capitalize()
    name = st.text_input("Имя", placeholder="Иван").strip().capitalize()
    birth_date = st.date_input("Дата рождения", value=date(1990, 1, 1),
                               min_value=date(1920, 1, 1), max_value=date.today())
    gender = st.radio("Пол", ["м", "ж"], horizontal=True)
    height_cm = st.number_input("Рост (см)", 100.0, 250.0, 170.0, 0.1)
    weight = st.number_input("Текущий вес (кг)", 30.0, 300.0, 70.0, 0.1)
    target_weight = st.number_input("Целевой вес (кг)", 30.0, 300.0, 65.0, 0.1)
    activity = st.selectbox("Активность", ["Сидячий", "Умеренный", "Активный", "Очень активный"])

# ============================================================================
# 6. РАЗДЕЛ: 🏠 ГЛАВНАЯ
# ============================================================================
if section == "🏠 Главная":
    st.warning("⚠️ **Внимание:** Приложение носит информационный характер и не заменяет консультацию врача.")
    st.markdown("<h1 style='text-align:center;'>🏥 HEALTH PLATFORM 360°</h1>", unsafe_allow_html=True)
    st.markdown("### Твой персональный помощник для комплексного управления здоровьем")

    if surname and name:
        age = calculate_age(birth_date)
        st.info(f"👋 Привет, **{name}**! Тебе **{age} лет**. Выбери раздел слева для работы.")

        # Быстрые расчёты
        height_m = height_cm / 100
        bmi = round(weight / (height_m ** 2), 1)
        norm_min, norm_max = get_age_norm(age)
        cal_m, cal_l = calculate_calories(gender, weight, height_cm, age, activity)
        water_ml = calculate_water(weight, activity)
        sleep_min, sleep_max, sleep_text = SLEEP_BY_AGE[get_sleep_group(age)]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 ИМТ", bmi)
        c2.metric("🔥 Калории", f"{cal_l} ккал")
        c3.metric("💧 Вода", f"{water_ml} мл")
        c4.metric("😴 Сон", f"{sleep_min}-{sleep_max} ч")

        if bmi < norm_min:
            cat = "Недостаточный вес"
        elif bmi <= norm_max:
            cat = "Норма"
        elif bmi < 30:
            cat = "Избыточный вес"
        else:
            cat = "Ожирение"
        st.success(f"📋 Твоя категория: **{cat}**")
    else:
        st.warning("⬅️ Заполни профиль в боковом меню слева")

# ============================================================================
# 7. РАЗДЕЛ: 🥗 ПИТАНИЕ (УГЛУБЛЁННОЕ)
# ============================================================================
elif section == "🥗 Питание":
    st.markdown("<h1>🥗 Персональное питание</h1>", unsafe_allow_html=True)

    if not (surname and name):
        st.warning("⬅️ Заполни профиль слева")
    else:
        age = calculate_age(birth_date)
        age_group = get_age_group(age)
        cal_m, cal_l = calculate_calories(gender, weight, height_cm, age, activity)
        norms = NUTRITION_BY_AGE[age_group]

        # Расчёт БЖУ
        protein_min = round(weight * norms['protein'][0], 1)
        protein_max = round(weight * norms['protein'][1], 1)
        fat_min = round(weight * norms['fat'][0], 1)
        fat_max = round(weight * norms['fat'][1], 1)
        carbs_min = round(weight * norms['carbs'][0], 1)
        carbs_max = round(weight * norms['carbs'][1], 1)

        st.markdown(f"### 📊 Твоя норма калорий и БЖУ (возрастная группа: **{age_group}**)")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔥 Калории", f"{cal_l} ккал", "для похудения")
        c2.metric("🥩 Белки", f"{protein_min}-{protein_max} г")
        c3.metric("🥑 Жиры", f"{fat_min}-{fat_max} г")
        c4.metric("🍞 Углеводы", f"{carbs_min}-{carbs_max} г")

        tab1, tab2, tab3, tab4 = st.tabs(["📋 Принципы", "✅ Что есть", "❌ Что исключить", "📊 Таблица ГИ"])

        with tab1:
            st.markdown(f"### 🎯 Возрастные особенности ({age_group} лет)")
            if age_group == '18-29':
                st.info("🔥 Метаболизм на пике. Важно сформировать здоровые привычки на всю жизнь.")
            elif age_group == '30-49':
                st.info("⚠️ Метаболизм начинает замедляться. Увеличь долю белка, следи за сахаром.")
            elif age_group == '50-64':
                st.info("🦴 Важно: кальций, витамин D, омега-3. Снизь соль и насыщенные жиры.")
            else:
                st.info("👴 Нужно БОЛЬШЕ белка (1.2-1.5 г/кг) для сохранения мышц. Кальций и B12 критичны.")

            st.markdown(f"""
            **Общие принципы твоего возраста:**
            - 💧 Вода: **{calculate_water(weight, activity)} мл** в день
            - 🥦 Клетчатка: **{norms['fiber']} г** в день (овощи, цельные злаки)
            - 🧂 Соль: не более **5 г** в день (ВОЗ)
            - 🍬 Сахар: не более **25 г** добавленного сахара в день (ВОЗ)
            - 🍽️ Режим: 3 основных приёма + 1-2 перекуса
            """)

        with tab2:
            st.markdown("### ✅ Рекомендуемые продукты")
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
            st.markdown("### ❌ Что исключить или минимизировать")
            st.markdown("""
            - 🍞 **Белый хлеб, выпечка** (ГИ 75+) → замени на цельнозерновой
            - 🍟 **Жареное, фастфуд** → готовь на пару, запекай
            - 🍬 **Сладости, газировки** → фрукты, ягоды, вода
            - 🥓 **Переработанное мясо** (сосиски, колбаса) → свежее мясо, рыба
            - 🍺 **Алкоголь** — пустые калории + вред для сна
            - 🧂 **Избыток соли** — провоцирует отёки и гипертонию
            """)

        with tab4:
            st.markdown("### 📊 Гликемический индекс продуктов")
            for level, products in GI_PRODUCTS.items():
                st.markdown(f"#### {level}")
                df = pd.DataFrame(products, columns=['Продукт', 'ГИ'])
                st.dataframe(df, use_container_width=True, hide_index=True)

# ============================================================================
# 8. РАЗДЕЛ: 💪 ТРЕНИРОВКИ
# ============================================================================
elif section == "💪 Тренировки":
    st.markdown("<h1>💪 Тренировочный дневник</h1>", unsafe_allow_html=True)

    if not (surname and name):
        st.warning("⬅️ Заполни профиль слева")
    else:
        age = calculate_age(birth_date)
        act_group = get_activity_group(age)
        rec = ACTIVITY_BY_AGE[act_group]

        st.markdown(f"### 📋 Рекомендации ВОЗ для возраста **{age} лет** ({act_group})")
        st.info(f"""
        🏃 **Аэробная нагрузка:** {rec['aerobic']}  
        🏋️ **Силовая:** {rec['strength']}
        """)
        st.markdown("**Примеры активности:** " + ", ".join(rec['examples']))

        st.markdown("---")
        st.markdown("### 📝 Записать тренировку")

        c1, c2, c3 = st.columns(3)
        with c1:
            exercise = st.text_input("Упражнение", placeholder="Приседания")
            sets = st.number_input("Подходы", 1, 20, 3)
        with c2:
            reps = st.number_input("Повторения", 1, 100, 12)
            weight_kg = st.number_input("Вес (кг)", 0.0, 500.0, 0.0, 0.5)
        with c3:
            notes = st.text_input("Заметки (опционально)")
            if st.button("💾 Сохранить тренировку", type="primary", use_container_width=True):
                if exercise:
                    cursor = conn.cursor()
                    cursor.execute('''INSERT INTO workouts 
                        (date, surname, name, birth_date, exercise, sets, reps, weight_kg, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                   (datetime.now().strftime("%d.%m.%Y %H:%M"), surname, name,
                                    birth_date.strftime("%d.%m.%Y"), exercise, sets, reps, weight_kg, notes))
                    conn.commit()
                    st.success(f"✅ Записано: {exercise} — {sets}x{reps}")

        st.markdown("---")
        st.markdown("### 📖 История твоих тренировок")
        df = pd.read_sql_query('''SELECT date as 'Дата', exercise as 'Упражнение',
            sets as 'Подходы', reps as 'Повторения', weight_kg as 'Вес (кг)', notes as 'Заметки'
            FROM workouts WHERE surname=? AND name=? AND birth_date=?
            ORDER BY date DESC LIMIT 20''', conn,
                               params=(surname, name, birth_date.strftime("%d.%m.%Y")))

        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Пока нет записей. Начни свою первую тренировку!")

# ============================================================================
# 9. РАЗДЕЛ: 💧 ВОДА
# ============================================================================
elif section == "💧 Вода":
    st.markdown("<h1>💧 Водный баланс</h1>", unsafe_allow_html=True)

    if not (surname and name):
        st.warning("⬅️ Заполни профиль слева")
    else:
        daily_goal = calculate_water(weight, activity)
        glasses_ml = 250  # объём одного стакана

        st.markdown(f"### 🎯 Твоя дневная норма: **{daily_goal} мл** ({round(daily_goal / glasses_ml, 1)} стаканов)")
        st.caption("Расчёт: 30 мл на кг веса + поправка на активность")

        # Прогресс-бар
        today = datetime.now().strftime("%d.%m.%Y")
        df_today = pd.read_sql_query('''SELECT SUM(volume_ml) as total FROM water
            WHERE surname=? AND name=? AND birth_date=? AND date LIKE ?''', conn,
                                     params=(surname, name, birth_date.strftime("%d.%m.%Y"), f"{today}%"))
        drunk = int(df_today['total'].iloc[0] or 0)

        progress = min(drunk / daily_goal, 1.0)
        st.progress(progress, text=f"Выпито сегодня: {drunk} мл из {daily_goal} мл ({int(progress * 100)}%)")

        if progress >= 1.0:
            st.success("🎉 Дневная норма выполнена! Отличная работа!")
        elif progress >= 0.7:
            st.info("💪 Осталось немного. Продолжай!")

        st.markdown("---")
        st.markdown("### 🥤 Добавить стакан воды")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            glasses = st.number_input("Стаканов", 1, 20, 1)
        with c2:
            vol = st.number_input("Объём (мл)", 100, 1000, 250, 50)
        with c3:
            if st.button("💧 Выпить", type="primary", use_container_width=True):
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO water (date, surname, name, birth_date, glasses, volume_ml, goal_ml)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                               (datetime.now().strftime("%d.%m.%Y %H:%M"), surname, name,
                                birth_date.strftime("%d.%m.%Y"), glasses, glasses * vol, daily_goal))
                conn.commit()
                st.success(f"✅ Записано: {glasses * vol} мл")
                st.rerun()

        st.markdown("---")
        st.markdown("### 📊 История по дням")
        df_hist = pd.read_sql_query('''SELECT SUBSTR(date, 1, 10) as 'День', 
            SUM(volume_ml) as 'Выпито (мл)', MAX(goal_ml) as 'Норма (мл)'
            FROM water WHERE surname=? AND name=? AND birth_date=?
            GROUP BY SUBSTR(date, 1, 10) ORDER BY date DESC LIMIT 14''', conn,
                                    params=(surname, name, birth_date.strftime("%d.%m.%Y")))
        if not df_hist.empty:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            chart = df_hist.set_index('День')
            st.line_chart(chart)

# ============================================================================
# 10. РАЗДЕЛ: 😴 СОН
# ============================================================================
elif section == "😴 Сон":
    st.markdown("<h1>😴 Трекер сна</h1>", unsafe_allow_html=True)

    if not (surname and name):
        st.warning("⬅️ Заполни профиль слева")
    else:
        age = calculate_age(birth_date)
        sl_group = get_sleep_group(age)
        sl_min, sl_max, sl_text = SLEEP_BY_AGE[sl_group]

        st.markdown(f"### 🎯 Твоя норма сна: **{sl_min}-{sl_max} часов** ({sl_text})")

        st.markdown("---")
        st.markdown("### 📝 Записать сон")
        c1, c2, c3 = st.columns(3)
        with c1:
            bedtime = st.time_input("Во сколько лёг", value=None)
        with c2:
            wake_time = st.time_input("Во сколько встал", value=None)
        with c3:
            quality = st.selectbox("Качество сна", ["Отличное 😴", "Хорошее 🙂", "Нормальное 😐", "Плохое 😫"])
        notes = st.text_input("Заметки (кофе поздно, стресс и т.д.)")

        if st.button("💾 Сохранить сон", type="primary"):
            if bedtime and wake_time:
                # Расчёт часов
                bed_dt = datetime.combine(date.today(), bedtime)
                wake_dt = datetime.combine(date.today(), wake_time)
                if wake_dt <= bed_dt:
                    wake_dt += timedelta(days=1)
                hours = round((wake_dt - bed_dt).total_seconds() / 3600, 1)

                cursor = conn.cursor()
                cursor.execute('''INSERT INTO sleep 
                    (date, surname, name, birth_date, bedtime, wake_time, hours, quality, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                               (datetime.now().strftime("%d.%m.%Y %H:%M"), surname, name,
                                birth_date.strftime("%d.%m.%Y"), bedtime.strftime("%H:%M"),
                                wake_time.strftime("%H:%M"), hours, quality, notes))
                conn.commit()

                if sl_min <= hours <= sl_max:
                    st.success(f"✅ Отлично! Ты спал(а) **{hours} ч** — это в норме!")
                elif hours < sl_min:
                    st.warning(f"⚠️ Ты спал(а) **{hours} ч** — меньше нормы ({sl_min} ч)")
                else:
                    st.info(f"💤 Ты спал(а) **{hours} ч** — больше нормы")

        st.markdown("---")
        st.markdown("### 📊 История сна")
        df = pd.read_sql_query('''SELECT date as 'Дата', bedtime as 'Лёг', wake_time as 'Встал',
            hours as 'Часов', quality as 'Качество', notes as 'Заметки'
            FROM sleep WHERE surname=? AND name=? AND birth_date=?
            ORDER BY date DESC LIMIT 14''', conn,
                               params=(surname, name, birth_date.strftime("%d.%m.%Y")))
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            chart = df[['Дата', 'Часов']].set_index('Дата')
            st.line_chart(chart)

# ============================================================================
# 11. РАЗДЕЛ: 📊 ИСТОРИЯ
# ============================================================================
elif section == "📊 История":
    st.markdown("<h1>📊 Полная история</h1>", unsafe_allow_html=True)

    if not (surname and name):
        st.warning("⬅️ Заполни профиль слева")
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["⚖️ Замеры", "💪 Тренировки", "💧 Вода", "😴 Сон"])
        bd = birth_date.strftime("%d.%m.%Y")

        with tab1:
            df = pd.read_sql_query('''SELECT date as 'Дата', weight as 'Вес', bmi as 'ИМТ',
                category as 'Категория', calories_lose as 'Ккал' FROM measurements
                WHERE surname=? AND name=? AND birth_date=? ORDER BY date DESC''', conn,
                                   params=(surname, name, bd))
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                if len(df) >= 2:
                    st.line_chart(df[['Дата', 'Вес']].set_index('Дата'))
            else:
                st.info("Нет записей")

        with tab2:
            df = pd.read_sql_query('''SELECT date as 'Дата', exercise as 'Упражнение',
                sets as 'Подх', reps as 'Повт', weight_kg as 'Вес' FROM workouts
                WHERE surname=? AND name=? AND birth_date=? ORDER BY date DESC LIMIT 30''', conn,
                                   params=(surname, name, bd))
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Нет записей")

        with tab3:
            df = pd.read_sql_query('''SELECT SUBSTR(date, 1, 10) as 'День',
                SUM(volume_ml) as 'Всего (мл)' FROM water
                WHERE surname=? AND name=? AND birth_date=?
                GROUP BY SUBSTR(date, 1, 10) ORDER BY date DESC LIMIT 14''', conn,
                                   params=(surname, name, bd))
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.line_chart(df.set_index('День'))
            else:
                st.info("Нет записей")

        with tab4:
            df = pd.read_sql_query('''SELECT date as 'Дата', hours as 'Часов',
                quality as 'Качество' FROM sleep
                WHERE surname=? AND name=? AND birth_date=? ORDER BY date DESC LIMIT 14''', conn,
                                   params=(surname, name, bd))
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.line_chart(df[['Дата', 'Часов']].set_index('Дата'))
            else:
                st.info("Нет записей")