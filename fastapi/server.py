# import io

from pathlib import Path
import shutil
from typing import Annotated
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form, Body
import pandas as pd
import os
from prediction.yolov5.classify.predict import run as run_classification

# model = get_segmentator()

app = FastAPI(
    title="WasKrabbeltDa? - Backend",
    description="""Obtain data from your local insect-detect camera.""",
    version="0.0.1",
)

# FILE = Path(__file__).resolve()
# #TODO: ROOT somehow needs to be both yolo5 and prediction, get better folder structure running
# ROOT = FILE.parents[1]  # prediction directory -> START HERE
# SERVER_ROOT = FILE.parents[3]

data = pd.read_csv("classification_data.csv")

#TODO: Continue working here!
#TODO: Make async
#TODO: Checkout if we can get all timestamps without dpeending on naming
#TODO: checkout what top1_prob_mean is and how to get it
@app.post("/classify/{tracking_id}")
async def classify(
                files: list[UploadFile],
                tracking_id: int, 
                start_date: datetime = Body(...),
                end_date: datetime = Body(...),
                duration_s: int = Body(...)):
    data_path = Path("data", str(tracking_id))
    data_path.mkdir(exist_ok=True)#TODO: exist_ok logic
    # timestamps = []
    for file in files:
        # date_string = file.filename.split(".")[0]
        # timestamp = datetime.strptime(date_string, "%Y-%m-%d_%H-%M-%S")
        # timestamps.append(timestamp)
        file_path = data_path / file.filename
        with open(file_path, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object) 
    #convert timestamps to datetime
    # timestamps.sort()
    #get json object with date,time,track_ID,track_ID_imgs,top1,top1_prob
    classification_results = run_classification(tracking_id=tracking_id)
    new_row = {'date': datetime.now().date(),
               'start_time': start_date,
                'end_time': end_date,
                'duration_s': duration_s,
               'track_ID': tracking_id,
               'track_ID_imgs': len(files),
               'top1': classification_results["top1"],
               'top1_prob': classification_results["top1_prob"],
               }
    data.loc[len(data)] = new_row
    print(data)
    data.to_csv("classification_data.csv", index=False)
    return {"success": True}

@app.get("/data")
def read_root():
    return data.to_dict(orient="records")
