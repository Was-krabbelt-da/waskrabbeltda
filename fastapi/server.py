import os
from fastapi.responses import FileResponse
import auth
import shutil
import pandas as pd

from pathlib import Path
from datetime import datetime
from fastapi import BackgroundTasks, FastAPI, UploadFile, Body, Depends
from fastapi.security.api_key import APIKey

from prediction.yolov5.classify.predict import run as run_classification

import threading

CLASSIFICATION_DATA_PATH = Path(".", "data", "classification_data.csv")
lock = threading.Lock()

app = FastAPI(
    title="WasKrabbeltDa? - Backend",
    description="""Obtain data from your local insect-detect camera.""",
    version="0.0.1",
)

def remove_file(path: str) -> None:
    os.unlink(path)

# Setup
if not CLASSIFICATION_DATA_PATH.exists():
    data = pd.DataFrame(
        columns=[
            "date",
            "start_time",
            "end_time",
            "duration_s",
            "track_ID",
            "track_ID_imgs",
            "tracking_run_ID",
            "top1",
            "top1_prob",
        ]
    )
    data.to_csv(CLASSIFICATION_DATA_PATH, index=False)


@app.post("/classify/{tracking_id}")
def classify(
    files: list[UploadFile],
    tracking_id: int,
    api_key: APIKey = Depends(auth.get_api_key),
    start_date: datetime = Body(...),
    end_date: datetime = Body(...),
    duration_s: int = Body(...),
):
    lock.acquire()

    # Store the uploaded tracking files
    # get current date
    tracking_run_id = f"ID{tracking_id}-{end_date.strftime('%H-%M-%S')}"
    data_path = Path("data", f"{end_date.strftime('%Y-%m-%d')}", tracking_run_id)
    data_path.mkdir(exist_ok=True, parents=True)#TODO: exist_ok logic
    for file in files:
        file_path = data_path / file.filename
        with open(file_path, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

    # Run classification, obtain mean of classification results
    classification_results = run_classification(data_path)

    # Store classification results
    new_row = {
        "date": end_date.date(),
        "start_time": start_date,
        "end_time": end_date,
        "duration_s": duration_s,
        "track_ID": tracking_id,
        "track_ID_imgs": len(files),
        "tracking_run_ID": tracking_run_id,
        "top1": classification_results["top1"],
        "top1_prob": classification_results["top1_prob"],
    }

    data = pd.read_csv(CLASSIFICATION_DATA_PATH)
    data.loc[len(data)] = new_row
    data.to_csv(CLASSIFICATION_DATA_PATH, index=False)

    lock.release()

    return {"success": True}


@app.get("/data/classification")
def get_classification_data(api_key: APIKey = Depends(auth.get_api_key)):
    data = pd.read_csv(CLASSIFICATION_DATA_PATH)
    return data.to_dict(orient="records")

@app.get("/data/all")
def get_all_data(background_tasks: BackgroundTasks, api_key: APIKey = Depends(auth.get_api_key)):
    zip_archive_name = shutil.make_archive(f"waskrabbeltda_data_{datetime.today().strftime('%Y-%m-%d')}", 'zip', 'data')
    background_tasks.add_task(remove_file, zip_archive_name)
    return FileResponse(zip_archive_name)

@app.get("/data/{date}/{tracking_run}")
def get_tracking_run_images(date: str, tracking_run: str, background_tasks: BackgroundTasks, api_key: APIKey = Depends(auth.get_api_key)):
    zip_archive_name = shutil.make_archive(f"waskrabbeltda_data_{date}_{tracking_run}", 'zip', Path("data", date, tracking_run))
    background_tasks.add_task(remove_file, zip_archive_name)
    return FileResponse(zip_archive_name)

@app.get("/data/tracking_runs")
def get_tracking_runs(api_key: APIKey = Depends(auth.get_api_key)):
    tracking_runs = {}
    # iterate over each date folder in data
    data_path = Path("data")
    for folder in os.listdir(data_path):
        if not os.path.isdir(Path(data_path, folder)) or folder == "lost+found":
            continue
        tracking_runs[folder] = []
        for tracking_run in os.listdir(Path(data_path,folder)):
            tracking_runs[folder].append(tracking_run)
    return tracking_runs
