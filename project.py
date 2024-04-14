#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Загрузка и подготовка данных

# Приведем данные в единый удобный для работы формат

salaries0 = st.cache_data(pd.read_excel)(
    'zpl by field.xlsx',
    sheet_name='с 2017 г.',
    skiprows=4,
    index_col=0
    )
salaries1 = st.cache_data(pd.read_excel)(
    'zpl by field.xlsx',
    sheet_name='2000-2016 гг.',
    skiprows=2,
    index_col=0
    )

inflation = st.cache_data(pd.read_excel)('inflation.xlsx')
brent = st.cache_data(pd.read_excel)('brent.xlsx')
usdrub = st.cache_data(pd.read_excel)('usdrub.xlsx')

inflation = inflation[['Год', 'Всего']]
inflation = inflation.set_index('Год')

salaries0.rename(columns={
        '20171)': 2017,
        '20222)': 2022,
        '20232), 3)': 2023}, inplace=True)

salaries1.rename(columns={
        'Unnamed: 0': 'Отрасль',
        }, inplace=True)

#удаляем строчки с примечаниями
salaries0 = salaries0[:-3]

# Отфильтруем нужные строки и объединим фреймы
# В датафреймах существенно различается разбивка по строкам, поэтому имеет смысл сначала выделить нужные, удалить, дать одинаковые имена и затем конкатенировать.

old = salaries1.loc[["  добыча топливно-энергетических  полезных ископаемых", "Гостиницы и рестораны", "Образование"]].T

new = salaries0.loc[["     добыча нефти и природного газа",
                     "     добыча угля", 
                     "деятельность гостиниц и предприятий общественного питания",
                     "образование"]].T

old.columns = ['oilgasandcoal', 'horeca', 'education']
new.columns = ['oilgas', 'coal', 'horeca', 'education']

old = old.apply(pd.to_numeric)
new = new.apply(pd.to_numeric)

# за неимением данных численности работников в добыче угля и нефтегаза возьмем просто среднюю зп 
# и будем надеяться, что это недалеко от истины
new['oilgasandcoal'] = (new.coal + new.oilgas)/2
new.drop(columns=['oilgas', 'coal'], inplace=True)

salaries = pd.concat([old, new])

inflation.columns = ['inflation']

salaries_inflation = pd.concat([salaries, inflation], axis=1)
salaries_inflation.inflation = salaries_inflation.inflation.apply(lambda x: 1+x/100.)

salaries_inflation = salaries_inflation[salaries_inflation.index > 1999]

# создадим показатель "дефлятор", отражающий накопленную за годы инфляцию, начиная с 2000 года
# для этого перемножим показатели каждого года со сдвигом на один год (в 2000 примем индекс за 1.0)

# будем методически подходить так: чтобы привести цены, например, 2002 года, к ценам 2000 года, необходимо
# исключить накопленное влияние инфляции за весь 2000 год и за весь 2001 год. 

salaries_inflation['deflator'] = salaries_inflation.inflation.shift(fill_value=1).cumprod()

usdrub['Дата'] = pd.to_datetime(usdrub['Дата'])
brent['Дата'] = pd.to_datetime(brent['Дата'])

#Получим среднегодовые значения 
usdrub['USDRUB_year_avg'] = usdrub.groupby(usdrub['Дата'].dt.year)['Значение'].transform('mean')
usdrub_year = usdrub.groupby(usdrub['Дата'].dt.year)['USDRUB_year_avg'].mean()

brent['BRENT_year_avg'] = brent.groupby(brent['Дата'].dt.year)['Значение'].transform('mean')
brent_year = brent.groupby(brent['Дата'].dt.year)['BRENT_year_avg'].mean()

all_data = pd.concat([salaries_inflation, brent_year, usdrub_year], axis=1)

for col in ['oilgasandcoal','horeca','education']:
    all_data[col+"_corr"] = all_data[col] / all_data['deflator']

# ### Визуализируем собранные данные

st.title('Краткий обзор доходов работников по избранным отраслям экономики')

st.write('Пользуясь данными Росстата и некоторыми сторонними источниками, попробуем\
    проанализировать изменение доходов работников ряда отраслей в период с 2000 по 2023 гг.')


infl_corrected = st.radio('Выбор типа графика', ['Номинальные показатели', 'Скорректированные на инфляцию'])

if infl_corrected == 'Номинальные показатели':
    st.pyplot(all_data[['oilgasandcoal','horeca','education']].plot().figure)
    st.write("Из графиков видно, что во всех выбранных отраслях средний размер оплаты\
        растет на протяжении всего периода наблюдений. Однако данные графики недостаточно\
         информативны, т.к. показывают зарплаты в номинальном выражении. Попробуем привести\
          все зарплаты к ценам 2000 года, поделив на соответствующий дефлятор.")

elif infl_corrected == 'Скорректированные на инфляцию':
    st.pyplot(all_data[['oilgasandcoal_corr','horeca_corr','education_corr']].plot().figure)
    st.write('На график выведены зарплаты, скорректированные на величину инфляции, т.наз.\
            реальные зарплаты, в ценах 2000 г.\
            Из графика виден рост реальных доходов, характерный для всех рассматриваемых отраслей.\
            Обращает на себя внимание, что реальные доходы в образовании после 2008 года стали\
            обгонять доходы в индустрии гостеприимства и общепита.')

