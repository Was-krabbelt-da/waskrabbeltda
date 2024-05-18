from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests
import os
from dotenv import load_dotenv

load_dotenv()

DATA_ENDPOINT = f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data"
API_KEY = os.getenv('API_KEY')
CAMERA_NAME = os.getenv('CAMERA_NAME', 'waskrabbeltda')
EXCLUDE_CLASSES = ['none_dirt', 'none_bg', 'none_dirt', 'none_shadow', 'other']

# Set streamlit page configuration, this needs to be the first streamlit command.
st.set_page_config(
    page_title="Was krabbelt da? 🐞🐞🐞",
    page_icon="🐞",
    layout="wide",
    initial_sidebar_state="expanded")

# Define constants
START_TIME_COLUMN = 'start_time'
END_TIME_COLUMN = 'end_time'
DURATION_COLUMN = 'duration_s'

# Configure CSS Styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    #background-color: #393939;
    text-align: center;
    padding: 15px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

</style>
""", unsafe_allow_html=True)

# Functions 

# Load data with caching, column renaming and data type conversions.
# Create additionally needed data columns here.
def load_data():
    response = requests.get(DATA_ENDPOINT, headers={'access_token': API_KEY})
    data = response.json()
    data = pd.DataFrame(data)
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis='columns', inplace=True)
    data[START_TIME_COLUMN] = pd.to_datetime(data[START_TIME_COLUMN], format='mixed')
    data[END_TIME_COLUMN] = pd.to_datetime(data[END_TIME_COLUMN], format='mixed')
    data["hour"] = data[START_TIME_COLUMN].dt.hour
    data = data[~data['top1'].isin(EXCLUDE_CLASSES)]
    return data

# Plot functions
# Create heatmap with Altair
def make_heatmap(input_df, input_y, input_x, input_color, input_color_theme):
    heatmap = alt.Chart(input_df).mark_rect().encode(
            y=alt.Y(f'{input_y}:O', axis=alt.Axis(title="Tier", titleFontSize=18, titlePadding=15, titleFontWeight=900, labelAngle=0)),
            x=alt.X(f'{input_x}:O', axis=alt.Axis(title="Uhrzeit", titleFontSize=18, titlePadding=15, titleFontWeight=900)),
            color=alt.Color(f'max({input_color}):Q',
                                legend=None,
                                scale=alt.Scale(scheme=input_color_theme)),
            stroke=alt.value('black'),
            strokeWidth=alt.value(0.25),
        ).properties(width=900
        ).configure_axis(
        labelFontSize=12,
        titleFontSize=12
        ) 
    return heatmap

# Load data
data = load_data()

# Dashboard content

# Define sidebar. The sidebar will be displayed on the left side of the page and can be toggled by the user.
# The sidebar contains the title and elements for user input, e.g. for choosing a color theme or a day to view.
with st.sidebar:
    st.title('🐞 Was krabbelt da Dashboard')
    
    # Create a list of unique dates in the data and reverse the list to display the most recent date first
    day_list = list(data.date.unique())[::-1]
    # Create a selectbox to choose a date from the list of unique dates and create a new dataframe
    # containing only observations from the selected date
    selected_date = st.selectbox('Wähle einen Tag aus', day_list, index=0)
    df_selected_day = data[data.date == selected_date]

    # Create a selectbox to choose a color theme and store it in selected_color_theme. This is later used e.g. for the heatmap.
    color_theme_list = ['blues', 'cividis', 'greens', 'inferno', 'magma', 'plasma', 'reds', 'rainbow', 'turbo', 'viridis']
    selected_color_theme = st.selectbox('Select a color theme', color_theme_list)


# Set up layout for main content
# This creates a two-column layout, with a width ratio of 1:3.
columns = st.columns([1, 3], gap='medium')

# Column 1
with columns[0]:

    # Display a download button to download the data as a CSV file.
    st.download_button(
    label="Download data as CSV",
    data=data.to_csv(index=False).encode('utf-8'),
    file_name=f"{datetime.now().strftime('%Y_%m_%d-%H-%M-%S')}-{CAMERA_NAME}.csv",
    mime="text/csv",
    )  
     
    # Display count of each insect category for the selected date.
    # Count occurrences, sort by count, and display with st.metric elements. 
    # The st.metric elements are styled with CSS in the header of the script.
    st.subheader( selected_date)
    label_counts = df_selected_day['top1'].value_counts()
    for label, count in label_counts.items():
        st.metric(label=label, value=count)

# Column 2: Display visualizations, stacked on top of each other.
with columns[1]:
    # Display raw data if checkbox is selected.
    if st.checkbox(f'Show raw data of {selected_date}'):
        st.subheader('Raw data')
        st.write(df_selected_day)
    
    # Create a histogram based on the data for the selected day, counting the number of insects per hour.
    # Display it as a bar chart provided by streamlit.
    st.subheader('Anzahl der Insekten pro Stunde')
    hist_values = np.histogram(df_selected_day[START_TIME_COLUMN].dt.hour, bins=24, range=(0,24))[0]
    st.bar_chart(hist_values)


    hour_to_filter = st.slider('Wähle eine Uhrzeit aus', 0, 23, 16)
    st.subheader('Wer ist um %s:00 Uhr unterwegs?' % hour_to_filter)
    filtered_data = df_selected_day[df_selected_day[START_TIME_COLUMN].dt.hour == hour_to_filter]
    st.bar_chart(filtered_data['top1'].value_counts())
    # Display a horizontal divider.
    st.divider()

    st.subheader('Wer ist wann am Tag unterwegs?')
    # Create a heatmap showing the distribution of insect categories over the hours of the day.
    # Create a dedicated dataframe for the heatmap with the count of each insect category per hour.
    # Use the make_heatmap function to create the heatmap with Altair and display it with st.altair_chart.
    heatmap_df = data.groupby(['top1', 'hour']).size().reset_index(name='count')
    heatmap = make_heatmap(heatmap_df, 'top1', 'hour', 'count', selected_color_theme)
    st.altair_chart(heatmap, use_container_width=True)

    # Display a horizontal divider.
    st.divider()
    st.subheader('Wie lange sind die Insekten auf der Kamera?')
    # Create a histogram showing the duration of insect observations.
    duration_hist_values = np.histogram(df_selected_day[DURATION_COLUMN], bins=150, range=(0,150))[0]
    st.bar_chart(duration_hist_values)
