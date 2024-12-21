import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt

# Функция для загрузки данных из файла
def load_data(file):
    data = pd.read_csv(file, parse_dates=['timestamp'])
    return data

# Функция для анализа исторических данных
def analyze_data(city_data):
    # Описательная статистика
    stats = city_data['temperature'].describe()

    # Вычисление скользящего среднего
    city_data['rolling_avg'] = city_data['temperature'].rolling(window=30, min_periods=1).mean()

    # Выделение аномалий
    city_data['is_anomaly'] = (
        (city_data['temperature'] < city_data['rolling_avg'] - 2 * city_data['temperature'].std()) |
        (city_data['temperature'] > city_data['rolling_avg'] + 2 * city_data['temperature'].std())
    )

    # Сезонные профили
    season_stats = city_data.groupby('season')['temperature'].agg(['mean', 'std']).reset_index()

    return stats, city_data, season_stats

# Функция для получения текущей температуры через OpenWeatherMap API
def get_current_temperature(city, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['main']['temp'], None
    else:
        return None, response.json()

# Проверка, нормальна ли текущая температура для сезона
def is_temperature_normal(temp, season_stats, season):
    season_data = season_stats[season_stats['season'] == season]
    mean = season_data['mean'].values[0]
    std = season_data['std'].values[0]
    return mean - 2 * std <= temp <= mean + 2 * std

# Интерфейс Streamlit
st.title("Анализ температуры и мониторинг текущей погоды")

# Загрузка файла
uploaded_file = st.file_uploader("Загрузите файл с историческими данными (CSV)", type="csv")
if uploaded_file:
    data = load_data(uploaded_file)
    cities = data['city'].unique()

    # Выбор города
    city = st.selectbox("Выберите город", cities)

    # Фильтрация данных по городу
    city_data = data[data['city'] == city]

    # Ввод API-ключа
    api_key = st.text_input("Введите ваш API-ключ OpenWeatherMap")
    api_error = None

    # Анализ данных
    stats, analyzed_data, season_stats = analyze_data(city_data)

    if api_key:
        current_temp, error = get_current_temperature(city, api_key)

        if current_temp is not None:
            st.subheader("Текущая температура")
            st.write(f"Текущая температура в городе {city}: {current_temp}°C")

            # Определение сезона
            current_month = pd.Timestamp.now().month
            season_map = {12: 'winter', 1: 'winter', 2: 'winter',
                          3: 'spring', 4: 'spring', 5: 'spring',
                          6: 'summer', 7: 'summer', 8: 'summer',
                          9: 'autumn', 10: 'autumn', 11: 'autumn'}
            current_season = season_map[current_month]

            is_normal = is_temperature_normal(current_temp, season_stats, current_season)
            if is_normal:
                st.write(f"Текущая температура нормальна для сезона ({current_season}).")
            else:
                st.write(f"Текущая температура является аномальной для сезона ({current_season}).")
        else:
            api_error = error['message']
            st.error(f"Ошибка API: {api_error}")
    else:
        st.warning("Введите API-ключ для получения текущей погоды.")

    # Отображение результатов
    st.subheader("Описательная статистика")
    st.write(stats)

    st.subheader("Временной ряд температур с аномалиями")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(analyzed_data['timestamp'], analyzed_data['temperature'], label="Температура")
    ax.scatter(analyzed_data['timestamp'][analyzed_data['is_anomaly']],
               analyzed_data['temperature'][analyzed_data['is_anomaly']],
               color='red', label="Аномалия")
    ax.set_title(f"Температурный ряд для {city}")
    ax.set_xlabel("Дата")
    ax.set_ylabel("Температура")
    ax.legend()
    st.pyplot(fig)

    st.subheader("Сезонные профили")
    st.write(season_stats)
