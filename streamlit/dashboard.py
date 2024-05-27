import io
import zipfile
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import math
from pathlib import Path
import os
import datetime
import json
import locale
import random
import matplotlib.pyplot as plt  # für Kreisdiagramme
from PIL import Image  # für das Logo
import requests
from dotenv import load_dotenv

load_dotenv()

CLASSIFICATION_DATA_ENDPOINT = (
    f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data/classification"
)
DATA_ALL_ENDPOINT = f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data/all"
TRACKING_RUNS_ENDPOINT = (
    f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data/tracking_runs"
)
MOST_RECENT_INSECT_ENDPOINT = (
    f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data/most_recent_insect"
)

IMAGE_ENDPOINT = f"{os.getenv('DATA_ENDPOINT', 'http://fastapi:8000')}/data"

API_KEY = os.getenv("API_KEY")
# CAMERA_NAME = os.getenv("CAMERA_NAME", "waskrabbeltda")


# Set the locale to German for date formatting
locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")

# Set streamlit page configuration, this needs to be the first streamlit command.
st.set_page_config(
    page_title="Was krabbelt da?",
    page_icon="🐞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# TODO: Make configurable.
# Define constants
CAMERA_NAME = "krabbeltrap1"
CAMERA_POSITION = "Freundschaftsinsel, Potsdam"

START_TIME_COLUMN = "start_time"
END_TIME_COLUMN = "end_time"
DURATION_COLUMN = "duration_s"

EXCLUDE_CLASSES = [
    "none_dirt",
    "none_bg",
    "none_dirt",
    "none_bird",
    "none_shadow",
]

# Load german translation
with open("german_translation.json") as json_config:
    GERMAN_TRANSLATION_LABELS = json.load(json_config)
# Load krabbler funfacts
with open("funfacts.json") as json_funfacts:
    FUNFACTS = json.load(json_funfacts)
logo = Image.open("assets/waskrabbeltda-logo.png")
# Berechne die neue Größe
width, height = logo.size
new_size = (int(width * 0.1), int(height * 0.1))
resized_logo = logo.resize(new_size)

# Configure CSS Styling
st.markdown(
    """
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
 .header {
        display: flex;
        align-items: center;
    }
    .header img {
        width: 20%;
    }
    .header h1 {
        margin-left: 20px;
    }

</style>
""",
    unsafe_allow_html=True,
)


# Functions
def translate_label(label):
    if label in GERMAN_TRANSLATION_LABELS:
        return GERMAN_TRANSLATION_LABELS[label]
    return label


def get_funfact(label):
    if label in FUNFACTS:
        return FUNFACTS[label].get("funfact", "")
    return ""


# Diese Funktion wird verwendet, um die letzten fünf Schnappschüsse mit unterschiedlichen IDs zu erhalten
def get_latest_unique_snapshots(directory, num_snapshots=5):
    snapshots = []
    seen_ids = set()
    all_files = sorted(
        os.listdir(directory),
        key=lambda x: os.path.getctime(os.path.join(directory, x)),
        reverse=True,
    )

    for file in all_files:
        snap_id = file.split("_")[0]  # Extrahiere die ID aus dem Dateinamen
        if snap_id not in seen_ids:
            snapshots.append(file)
            seen_ids.add(snap_id)
        if len(snapshots) >= num_snapshots:
            break

    return snapshots


def get_unique_snapshots(date, num_snapshots=15):
    snapshots = []

    tracking_runs = requests.get(
        TRACKING_RUNS_ENDPOINT, headers={"access_token": API_KEY}
    ).json()

    last_tracked_runs = tracking_runs[date]

    for run in last_tracked_runs[:num_snapshots]:
        images_path = Path("data", date, run)

        if not images_path.exists():
            images_path.mkdir(parents=True)
            # get zip file with all images for selected run
            images_endpoint = f"{IMAGE_ENDPOINT}/{date}/{run}"
            zip_images_response = requests.get(
                images_endpoint, headers={"access_token": API_KEY}
            )
            zip_images = zipfile.ZipFile(io.BytesIO(zip_images_response.content))
            zip_images.extractall(images_path)

        run_files = os.listdir(images_path)
        # select random run file
        rand_index = random.randint(0, len(run_files) - 1)
        snapshots.append(Path(run, run_files[rand_index]))
    return snapshots


def make_pie_chart(data):
    # Bereite die Daten für das Kreisdiagramm vor
    label_counts = data["top1"].value_counts()
    labels = label_counts.index
    sizes = label_counts.values
    # Erstelle das Kreisdiagramm
    fig, ax = plt.subplots()
    ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=plt.cm.Greens(np.linspace(0, 1, len(labels))),
    )
    ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(fig)


