import streamlit as st
import pandas as pd
import numpy as np

st.title('Was krabbelt da Dashboard')

DATA_URL = ('./data/insects.csv')
DATE_COLUMN = 'start_time'

@st.cache_data
def load_data():
    data = pd.read_csv(DATA_URL)
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis='columns', inplace=True)
    data[DATE_COLUMN] = pd.to_datetime(data[DATE_COLUMN])
    return data

data = load_data()



if st.checkbox('Show raw data'):
    st.subheader('Raw data')
    st.write(data)

st.subheader('Anzahl der Insekten pro Stunde')
hist_values = np.histogram(data[DATE_COLUMN].dt.hour, bins=24, range=(0,24))[0]
print(hist_values)
st.bar_chart(hist_values)


hour_to_filter = st.slider('hour', 0, 23, 17)
filtered_data = data[data[DATE_COLUMN].dt.hour == hour_to_filter]


st.subheader('Wer ist um %s:00 Uhr unterwegs?' % hour_to_filter)

#create np histogram data for the filtered data
print(filtered_data['top1'].value_counts(ascending=True))
hist_values = filtered_data['top1'].value_counts(ascending=True)
print(hist_values)
st.bar_chart(hist_values)