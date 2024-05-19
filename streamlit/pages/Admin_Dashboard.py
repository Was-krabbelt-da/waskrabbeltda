from datetime import datetime
import io
import math
from pathlib import Path
import zipfile
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

CLASSIFICATION_DATA_ENDPOINT = f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data/classification"
DATA_ALL_ENDPOINT = f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data/all"
TRACKING_RUNS_ENDPOINT = f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data/tracking_runs"
IMAGE_ENDPOINT = f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data"
API_KEY = os.getenv('API_KEY')
CAMERA_NAME = os.getenv('CAMERA_NAME', 'waskrabbeltda')
EXCLUDE_CLASSES = ['none_dirt', 'none_bg', 'none_dirt', 'none_shadow', 'other']

with open("german_translation.json") as json_config:
    GERMAN_TRANSLATION_LABELS = json.load(json_config)

# Set streamlit page configuration, this needs to be the first streamlit command.
st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="🖥️",
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

def translate_label(label):
    if label in GERMAN_TRANSLATION_LABELS:
        return GERMAN_TRANSLATION_LABELS[label]
    return label

# Load data with caching, column renaming and data type conversions.
# Create additionally needed data columns here.
def load_data():
    response = requests.get(CLASSIFICATION_DATA_ENDPOINT, headers={'access_token': API_KEY})
    data = response.json()
    data = pd.DataFrame(data)
    
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis='columns', inplace=True)

    # Convert columns to datetime and add hour column
    data[START_TIME_COLUMN] = pd.to_datetime(data[START_TIME_COLUMN], format='mixed')
    data[END_TIME_COLUMN] = pd.to_datetime(data[END_TIME_COLUMN], format='mixed')
    data["hour"] = data[START_TIME_COLUMN].dt.hour
    
    # Remove observations which are not classified as insects
    data = data[~data['top1'].isin(EXCLUDE_CLASSES)]
    
    # Translate classification labels to German
    data['top1'] = data['top1'].map(translate_label)

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
    st.title('Admin Dashboard')
    
    # Create a list of unique dates in the data and reverse the list to display the most recent date first
    day_list = list(data.date.unique())[::-1]
    # Create a selectbox to choose a date from the list of unique dates and create a new dataframe
    # containing only observations from the selected date
    # selected_date = st.selectbox('Wähle einen Tag aus', day_list, index=0)
    # df_selected_day = data[data.date == selected_date]

    # # Create a selectbox to choose a color theme and store it in selected_color_theme. This is later used e.g. for the heatmap.
    # color_theme_list = ['blues', 'cividis', 'greens', 'inferno', 'magma', 'plasma', 'reds', 'rainbow', 'turbo', 'viridis']
    # selected_color_theme = st.selectbox('Select a color theme', color_theme_list)

# Set up layout for main content
# This creates a two-column layout, with a width ratio of 1:3.
columns = st.columns([1, 3], gap='medium')

# Column 1
with columns[0]:

    st.subheader('Download data')
    # Display a download button to download the data as a CSV file.
    st.download_button(
    label="Download data as CSV",
    data=data.to_csv(index=False).encode('utf-8'),
    file_name=f"{datetime.now().strftime('%Y_%m_%d-%H-%M-%S')}-{CAMERA_NAME}.csv",
    mime="text/csv",
    )  

    # Display download button for images. Potential TODO: make this more efficient.
    zip_data = requests.get(DATA_ALL_ENDPOINT, headers={'access_token': API_KEY}).content
    st.download_button(
        label="Download all images",
        data=zip_data,
        file_name=f"{datetime.now().strftime('%Y_%m_%d-%H-%M-%S')}-{CAMERA_NAME}-images.zip",
        mime="application/zip",
    )

# Column 2: Display visualizations, stacked on top of each other.
with columns[1]:
    # Display raw data if checkbox is selected.
    st.subheader('Raw data')
    if st.checkbox(f'Show classification data'):
        st.subheader('Classification data')
        st.write(data)
    
# Image Gallery
st.title("Image Gallery")

tracking_runs = requests.get(TRACKING_RUNS_ENDPOINT, headers={'access_token': API_KEY}).json()
days_with_images = sorted(list(tracking_runs.keys()))[::-1]
# Select day
selections = st.columns(2)
with selections[0]:
    selected_day = st.selectbox('Wähle einen Tag aus', days_with_images, index=0)
with selections[1]:
    day_tracking_runs = tracking_runs[selected_day]
    selected_run = st.selectbox('Wähle einen Tracking Run aus', day_tracking_runs)

# Query images, store and display
images_path = Path('data', selected_day, selected_run)
if not os.path.exists(images_path):
    images_path.mkdir(parents=True)
    #get zip file with all images for selected run
    images_endpoint = f"{IMAGE_ENDPOINT}/{selected_day}/{selected_run}"
    zip_images_response = requests.get(images_endpoint, headers={'access_token': API_KEY})
    zip_images = zipfile.ZipFile(io.BytesIO(zip_images_response.content))
    zip_images.extractall(images_path)

# Show images
files = os.listdir(images_path) 

controls = st.columns(3)
with controls[0]:
    batch_size = st.select_slider("Batch size:",range(10,30,5))
with controls[1]:
    row_size = st.select_slider("Row size:", range(1,6), value = 5)
num_batches = math.ceil(len(files)/batch_size)
with controls[2]:
    page = st.selectbox("Page", range(1,num_batches+1))

batch = files[(page-1)*batch_size : page*batch_size]

grid = st.columns(row_size)
col = 0
for image in batch:
    with grid[col]:
        st.image(f'{images_path}/{image}', caption=image.split('.')[0], use_column_width=True)   
    col = (col + 1) % row_size