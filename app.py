# ============================================================================
# 🏋️ ДНЕВНИК ПОХУДЕНИЯ PRO — С советами по питанию и ГИ
# ============================================================================

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date

st.set_page_config(page_title="Дневник похудения PRO", page_icon="🏋️", layout="centered")


# ============================================================================
# 1. БАЗА ДАННЫХ
# ============================================================================
@st.cache_resource
def init_db():
    conn = sqlite3.connect('diary_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, surname TEXT, name TEXT, birth_date TEXT,
            gender TEXT, height REAL, weight REAL, target_weight REAL,
            bmi REAL, category TEXT, ideal_weight REAL,
            calories_maintain INT, calories_lose INT
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


def calculate_age(birth_date):
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


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
    if gender == 'м':
        bmr = 10 * weight + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height_cm - 5 * age - 161
    multipliers = {'Сидячий': 1.2, 'Умеренный': 1.375, 'Активный': 1.55}
    maintain = int(bmr * multipliers[activity])
    lose = maintain - 500
    return maintain, max(lose, 1200)


# ============================================================================
# 3. СОВЕТЫ ПО ПИТАНИЮ (НОВЫЙ БЛОК)
# ============================================================================

# Таблица гликемического индекса продуктов (по данным Международных таблиц ГИ)
GI_PRODUCTS = {
    'Низкий ГИ (≤55)': [
        ('Гречка', 54), ('Овсянка (долгой варки)', 55), ('Перловка', 22),
        ('Чечевица', 25), ('Фасоль', 30), ('Нут', 28),
        ('Яблоки', 38), ('Груши', 38), ('Апельсины', 42),
        ('Грейпфрут', 25), ('Вишня', 22), ('Клубника', 41),
        ('Брокколи', 10), ('Цветная капуста', 15), ('Огурцы', 15),
        ('Помидоры', 30), ('Шпинат', 15), ('Морковь (сырая)', 16),
        ('Миндаль', 15), ('Грецкие орехи', 15), ('Арахис', 14),
        ('Молоко 2.5%', 27), ('Йогурт натуральный', 33), ('Творог', 30),
    ],
    'Средний ГИ (56-69)': [
        ('Рис басмати', 58), ('Бурый рис', 68), ('Гречневые хлебцы', 68),
        ('Цельнозерновой хлеб', 65), ('Ржаной хлеб', 65),
        ('Бананы', 60), ('Киви', 58), ('Ананас', 59),
        ('Изюм', 64), ('Свёкла (варёная)', 64),
        ('Овсяное печенье', 55), ('Макароны из твёрдых сортов', 55),
    ],
    'Высокий ГИ (≥70)': [
        ('Белый хлеб', 75), ('Белый рис', 83), ('Картофельное пюре', 90),
        ('Жареный картофель', 75), ('Картофель фри', 75),
        ('Кукурузные хлопья', 85), ('Мюсли с сахаром', 80),
        ('Арбуз', 72), ('Ананас консервированный', 73),
        ('Финики', 103), ('Пиво', 110),
        ('Шоколад молочный', 70), ('Мёд', 61), ('Сахар', 68),
        ('Сладкие газировки', 85), ('Выпечка из белой муки', 75),
    ]
}


def get_nutrition_advice(category, goal):
    """Возвращает советы по питанию в зависимости от категории и цели"""

    if goal == 'lose':  # Похудение
        return {
            'title': '📉 ПИТАНИЕ ДЛЯ ПОХУДЕНИЯ',
            'color': '#4CAF50',
            'principles': [
                '🔥 Дефицит 400-500 ккал в день (не больше!)',
                '💧 Пей 30 мл воды на 1 кг веса (например, 2 л при весе 65 кг)',
                '🥩 Белок в каждом приёме пищи (1.2-1.6 г на кг веса)',
                '🥦 Половина тарелки — овощи и зелень',
                '⏰ Последний приём пищи за 3 часа до сна',
                '🚫 Исключи жидкие калории: соки, газировки, латте с сиропом',
            ],
            'to_add': [
                '🥬 Листовая зелень (шпинат, салат, руккола) — почти 0 ккал',
                '🐟 Белая рыба (треска, минтай) — 80 ккал/100г',
                '🍗 Куриная грудка без кожи — 110 ккал/100г',
                '🥚 Яйца — сытость на 4+ часа',
                '🥒 Огурцы, помидоры, кабачки — объём без калорий',
                '🫐 Ягоды (особенно клубника, черника) — низкий ГИ',
                '🥜 Орехи (миндаль, грецкие) — 15-20 г в день',
            ],
            'to_remove': [
                '🍞 Белый хлеб, булки, сдоба (ГИ 75+)',
                '🍟 Жареный картофель, фри (ГИ 75-90)',
                '🍬 Сладости, шоколад, печенье (ГИ 70+)',
                '🥤 Сладкие газировки и соки (ГИ 85+)',
                '🍺 Алкоголь — особенно пиво (ГИ 110!)',
                '🍝 Макароны из мягких сортов пшеницы',
                '🥐 Фастфуд, полуфабрикаты, колбасы',
            ],
            'menu_example': """
            **Завтрак:** Овсянка на воде + ягоды + 5 миндальных орехов (350 ккал)  
            **Перекус:** Яблоко + 20 г творога (150 ккал)  
            **Обед:** Куриная грудка + гречка + салат из свежих овощей (450 ккал)  
            **Полдник:** Натуральный йогурт + 10 г орехов (180 ккал)  
            **Ужин:** Белая рыба + тушёные овощи (350 ккал)
            """
        }

    elif goal == 'gain':  # Набор веса
        return {
            'title': '📈 ПИТАНИЕ ДЛЯ НАБОРА ВЕСА',
            'color': '#2196F3',
            'principles': [
                '🔥 Профицит 300-500 ккал в день',
                '🍽️ 5-6 приёмов пищи в день (небольшие порции)',
                '🥩 Увеличь белок до 1.6-2 г на кг веса',
                '🥑 Добавь полезные жиры (авокадо, орехи, оливковое масло)',
                '💪 Ешь углеводы с низким ГИ для энергии',
                '🏋️ Сочетай с силовыми тренировками (иначе пойдёт жир)',
            ],
            'to_add': [
                '🥑 Авокадо — 160 ккал/100г, полезные жиры',
                '🥜 Орехи и ореховая паста — 600 ккал/100г',
                '🍌 Бананы — быстрые углеводы после тренировки',
                '🥛 Цельное молоко, жирный творог (5-9%)',
                '🍗 Красное мясо (говядина) — железо и белок',
                '🐟 Жирная рыба (лосось, скумбрия) — омега-3',
                '🍚 Бурый рис, киноа, гречка — сложные углеводы',
                '🫒 Оливковое масло — добавляй в салаты',
            ],
            'to_remove': [
                '🍭 Пустые калории: сладости, фастфуд (набор жира, а не мышц)',
                '🥤 Газировки и энергетики',
                '🍟 Жареное в большом количестве масла',
                '🍺 Алкоголь — тормозит синтез белка',
                '🥡 Пропуск приёмов пищи',
            ],
            'menu_example': """
            **Завтрак:** Овсянка на молоке + банан + арахисовая паста (550 ккал)  
            **Перекус:** Творог 5% + орехи + мёд (350 ккал)  
            **Обед:** Говядина + бурый рис + овощи + оливковое масло (650 ккал)  
            **Полдник:** Сэндвич из цельнозернового хлеба с курицей и авокадо (450 ккал)  
            **Ужин:** Лосось + киноа + салат (550 ккал)  
            **Перед сном:** Стакан молока + 20 г миндаля (250 ккал)
            """
        }

    else:  # Поддержание
        return {
            'title': '⚖️ ПИТАНИЕ ДЛЯ ПОДДЕРЖАНИЯ ВЕСА',
            'color': '#FF9800',
            'principles': [
                '🔥 Держи калорийность на уровне своего расхода',
                '🥗 Правило тарелки: ½ овощи, ¼ белок, ¼ сложные углеводы',
                '💧 30 мл воды на 1 кг веса',
                '🍽️ 3 основных приёма пищи + 1-2 перекуса',
                '⏰ Старайся есть в одно и то же время',
                '😴 Сон 7-8 часов — критичен для метаболизма',
            ],
            'to_add': [
                '🥦 Разноцветные овощи — 5 порций в день',
                '🐟 Рыба 2-3 раза в неделю',
                '🥜 Орехи и семена (льняные, чиа)',
                '🫘 Бобовые (чечевица, фасоль) — 3-4 раза в неделю',
                '🥛 Кисломолочные продукты — для микрофлоры',
                '🍓 Сезонные ягоды и фрукты',
                '🫒 Нерафинированные масла (оливковое, льняное)',
            ],
            'to_remove': [
                '🍬 Избыток сахара (не более 25 г в день по ВОЗ)',
                '🧂 Избыток соли (не более 5 г в день)',
                '🍟 Трансжиры (маргарин, фастфуд, магазинная выпечка)',
                '🥤 Сладкие напитки',
                '🍺 Алкоголь — не более 1-2 раз в неделю',
                '🥡 Переработанное мясо (сосиски, колбасы)',
            ],
            'menu_example': """
            **Завтрак:** Омлет из 2 яиц + цельнозерновой тост + авокадо (450 ккал)  
            **Перекус:** Фрукт + горсть орехов (200 ккал)  
            **Обед:** Суп-пюре из овощей + куриная грудка + салат (500 ккал)  
            **Полдник:** Натуральный йогурт + ягоды (180 ккал)  
            **Ужин:** Запечённая рыба + овощи на пару + киноа (450 ккал)
            """
        }


# ============================================================================
# 4. ИНТЕРФЕЙС
# ============================================================================

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
    birth_date = st.date_input("🎂 Дата рождения", value=date(1990, 1, 1), min_value=date(1920, 1, 1),
                               max_value=date.today())
    gender = st.radio("⚧ Пол", ["м", "ж"], horizontal=True)

with col2:
    height_cm = st.number_input("📏 Рост (см)", min_value=100.0, max_value=250.0, value=170.0, step=0.1)
    weight = st.number_input("⚖️ Текущий вес (кг)", min_value=30.0, max_value=300.0, value=70.0, step=0.1)
    target_weight = st.number_input("🎯 Целевой вес (кг)", min_value=30.0, max_value=300.0, value=65.0, step=0.1)
    activity = st.selectbox("🏃 Уровень активности", ["Сидячий", "Умеренный", "Активный"])

# КНОПКА РАСЧЕТА
if st.button("🔢 РАССЧИТАТЬ И СОХРАНИТЬ", type="primary", use_container_width=True):
    if not surname or not name:
        st.error("❌ Пожалуйста, введите фамилию и имя!")
    else:
        age = calculate_age(birth_date)

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

        # Определяем цель
        diff = weight - target_weight
        if diff > 2:
            goal = 'lose'
            months = round(diff / 3, 1)
            target_date = datetime.now() + timedelta(days=int(months * 30))
            goal_text = f"Осталось: **{round(diff, 1)} кг**. При темпе 3 кг/мес. цель будет достигнута примерно к **{target_date.strftime('%B %Y')}** ({months} мес.)."
        elif diff < -2:
            goal = 'gain'
            months = round(abs(diff) / 2, 1)
            target_date = datetime.now() + timedelta(days=int(months * 30))
            goal_text = f"Нужно набрать: **{round(abs(diff), 1)} кг**. При темпе 2 кг/мес. цель будет достигнута примерно к **{target_date.strftime('%B %Y')}** ({months} мес.)."
        else:
            goal = 'maintain'
            goal_text = "🎉 Твой вес близок к цели! Задача — поддержание."

        # СОХРАНЕНИЕ В БАЗУ
        current_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (date, surname, name, birth_date, gender, height, weight, target_weight, bmi, category, ideal_weight, calories_maintain, calories_lose)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (current_date, surname, name, birth_date.strftime("%d.%m.%Y"), gender, height_cm, weight, target_weight,
              bmi, category, ideal_weight, calories_maintain, calories_lose))
        conn.commit()

        st.success("✅ Данные рассчитаны и сохранены!")

        # РЕЗУЛЬТАТЫ
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
            <p style='margin: 5px 0;'>Норма ИМТ для {age} лет: <b>{norm_min} – {norm_max}</b></p>
        </div>
        """, unsafe_allow_html=True)

        st.info(f"🎯 **План действий:** {goal_text}")

        # ====================================================================
        # 🥗 БЛОК СОВЕТОВ ПО ПИТАНИЮ (НОВОЕ!)
        # ====================================================================
        st.markdown("---")
        st.markdown("<h2 style='text-align: center;'>🥗 ПЕРСОНАЛЬНЫЕ СОВЕТЫ ПО ПИТАНИЮ</h2>", unsafe_allow_html=True)

        advice = get_nutrition_advice(category, goal)

        # Заголовок с цветом
        st.markdown(f"""
        <div style='background: {advice['color']}22; padding: 15px; border-radius: 10px; border-left: 5px solid {advice['color']};'>
            <h3 style='margin: 0; color: {advice['color']};'>{advice['title']}</h3>
        </div>
        """, unsafe_allow_html=True)

        # Вкладки для удобной навигации
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Принципы", "✅ Что добавить", "❌ Что исключить",
            "📊 Таблица ГИ", "🍽️ Пример меню"
        ])

        with tab1:
            st.markdown("### 🎯 Основные принципы твоего питания:")
            for principle in advice['principles']:
                st.markdown(f"- {principle}")

        with tab2:
            st.markdown("### ✅ Продукты, которые стоит добавить в рацион:")
            for product in advice['to_add']:
                st.markdown(f"- {product}")

        with tab3:
            st.markdown("### ❌ Продукты, которые стоит исключить или ограничить:")
            for product in advice['to_remove']:
                st.markdown(f"- {product}")

        with tab4:
            st.markdown("### 📊 Гликемический индекс (ГИ) продуктов")
            st.caption(
                "ГИ показывает, как быстро продукт повышает сахар в крови. Для похудения выбирай продукты с низким ГИ.")

            # Зелёная зона
            st.markdown("#### 🟢 Низкий ГИ (≤55) — **МОЖНО И НУЖНО**")
            df_low = pd.DataFrame(GI_PRODUCTS['Низкий ГИ (≤55)'], columns=['Продукт', 'ГИ'])
            st.dataframe(df_low, use_container_width=True, hide_index=True)

            # Жёлтая зона
            st.markdown("#### 🟡 Средний ГИ (56-69) — **УМЕРЕННО**")
            df_mid = pd.DataFrame(GI_PRODUCTS['Средний ГИ (56-69)'], columns=['Продукт', 'ГИ'])
            st.dataframe(df_mid, use_container_width=True, hide_index=True)

            # Красная зона
            st.markdown("#### 🔴 Высокий ГИ (≥70) — **ИСКЛЮЧИТЬ ИЛИ МИНИМИЗИРОВАТЬ**")
            df_high = pd.DataFrame(GI_PRODUCTS['Высокий ГИ (≥70)'], columns=['Продукт', 'ГИ'])
            st.dataframe(df_high, use_container_width=True, hide_index=True)

        with tab5:
            st.markdown("### 🍽️ Примерное меню на день:")
            st.markdown(advice['menu_example'])

        # Дисклеймер по питанию
        st.caption(
            "⚠️ Рекомендации носят общий характер. При наличии заболеваний ЖКТ, диабета, аллергии или беременности проконсультируйтесь с врачом.")

# ============================================================================
# 5. ЛИЧНЫЙ КАБИНЕТ
# ============================================================================
st.markdown("---")
st.subheader("📖 Личный кабинет")

search_col1, search_col2, search_col3 = st.columns(3)
with search_col1:
    search_surname = st.text_input("Фамилия:", value=surname if 'surname' in locals() else "").strip().capitalize()
with search_col2:
    search_name = st.text_input("Имя:", value=name if 'name' in locals() else "").strip().capitalize()
with search_col3:
    search_birth = st.date_input("Дата рождения:", value=birth_date if 'birth_date' in locals() else date(1990, 1, 1))

if st.button("🔍 Найти мои записи"):
    birth_str = search_birth.strftime("%d.%m.%Y")
    df = pd.read_sql_query('''
        SELECT date as 'Дата', weight as 'Вес', bmi as 'ИМТ', category as 'Категория', 
               calories_lose as 'Ккал для похудения', target_weight as 'Цель'
        FROM history 
        WHERE surname = ? AND name = ? AND birth_date = ?
        ORDER BY date DESC
    ''', conn, params=(search_surname, search_name, birth_str))

    if not df.empty:
        st.success(f"✅ Найдено записей: {len(df)}")
        st.dataframe(df, use_container_width=True, hide_index=True)

        if len(df) >= 2:
            st.markdown("📈 **Динамика твоего веса**")
            chart_data = df[['Дата', 'Вес']].set_index('Дата')
            st.line_chart(chart_data)
    else:
        st.info(f"Записей для {search_surname} {search_name} ({birth_str}) пока нет.")