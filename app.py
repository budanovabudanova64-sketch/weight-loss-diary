# ============================================================================
# 🏋️ ДНЕВНИК ПОХУДЕНИЯ — Веб-версия на Streamlit
# Работает в браузере на любом устройстве!
# ============================================================================

import streamlit as st
from datetime import datetime
import pandas as pd
import re

# Настройка страницы (должно быть первым вызовом Streamlit)
st.set_page_config(
    page_title="Дневник похудения",
    page_icon="🏋️",
    layout="centered"
)

# ============================================================================
# КОНСТАНТЫ И ФУНКЦИИ РАСЧЁТА
# ============================================================================

AGE_NORMS = [(25, 19, 24), (35, 20, 25), (45, 21, 26), (55, 22, 27), (65, 23, 28)]
AGE_FACTORS = [(30, 1.0), (40, 1.02), (50, 1.04), (60, 1.06), (float('inf'), 1.08)]


def get_age_norm(age):
    for max_age, min_val, max_val in AGE_NORMS:
        if age < max_age:
            return min_val, max_val
    return 24, 29


def get_age_factor(age):
    for max_age, factor in AGE_FACTORS:
        if age < max_age:
            return factor
    return 1.08


def calculate_ideal_weight(gender, height_inches, age_factor):
    formulas = {
        'devine': (50, 45.5, 2.3, 2.3),
        'robinson': (52, 49, 1.9, 1.7),
        'miller': (56.2, 53.1, 1.41, 1.36),
        'hamwi': (48, 45.5, 2.7, 2.2)
    }
    results = []
    for name, (m_base, f_base, m_mult, f_mult) in formulas.items():
        base = m_base if gender == 'м' else f_base
        mult = m_mult if gender == 'м' else f_mult
        result = base + mult * (height_inches - 60)
        if name == 'hamwi':
            result *= age_factor
        results.append(result)
    return sum(results) / len(results)


def sanitize_filename(name):
    cleaned = re.sub(r'[^\w\-]', '_', name)
    return cleaned[:50] if cleaned else "user"


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ SESSION STATE (хранилище данных между перезагрузками)
# ============================================================================

if 'history' not in st.session_state:
    st.session_state.history = []

# ============================================================================
# ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# ============================================================================