# Load data with caching, column renaming and data type conversions.
# Create additionally needed data columns here.
# @st.cache_data
def load_data():
    response = requests.get(CLASSIFICATION_DATA_ENDPOINT, headers={'access_token': API_KEY})
    data = response.json()
    data = pd.DataFrame(data)
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis="columns", inplace=True)
    data[START_TIME_COLUMN] = pd.to_datetime(data[START_TIME_COLUMN])
    data[END_TIME_COLUMN] = pd.to_datetime(data[END_TIME_COLUMN])
    data["hour"] = data[START_TIME_COLUMN].dt.hour
    # Remove observations which are not classified as insects
    dirt_data = data.copy()
    data = data[~data["top1"].isin(EXCLUDE_CLASSES)]

    # Translate classification labels to German
    data["top1"] = data["top1"].map(translate_label)

    return data, dirt_data


# Plot functions
# Create heatmap with Altair
def make_heatmap(input_df, input_y, input_x, input_color, input_color_theme):
    heatmap = (
        alt.Chart(input_df)
        .mark_rect()
        .encode(
            y=alt.Y(
                f"{input_y}:O",
                axis=alt.Axis(
                    title="Insekt",
                    titleFontSize=18,
                    titlePadding=15,
                    titleFontWeight=900,
                    labelAngle=0,
                ),
            ),
            x=alt.X(
                f"{input_x}:O",
                axis=alt.Axis(
                    title="Uhrzeit",
                    titleFontSize=18,
                    titlePadding=15,
                    titleFontWeight=900,
                ),
            ),
            color=alt.Color(
                f"max({input_color}):Q",
                legend=None,
                scale=alt.Scale(scheme=input_color_theme),
            ),
            stroke=alt.value("black"),
            strokeWidth=alt.value(0.25),
        )
        .properties(width=900)
        .configure_axis(labelFontSize=12, titleFontSize=12)
    )
    return heatmap


# Load data
data, dirt_data = load_data()

# Dashboard content

# Define sidebar. The sidebar will be displayed on the left side of the page and can be toggled by the user.
# The sidebar contains the title and elements for user input, e.g. for choosing a color theme or a day to view.
with st.sidebar:
    st.title("Tagesauswahl")

    # Create a list of unique dates in the data and reverse the list to display the most recent date first
    day_list = list(data.date.unique())[::-1]
    # Create a selectbox to choose a date from the list of unique dates and create a new dataframe
    # containing only observations from the selected date
    selected_date = st.selectbox("Wähle einen Tag aus", day_list)
    df_selected_day = data[data.date == selected_date]
    df_selected_daydirt = dirt_data[dirt_data.date == selected_date]

    # Dates with images
    # st.subheader("Tage mit Bildern")

    # tracking_runs = requests.get(
    #     TRACKING_RUNS_ENDPOINT, headers={"access_token": API_KEY}
    # ).json()
    # days_with_images = sorted(list(tracking_runs.keys()))[::-1]
    # # Select day
    # selected_day = st.selectbox("Wähle einen Tag mit Bildern aus", days_with_images)
    # day_tracking_runs = sorted(tracking_runs[selected_day])

    # selected_run = st.selectbox("Wähle einen Tracking Run aus", day_tracking_runs)

    st.image("assets/miz-logo.png")
    st.markdown(
        "**Was krabbelt da** wird unterstützt durch das Medieninnovationszentrum Babelsberg"
    )
    st.markdown("Kontakt: webmaster(at)joachimbudde.de")
# st.image(resized_logo)
# st.header("Was krabbelt da?")
col1, col2 = st.columns([1, 5])  # Passe die Breite der Spalten nach Bedarf an

with col1:
    st.image(resized_logo, use_column_width=True)

with col2:
    st.title("Krabbler-Dashboard")

tab1, tab2 = st.tabs(["Heute", "Gesamt"])

