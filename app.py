# ============================================================================
# 🏋️ ДНЕВНИК ПОХУДЕНИЯ PRO — Веб-версия с Базой Данных и Калькулятором Калорий
# ============================================================================

import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import datetime, timedelta

# Настройка страницы
st.set_page_config(page_title="Дневник похудения PRO", page_icon="🏋️", layout="centered")


# ============================================================================
# 1. ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ (SQLite)
# ============================================================================
@st.cache_resource
def init_db():
    conn = sqlite3.connect('diary_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            surname TEXT,
            name TEXT,
            gender TEXT,
            age INT,
            height REAL,
            weight REAL,
            target_weight REAL,
            bmi REAL,
            category TEXT,
            ideal_weight REAL,
            calories_maintain INT,
            calories_lose INT
        )
    ''')
    conn.commit()
    return conn


conn = init_db()

# ============================================================================
# 2. МАТЕМАТИЧЕСКИЕ ФУНКЦИИ
# ============================================================================
AGE_NORMS = [(25, 19, 24), (35, 20, 25), (45, 21, 26), (55, 22, 27), (65, 23, 28)]
AGE_FACTORS = [(30, 1.0), (40, 1.02), (50, 1.04), (60, 1.06), (float('inf'), 1.08)]


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
    for name, (m_base, f_base, m_mult, f_mult) in formulas.items():
        base = m_base if gender == 'м' else f_base
        mult = m_mult if gender == 'м' else f_mult
        result = base + mult * (height_inches - 60)
        if name == 'hamwi': result *= age_factor
        results.append(result)
    return sum(results) / len(results)


def calculate_calories(gender, weight, height_cm, age, activity):
    """Формула Миффлина-Сан Жеора"""
    if gender == 'м':
        bmr = 10 * weight + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height_cm - 5 * age - 161

    multipliers = {'Сидячий (мало движения)': 1.2, 'Умеренный (1-3 раза в неделю)': 1.375,
                   'Активный (3-5 раз в неделю)': 1.55}
    maintain = int(bmr * multipliers[activity])
    lose = maintain - 500  # Безопасный дефицит 500 ккал
    return maintain, max(lose, 1200)  # Не ниже 1200 ккал для безопасности


# ============================================================================
# 3. ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# ============================================================================

# ДИСКЛЕЙМЕР (Идея 1)
st.warning(
    "⚠️ **Внимание:** Данное приложение носит исключительно информационный и учебный характер. Расчеты являются приблизительными и не заменяют консультацию врача-диетолога или эндокринолога.")

st.markdown("<h1 style='text-align: center; color: #2c5f8d;'>🏋️ ДНЕВНИК ПОХУДЕНИЯ PRO</h1>", unsafe_allow_html=True)
st.markdown("---")

# ВВОД ДАННЫХ
st.subheader("📝 Твои данные")
col1, col2 = st.columns(2)

with col1:
    surname = st.text_input("👤 Фамилия", placeholder="Иванов").strip().capitalize()
    name = st.text_input("👤 Имя", placeholder="Иван").strip().capitalize()
    gender = st.radio("⚧ Пол", ["м", "ж"], horizontal=True)
    age = st.number_input("🎂 Возраст (лет)", min_value=10, max_value=100, value=30)

with col2:
    height_cm = st.number_input("📏 Рост (см)", min_value=100.0, max_value=250.0, value=170.0, step=0.1)
    weight = st.number_input("⚖️ Текущий вес (кг)", min_value=30.0, max_value=300.0, value=70.0, step=0.1)
    target_weight = st.number_input("🎯 Целевой вес (кг)", min_value=30.0, max_value=300.0, value=65.0, step=0.1)
    activity = st.selectbox("🏃 Уровень активности",
                            ["Сидячий (мало движения)", "Умеренный (1-3 раза в неделю)", "Активный (3-5 раз в неделю)"])

# КНОПКА РАСЧЕТА
if st.button("🔢 РАССЧИТАТЬ И СОХРАНИТЬ", type="primary", use_container_width=True):
    if not surname or not name:
        st.error("❌ Пожалуйста, введите фамилию и имя!")
    else:
        # --- РАСЧЕТЫ ---
        height_m = height_cm / 100
        height_inches = height_cm / 2.54
        bmi = round(weight / (height_m ** 2), 1)

        norm_min, norm_max = get_age_norm(age)
        age_factor = get_age_factor(age)

        if bmi < norm_min:
            category, cat_color = "Недостаточный вес", "#2196F3"
        elif bmi <= norm_max:
            category, cat_color = "Норма", "#4CAF50"
        elif bmi < 30:
            category, cat_color = "Избыточный вес", "#FF9800"
        else:
            category, cat_color = "Ожирение", "#F44336"

        ideal_weight = round(calculate_ideal_weight(gender, height_inches, age_factor), 1)
        calories_maintain, calories_lose = calculate_calories(gender, weight, height_cm, age, activity)

        # --- УМНАЯ ЦЕЛЬ (Идея 2) ---
        diff = weight - target_weight
        if diff > 2:
            months = round(diff / 3, 1)  # Средний темп 3 кг в месяц
            target_date = datetime.now() + timedelta(days=int(months * 30))
            goal_text = f"Осталось: **{diff} кг**. При темпе 3 кг/мес. цель будет достигнута примерно к **{target_date.strftime('%B %Y')}** ({months} мес.)."
        elif diff <= 2 and diff >= 0:
            goal_text = "🎉 Ты почти у цели! Осталось совсем немного."
        else:
            goal_text = "⚠️ Целевой вес выше текущего. Это набор массы, а не похудение."

        # --- СОХРАНЕНИЕ В БАЗУ ДАННЫХ (Идея 4) ---
        current_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (date, surname, name, gender, age, height, weight, target_weight, bmi, category, ideal_weight, calories_maintain, calories_lose)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (current_date, surname, name, gender, age, height_cm, weight, target_weight, bmi, category, ideal_weight,
              calories_maintain, calories_lose))
        conn.commit()

        st.success("✅ Данные рассчитаны и навсегда сохранены в базе приложения!")

        # --- ВЫВОД РЕЗУЛЬТАТОВ ---
        st.markdown("---")
        st.subheader("📊 Твои результаты")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📊 ИМТ", bmi)
        m2.metric("⚖️ Идеальный вес", f"{ideal_weight} кг")
        m3.metric("🔥 Поддержание", f"{calories_maintain} ккал")
        m4.metric("📉 Похудение", f"{calories_lose} ккал")

        st.markdown(f"""
        <div style='background: {cat_color}22; padding: 15px; border-radius: 10px; border-left: 5px solid {cat_color};'>
            <h3 style='margin: 0; color: {cat_color};'>📋 {category}</h3>
            <p style='margin: 5px 0;'>Норма ИМТ для твоего возраста: <b>{norm_min} – {norm_max}</b></p>
        </div>
        """, unsafe_allow_html=True)

        st.info(f"🎯 **План действий:** {goal_text}")

        with st.expander("📄 Подробная информация о калориях (Формула Миффлина-Сан Жеора)"):
            st.write(
                f"Твой базовый обмен веществ (в покое): **{int((calories_maintain / (1.2 if activity == 'Сидячий' else 1.375 if activity == 'Умеренный' else 1.55)))} ккал**")
            st.write(
                f"С учетом активности (**{activity}**): тебе нужно **{calories_maintain} ккал** в день, чтобы вес стоял на месте.")
            st.write(f"Для безопасного похудения (дефицит 500 ккал): **{calories_lose} ккал** в день.")
            st.caption(
                "⚠️ Не рекомендуется опускаться ниже 1200 ккал для женщин и 1500 ккал для мужчин без наблюдения врача.")

# ============================================================================
# 4. ПРОСМОТР ИСТОРИИ (ЛИЧНЫЙ КАБИНЕТ)
# ============================================================================
st.markdown("---")
st.subheader("📖 Личный кабинет и история")

search_surname = st.text_input("🔍 Введите фамилию для поиска истории:", value=surname).strip().capitalize()

if search_surname:
    df = pd.read_sql_query(
        "SELECT date as 'Дата', weight as 'Вес', bmi as 'ИМТ', category as 'Категория', calories_lose as 'Ккал для похудения' FROM history WHERE surname LIKE ?",
        conn, params=(f"%{search_surname}%",))

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

        if len(df) >= 2:
            st.markdown("📈 **Динамика твоего веса**")
            chart_data = df.rename(columns={'Дата': 'index', 'Вес': 'value'}).set_index('index')
            st.line_chart(chart_data)
    else:
        st.info(f"Записей для фамилии '{search_surname}' пока нет. Внеси данные выше!")