# Заголовок
st.markdown("""
<div style='background: linear-gradient(90deg, #2c5f8d, #4CAF50); padding: 20px; border-radius: 10px; text-align: center;'>
    <h1 style='color: white; margin: 0;'>🏋️ ДНЕВНИК ПОХУДЕНИЯ</h1>
    <p style='color: white; margin: 5px 0 0 0;'>Отслеживай свой прогресс каждый день</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# === БЛОК ВВОДА ===
st.subheader("📝 Введите свои данные")

col1, col2 = st.columns(2)

with col1:
    surname = st.text_input("👤 Фамилия", placeholder="Иванов")
    name = st.text_input("👤 Имя", placeholder="Иван")
    gender = st.radio("⚧ Пол", ["м", "ж"], horizontal=True)

with col2:
    age = st.number_input("🎂 Возраст (лет)", min_value=1, max_value=120, value=30)
    weight = st.number_input("⚖️ Вес (кг)", min_value=20.0, max_value=500.0, value=70.0, step=0.1)
    height_cm = st.number_input("📏 Рост (см)", min_value=100.0, max_value=250.0, value=175.0, step=0.1)

st.markdown("---")

# === КНОПКА РАСЧЁТА ===
calculate_btn = st.button("🔢 РАССЧИТАТЬ", type="primary", use_container_width=True)

# === РАСЧЁТ И ВЫВОД РЕЗУЛЬТАТА ===
if calculate_btn:
    # Проверка ввода
    if not surname.strip() or not name.strip():
        st.error("❌ Пожалуйста, введите фамилию и имя!")
    else:
        # Расчёты
        height_m = height_cm / 100
        height_inches = height_cm / 2.54
        bmi = round(weight / (height_m ** 2), 1)

        norm_min, norm_max = get_age_norm(age)
        age_factor = get_age_factor(age)

        if bmi < norm_min:
            category, advice = "Недостаточный вес", "Стоит питаться плотнее 🍔"
            category_color = "#2196F3"
        elif bmi <= norm_max:
            category, advice = "Норма для твоего возраста", "Всё отлично, так держать! 💪"
            category_color = "#4CAF50"
        elif bmi < 30:
            category, advice = "Избыточный вес", "Больше двигайся и следи за питанием 🏃"
            category_color = "#FF9800"
        else:
            category, advice = "Ожирение", "Лучше проконсультироваться с врачом 🩺"
            category_color = "#F44336"

        ideal_weight = round(calculate_ideal_weight(gender, height_inches, age_factor), 1)
        weight_diff = round(weight - ideal_weight, 1)

        if weight_diff > 0:
            percent = round(weight_diff / ideal_weight * 100, 1)
            diff_text = f"Ты тяжелее идеала на {weight_diff} кг (+{percent}%)"
        elif weight_diff < 0:
            percent = round(abs(weight_diff) / ideal_weight * 100, 1)
            diff_text = f"Ты легче идеала на {abs(weight_diff)} кг (-{percent}%)"
        else:
            diff_text = "Ты в идеальной форме! 🎯"

        current_date = datetime.now().strftime("%d.%m.%Y %H:%M")

        # === КРАСИВЫЙ ВЫВОД ===
        st.markdown("### 📊 Твои результаты")

        # Карточки с основными показателями
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 ИМТ", bmi)
        with col2:
            st.metric("⚖️ Идеальный вес", f"{ideal_weight} кг")
        with col3:
            st.metric("🎯 Норма ИМТ", f"{norm_min}-{norm_max}")

        # Основная информация
        st.markdown(f"""
        <div style='background: {category_color}22; padding: 15px; border-radius: 10px; border-left: 5px solid {category_color};'>
            <h3 style='margin: 0; color: {category_color};'>📋 {category}</h3>
            <p style='margin: 5px 0 0 0;'><b>💡 Совет:</b> {advice}</p>
        </div>
        """, unsafe_allow_html=True)

        st.info(f"📏 **{diff_text}**")

        # Детали
        with st.expander("📄 Подробная информация"):
            st.markdown(f"""
            - **📅 Дата:** {current_date}
            - **👤 ФИО:** {surname} {name}
            - **🎂 Возраст:** {age} лет
            - **⚧ Пол:** {'Мужской' if gender == 'м' else 'Женский'}
            - **📏 Рост:** {height_cm} см
            - **⚖️ Текущий вес:** {weight} кг
            - **📊 ИМТ:** {bmi}
            - **🎯 Норма ИМТ для {age} лет:** {norm_min}-{norm_max}
            - **⚖️ Идеальный вес:** {ideal_weight} кг
            - **📏 Разница:** {diff_text}
            """)

        # Сохраняем результат в историю
        st.session_state.result = {
            'date': current_date,
            'surname': surname,
            'name': name,
            'gender': 'Мужской' if gender == 'м' else 'Женский',
            'age': age,
            'height': height_cm,
            'weight': weight,
            'bmi': bmi,
            'category': category,
            'ideal_weight': ideal_weight,
            'diff': weight_diff,
            'diff_text': diff_text
        }

# === КНОПКИ ДЕЙСТВИЙ ===
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    if 'result' in st.session_state:
        if st.button("💾 Сохранить в дневник", use_container_width=True):
            st.session_state.history.append(st.session_state.result)
            st.success("✅ Запись добавлена в дневник!")

with col2:
    if st.session_state.history:
        # Кнопка скачивания истории
        df = pd.DataFrame(st.session_state.history)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачать историю (CSV)",
            data=csv,
            file_name="diary_history.csv",
            mime="text/csv",
            use_container_width=True
        )

with col3:
    if st.session_state.history:
        if st.button("🗑️ Очистить историю", use_container_width=True):
            st.session_state.history = []
            st.rerun()

# === ИСТОРИЯ ЗАПИСЕЙ ===
if st.session_state.history:
    st.markdown("---")
    st.subheader(f"📖 История ({len(st.session_state.history)} записей)")

    # Таблица истории
    df = pd.DataFrame(st.session_state.history)
    df_display = df[['date', 'surname', 'name', 'weight', 'bmi', 'category', 'ideal_weight']]
    df_display.columns = ['📅 Дата', '👤 Фамилия', '👤 Имя', '⚖️ Вес', '📊 ИМТ', '📋 Категория', '🎯 Идеал']
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # График динамики веса (если записей достаточно)
    if len(st.session_state.history) >= 2:
        st.markdown("### 📈 Динамика веса")
        chart_data = df[['date', 'weight']].copy()
        chart_data.columns = ['Дата', 'Вес']
        st.line_chart(chart_data.set_index('Дата'))

# === ПОДВАЛ ===
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
    ⚠️ Программа носит информационный характер и не заменяет консультацию врача.<br>
    Сделано с ❤️ на Python + Streamlit
</div>
""", unsafe_allow_html=True)