with tab1:
    # Set up layout for main content
    # This creates a two-column layout, with a width ratio of 1:3.
    columns = st.columns([1, 3], gap="medium")

    # Column 1: Display count of each insect category for the selected date.
    # Count occurrences, sort by count, and display with st.metric elements.
    # The st.metric elements are styled with CSS in the header of the script.
    with columns[0]:
        datum_deutsch = datetime.datetime.strptime(selected_date, "%Y-%m-%d").strftime(
            "%-d. %B %Y"
        )
        st.subheader("Überblick")
        total_counts = len(data)
        total_counts_today = len(df_selected_day)
        st.markdown("**Kameraname**: " + CAMERA_NAME)
        st.markdown("**Kamerastandort**: " + CAMERA_POSITION)
        st.markdown("**Krabbler heute**: " + str(total_counts_today))
        st.markdown("**Krabbler gesamt**: " + str(total_counts))
        st.divider()
        # TOP-SICHTUNGEN
        st.markdown("**" + datum_deutsch + "**")
        st.subheader("⭐ Top-Sichtungen")
        label_counts = df_selected_day["top1"].value_counts()
        for i, (translated_label, count) in enumerate(label_counts.items()):
            if i < 3:
                funfact = get_funfact(translated_label)
                if funfact:
                    st.markdown(
                        f"""
                        <div style='text-align: center;'>
                            <div style='font-size: 24px; color: green;'>{count}x</div>
                            <div>{translated_label}</div>
                            <div style='font-size: 12px;'>💡 {funfact}</div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    st.divider()
                else:
                    st.markdown(
                        f"""
                        <div style='text-align: center;'>
                            <div style='font-size: 28px; color: green;'>{count}x</div>
                            <div>{translated_label}</div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    st.divider()

            else:
                st.markdown(
                    f"""
                    <div style='text-align: center;'>
                        <div style='font-size: 18px; color: black;'>{count}x</div>
                        <div>{translated_label}</div>
                    </div>
                """,
                    unsafe_allow_html=True,
                )
                st.divider()
        # Erstelle und zeige das Kreisdiagramm für den ausgewählten Tag
        st.markdown("**Alle Insekten am " + datum_deutsch + "**")
        st.markdown(
            "Wie sich die Tagesgäste auf die verschiedenen Krabbler-Klassen verteilen."
        )
        make_pie_chart(df_selected_day)
        st.divider()
        st.markdown("**" + datum_deutsch + "**")
        st.subheader("👽 Fehlsichtungen")
        dirt_count_today = (
            df_selected_daydirt["top1"].value_counts().get("none_dirt", 0)
        )
        bird_count_today = (
            df_selected_daydirt["top1"].value_counts().get("none_bird", 0)
        )
        # Anzeige der gefilterten Fehlsichtungen "Blätter" und "Vögel" nur für den ausgewählten Tag
        st.markdown(
            f"""
            <div style='text-align: center; color: grey;'>
                <div style='font-size: 24px;'>🍃 {dirt_count_today} x</div>
                <div>Blätter und andere UFOs</div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown(
            f"""
            <div style='text-align: center; color: grey;'>
                <div style='font-size: 24px;'> 🐦 {bird_count_today}x</div>
                <div>Vögel</div>
            </div>
        """,
            unsafe_allow_html=True,
        )
    # Column 2: Display visualizations, stacked on top of each other.
    with columns[1]:
        # Display raw data if checkbox is selected.

        # Create a histogram based on the data for the selected day, counting the number of insects per hour.
        # Display it as a bar chart provided by streamlit.
        st.subheader("Tagesübersicht")
        st.markdown(
            "Je nachdem wie der Tag verläuft ist auch vor unserer Linse unterschiedlich viel los: An warmen Sommertagen ist mehr los, als an kühlen. Wenn es regnet, besuchen weniger Krabbler unsere Kamera. Und auch wenn es stürmt, bleiben viele Fluginsekten lieber an geschützten Orten. Hier siehst du die **Anzahl der Insekten pro Stunde**."
        )

        # Histogramm-Werte vorbereiten
        hist_values = (
            df_selected_day[START_TIME_COLUMN]
            .dt.hour.value_counts()
            .sort_index()
            .reset_index()
        )
        hist_values.columns = ["hour", "count"]

        # Sicherstellen, dass alle Stunden von 0 bis 23 enthalten sind
        all_hours = pd.DataFrame({"hour": range(24)})
        hist_values = all_hours.merge(hist_values, on="hour", how="left").fillna(0)

        # Bar-Chart mit Altair erstellen
        bar_chart = (
            alt.Chart(hist_values)
            .mark_bar(color="#92c01f")
            .encode(
                x=alt.X(
                    "hour:O",
                    title="Uhrzeit",
                    axis=alt.Axis(
                        title="Uhrzeit",
                        titleFontSize=18,
                        titlePadding=15,
                        titleFontWeight=900,
                        labelFontSize=12,
                        labelExpr="datum.value + ' Uhr'",
                    ),
                ),
                y=alt.Y(
                    "count:Q",
                    title="Anzahl",
                    axis=alt.Axis(
                        title="Anzahl",
                        titleFontSize=18,
                        titlePadding=15,
                        titleFontWeight=900,
                        labelFontSize=12,
                    ),
                ),
            )
            .properties(width=900)
            .configure_axis(labelFontSize=12, titleFontSize=12)
        )

        st.altair_chart(bar_chart, use_container_width=True)

        st.subheader("Stundenblick")
        st.markdown(
            "Viele Insekten richten sich nach dem Tageslicht. Zu jeder Stunde des Tages besuchen andere Krabbler unsere Kamera: Marienkäfer zum Beispiel sind Frühaufsteher, Ameisen warten auf die warmen Sonnenstrahlen, Nachtfalter warten auf die Dunkelheit. Hier kannst du jede Stunde des Tages einzeln in den Blick nehmen. "
        )
        # Anpassen des Sliders, um 0 Uhr und 24 Uhr zu beschriften
        hour_to_filter = st.slider("Wähle eine Stunde aus", 0, 24, 15, format="%d Uhr")

        st.markdown("**Wer war um %s Uhr unterwegs?**" % hour_to_filter)
        if hour_to_filter == 24:
            filtered_data = df_selected_day[
                df_selected_day[START_TIME_COLUMN].dt.hour == 0
            ]
        else:
            filtered_data = df_selected_day[
                df_selected_day[START_TIME_COLUMN].dt.hour == hour_to_filter
            ]

        if filtered_data.empty:
            st.write("Keine Daten für dieses Zeitfenster")
        else:
            st.bar_chart(filtered_data["top1"].value_counts(), color="#92c01f")

        # filtered_data = df_selected_day[df_selected_day[START_TIME_COLUMN].dt.hour == hour_to_filter]
        # st.bar_chart(filtered_data['top1'].value_counts())
        # Display a horizontal divider.
        st.divider()

        # Experimental image gallery
        st.subheader("Die letzten Schnappschüsse")
        st.markdown(
            "Wir fotografieren unsere krabbelnden Stars von oben. So können wir sie am Besten erkennen. Unser roter Teppich ist grün: eine Acrylglasplatte bedruckt mit einer abstrakten Wiese. Unsere Kamera erkennt die Krabbler nicht nur an Farbe und Größe, sondern auch daran, wie schnell und wie sie sich bewegen. Statt ein einziges hochauflösendes Foto, machen wir viele. **Erkennst du, wer da krabbelt?**"
        )
        # get most recent snapshots

        most_recent_directory_response = requests.get(
            MOST_RECENT_INSECT_ENDPOINT, headers={"access_token": API_KEY}
        ).json()
        most_recent_date = most_recent_directory_response["most_recent_date"]
        most_recent_tracking_run = most_recent_directory_response[
            "most_recent_tracking_run"
        ]
        most_recent_tracking_run_path = Path(
            "data", most_recent_date, most_recent_tracking_run
        )
        if not most_recent_tracking_run_path.exists():
            most_recent_tracking_run_path.mkdir(parents=True)
            # get zip file with all images for selected run
            images_endpoint = (
                f"{IMAGE_ENDPOINT}/{most_recent_date}/{most_recent_tracking_run}"
            )
            zip_images_response = requests.get(
                images_endpoint, headers={"access_token": API_KEY}
            )
            zip_images = zipfile.ZipFile(io.BytesIO(zip_images_response.content))
            zip_images.extractall(most_recent_tracking_run_path)

        files = os.listdir(most_recent_tracking_run_path)

        # obtain label if available
        label = ""
        classified_runs = list(
            dirt_data[dirt_data["date"] == most_recent_date]["tracking_run_id"]
        )
        if most_recent_tracking_run in classified_runs:
            label = dirt_data[dirt_data["tracking_run_id"] == most_recent_tracking_run][
                "top1"
            ].values[0]

        controls = st.columns(4)
        with controls[0]:
            batch_size = st.select_slider("Batch size:", range(10, 30, 5), value=10)
        with controls[1]:
            row_size = st.select_slider("Row size:", range(1, 6), value=5)
        num_batches = math.ceil(len(files) / batch_size)
        with controls[2]:
            page = st.selectbox("Seite", range(1, num_batches + 1))
        with controls[3]:
            if label:
                st.write(f"Label: {translate_label(label)}")
            else:
                st.write("No classification data available for this run.")

        batch = files[(page - 1) * batch_size : page * batch_size]

        grid = st.columns(row_size)
        col = 0
        for image in batch:
            with grid[col]:
                st.image(
                    f"{most_recent_tracking_run_path}/{image}",
                    caption="Schnappschuss "
                    + image.split("_")[2]
                    + " Label: "
                    + translate_label(label),
                    use_column_width=True,
                )
            col = (col + 1) % row_size


with tab2:
    # Gesamtübersicht nach Arten
    # Erstellen einer Liste der verfügbaren Arten
    # Erstellen einer Liste der verfügbaren Arten
    st.subheader("Gesamtübersicht der unterschiedlichen Krabbler")
    st.markdown(
        "Die Linien zeigen, wie sich die Zahl der Insekten an den einzelnen Tagen verändert. Das kann viele Gründe haben: entweder die Bedingungen waren für Schmetterlinge oder Honigbienen an einem Tag besser, als am anderen. Oder sie haben zufälligerweise unsere Kamera nicht angesteuert. **Du kannst die einzelnen Krabbler-Klassen zuwählen oder ausblenden.**"
    )
    # Erstellen einer Liste der verfügbaren Arten
    available_species = data["top1"].unique()
    selected_species = st.multiselect(
        "Wähle Arten aus", available_species, default=available_species[:5]
    )

    # Filtere die Daten nach den ausgewählten Arten
    filtered_time_data = data[data["top1"].isin(selected_species)]

    if filtered_time_data.empty:
        st.write("Keine Daten für die ausgewählten Arten")
    else:
        # Gruppieren und Aggregieren der Daten
        time_series_data = (
            filtered_time_data.groupby(["date", "top1"])
            .size()
            .reset_index(name="count")
        )

        # Formatieren des Datums in deutscher Schreibweise
        time_series_data["date"] = pd.to_datetime(time_series_data["date"]).dt.strftime(
            "%-d. %-m."
        )

        # Erstellen des Liniendiagramms mit Altair
        line_chart = (
            alt.Chart(time_series_data)
            .mark_line()
            .encode(
                x=alt.X(
                    "date:N",
                    title="Datum",
                    axis=alt.Axis(
                        titleFontSize=18, titlePadding=15, titleFontWeight=900
                    ),
                ),
                y=alt.Y(
                    "count:Q",
                    title="Anzahl der Sichtungen",
                    axis=alt.Axis(
                        titleFontSize=18, titlePadding=15, titleFontWeight=900
                    ),
                ),
                color=alt.Color("top1:N", legend=alt.Legend(title="Art")),
            )
            .properties(width=900)
            .configure_axis(labelFontSize=12, titleFontSize=12)
        )
        st.altair_chart(line_chart, use_container_width=True)

    # Gesamtübersicht
    st.subheader("Gesamtübersicht aller Sichtungen")
    st.markdown(
        "Hier ist ein Diagramm, das die Gesamtwerte der verschiedenen Krabbler-Klassen anzeigt, die wir seit Beginn unserer Messungen beobachtet haben. Was sind Krabbler-Klassen? Das ist das, was wir schon können. Unser KI-Modell lernt noch. Wir zählen zum Beispiel Käfer (die nicht Marienkäfer sind), weil Marienkäfer erkennen wir schon extra und Wanzen (die keine Streifenwanzen sind), weil Streifenwanzen erkennt die Kamera auch schon sehr sicher."
    )
    # Aggregiere die Daten, um die Gesamtzahl der Beobachtungen pro Insektenklasse zu erhalten.
    total_label_counts = data["top1"].value_counts()

    # Erstellen eines DataFrames für die Visualisierung
    total_label_df = pd.DataFrame(total_label_counts).reset_index()
    total_label_df.columns = ["Insektenklasse", "Anzahl"]

    # Erstellen des Bar-Charts mit Altair
    bar_chart = (
        alt.Chart(total_label_df)
        .mark_bar(color="#92c01f")
        .encode(
            x=alt.X(
                "Insektenklasse:N",
                title="Insekten",
                axis=alt.Axis(
                    title="Insekten",
                    titleFontSize=18,
                    titlePadding=15,
                    titleFontWeight=900,
                    labelFontSize=12,
                    labelAngle=-45,
                ),
            ),
            y=alt.Y(
                "Anzahl:Q",
                title="Anzahl",
                axis=alt.Axis(
                    title="Anzahl",
                    titleFontSize=18,
                    titlePadding=15,
                    titleFontWeight=900,
                    labelFontSize=12,
                ),
            ),
        )
        .properties(width=900)
        .configure_axis(labelFontSize=12, titleFontSize=12)
    )

    st.altair_chart(bar_chart, use_container_width=True)

    st.subheader("Wer ist wann unterwegs?")
    st.markdown(
        "Manche Insekten sind morgends aktiv, andere abends oder nachts. In dieser **Heatmap** kannst du die **Aktivitätszeiten** der verschiedenen Krabbler ablesen."
    )
    # Create a heatmap showing the distribution of insect categories over the hours of the day.
    # Create a dedicated dataframe for the heatmap with the count of each insect category per hour.
    # Use the make_heatmap function to create the heatmap with Altair and display it with st.altair_chart.
    heatmap_df = data.groupby(["top1", "hour"]).size().reset_index(name="count")
    heatmap = make_heatmap(heatmap_df, "top1", "hour", "count", "greens")
    st.altair_chart(heatmap, use_container_width=True)

    # Display a horizontal divider.
    st.divider()

    # Scatter Chart Wie lang sind die verschiedenen Arten vor der Kamera?
    st.subheader("Wie lange sind die Insekten vor der Kamera?")
    st.markdown(
        "Manche Krabbler huschen nur kurz dabei, andere machen es sich auf der Bühne vor unserer Kamera länger bequem oder drehen mehrere Runden. Hier siehst du, wie lange unsere Besucher bleiben."
    )

    # Berechnen der durchschnittlichen Zeit pro Insektenart für die Gesamtdaten
    avg_duration_data = data.groupby("top1")[DURATION_COLUMN].mean().reset_index()
    avg_duration_data.columns = ["Insektenart", "Durchschnittliche Zeit (s)"]

    # Erstellen des Scatter-Charts mit Altair
    scatter_chart = (
        alt.Chart(avg_duration_data)
        .mark_point(size=100, opacity=0.7)
        .encode(
            x=alt.X(
                "Insektenart:N",
                title="Insekten",
                axis=alt.Axis(titleFontSize=18, titlePadding=15, titleFontWeight=900),
            ),
            y=alt.Y(
                "Durchschnittliche Zeit (s):Q",
                title="Durchschnittliche Zeit (s)",
                axis=alt.Axis(titleFontSize=18, titlePadding=15, titleFontWeight=900),
            ),
            tooltip=["Insektenart:N", "Durchschnittliche Zeit (s):Q"],
        )
        .properties(width=900)
        .configure_axis(labelFontSize=12, titleFontSize=12)
        .configure_mark(color="#92c01f")
    )
    st.altair_chart(scatter_chart, use_container_width=True)

    # Galerie mit den letzten 5 Snapshots des Tages
    st.subheader("Live vom grünen Teppich")
    st.markdown(
        "Wir fotografieren unsere krabbelnden Stars von oben. So können wir sie am besten erkennen. Unser roter Teppich ist grün: eine Acrylglasplatte bedruckt mit einer abstrakten Wiese. So sehen einige Bilder der letzten Krabbler aus – oder eben nur bewegende Schatten oder Blätter. Übrigens: Die Kamera macht von jedem Krabbler viel mehr Bilder: Unsere Kamera erkennt die Krabbler nicht nur an Farbe und Größe, sondern auch daran, wie schnell und wie sie sich bewegen.\n**Erkennst du, wer da krabbelt?**"
    )
    directory = Path("data", most_recent_date)

    # Erhalte die letzten fünf Schnappschüsse mit unterschiedlichen IDs
    snapshots_today = get_unique_snapshots(most_recent_date)

    grid = st.columns(5)  # Ändere diese Zahl, um die Anzahl der Spalten anzupassen
    col = 0
    for image in snapshots_today:
        # insect_key = image.split("_")[1]  # Extrahiere den Schlüssel aus dem Dateinamen
        # insect_name = translate_label(insect_key)
        with grid[col]:
            st.image(
                f"{directory}/{image}",
                # caption=f'Schnappschuss Nr. {image.split("_")[0]}: {insect_name}',
                use_column_width=True,
            )
        col = (col + 1) % 5