all_data['nrg_edu_ratio'] = all_data['oilgasandcoal'] / all_data['education']
all_data['horeca_edu_ratio'] = all_data['horeca'] / all_data['education']
all_data['nrg_horeca_ratio'] = all_data['oilgasandcoal'] / all_data['horeca']

if st.button('Показать соотношения зарплат'):
    st.pyplot(all_data[['nrg_edu_ratio', 'horeca_edu_ratio', 'nrg_horeca_ratio']].plot().figure)
    st.write("Рассмотрим соотношения между отраслями немного подробнее. Например, в начале века заработная плата\
        работников, занятых в добыче энергетических полезных ископаемых превосходила зарплаты в образовании в 6 раз.\
        К 2023 году соотношение снизилось до 3 и менее. Соотношение зарплат в хореке и образовании\
        близко к единице, но в начале века оно превышало 1.0, а сейчас - ниже 1.0.")

all_data['oilgasandcoal_usd'] = all_data['oilgasandcoal'] / all_data['USDRUB_year_avg']
all_data['horeca_usd'] = all_data['horeca'] / all_data['USDRUB_year_avg']
all_data['education_usd'] = all_data['education'] / all_data['USDRUB_year_avg']

st.write('### Изучим связь нефтегазовых доходов страны и реальных доходов населения')

choice = st.radio("Выберите отрасль", ['oilgasandcoal', 'horeca', 'education'])

fig, ax1 = plt.subplots()

color = 'tab:red'
ax1.set_xlabel('Год')
ax1.set_ylabel('Цена барреля BRENT', color=color)
ax1.set_ylim(0,200)
ax1.bar(all_data.index, all_data.BRENT_year_avg, color=color)
ax1.tick_params(axis='y', labelcolor=color)

ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

color = 'tab:blue'
ax2.set_ylabel('Реальные зарплаты в секторе '+choice+', в руб. 2000 г.', color=color)  # we already handled the x-label with ax1
ax2.plot(all_data.index, all_data[choice+'_corr'], color=color)
ax2.tick_params(axis='y', labelcolor=color)

fig.tight_layout()  # otherwise the right y-label is slightly clipped
st.pyplot(fig)

st.write("Период с 2003 по 2014 год отметился самым быстрым ростом зарплат и наиболее высокими ценами на нефть.")

st.write('## Оценим реальные доходы работников в USD')

st.pyplot(all_data[['oilgasandcoal_usd', 'horeca_usd', 'education_usd']].plot().figure)

st.write("Интересно исследовать зарплаты, выраженные в более стабильной валюте,\
    в данном случае основной мировой резервной валюте - доллларе США. Из графика очевидно,\
    что рост реальных доходов, выраженный в валюте, прекратился после 2014 года.\
    Выражение доходов в иностранной валюте актуально в отношении покупки импортных товаров, зарубежных туристических поездок.\
    Период с 2000 по 2014 год характеризовался крайне быстрым ростом доходов в долларовом выражении,\
    при этом даже глубокий финансовый кризис 2008 года на этом процессе отразился не так сильно.")


st.write('## Сопоставим курс доллара к рублю и цены на нефть марки Brent')

fig, ax1 = plt.subplots()

color = 'tab:red'
ax1.set_xlabel('year')
ax1.set_ylabel('USD RUB rate', color=color)
ax1.set_ylim(20,100)
ax1.bar(all_data.index, all_data.USDRUB_year_avg, color=color)
ax1.tick_params(axis='y', labelcolor=color)

ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

color = 'tab:blue'
ax2.set_ylabel('Brent price', color=color)  # we already handled the x-label with ax1
ax2.set_ylim(0,150)
ax2.plot(all_data.index, all_data.BRENT_year_avg, color=color)

ax2.tick_params(axis='y', labelcolor=color)

fig.tight_layout()  # otherwise the right y-label is slightly clipped
st.pyplot(fig)

st.write("Данный график из-за большого периода недостаточно наглядно показывает некоторые моменты\
         В частности, в период по 2014 год включительно, связь между курсом доллара к рублю и ценой нефти\
         была очень сильной. Начиная с 2015, а еще более выраженно с 2018, эта связь была разорвана\
         и рубль стал стоить существенно меньше, чем можно было ожидать при той же цене на нефть\
         это связано с особенностями валютных операций и т.н. бюджетного правила.")
st.write("Автор был непосредственным наблюдателем, а где-то и участником всех описанных на графиках процессов\
         с 2001 по 2021 годы :-)")

st.write("Для наглядности рассмотрим отдельно период 2000-2014 г.")
st.pyplot(all_data.loc[2000:2014, ['USDRUB_year_avg', 'BRENT_year_avg']].plot().figure)

#salaries_inflation.horeca.iloc[-1]/ salaries_inflation.horeca.iloc[0]
#salaries_inflation.oilgasandcoal.iloc[-1]/ salaries_inflation.oilgasandcoal.iloc[0]
