import auth
import shutil
import pandas as pd

from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, Body, Depends
from fastapi.security.api_key import APIKey

from prediction.yolov5.classify.predict import run as run_classification

app = FastAPI(
    title="WasKrabbeltDa? - Backend",
    description="""Obtain data from your local insect-detect camera.""",
    version="0.0.1",
)

@app.post("/classify/{tracking_id}")
async def classify(
                files: list[UploadFile],
                tracking_id: int, 
                api_key: APIKey = Depends(auth.get_api_key),
                start_date: datetime = Body(...),
                end_date: datetime = Body(...),
                duration_s: int = Body(...)):
    
    # Store the uploaded tracking files
    #get current date
    data_path = Path("data", f"{datetime.today().strftime('%Y-%m-%d')}", f"{tracking_id}-{datetime.now().strftime('%H-%M-%S')}")
    data_path.mkdir(exist_ok=True, parents=True)#TODO: exist_ok logic
    for file in files:
        file_path = data_path / file.filename
        with open(file_path, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

    # Run classification, obtain mean of classification results
    classification_results = run_classification(data_path)
    
    # Store classification results
    new_row = {
            'date': datetime.now().date(),
            'start_time': start_date,
            'end_time': end_date,
            'duration_s': duration_s,
            'track_ID': tracking_id,
            'track_ID_imgs': len(files),
            'top1': classification_results["top1"],
            'top1_prob': classification_results["top1_prob"],
            }
    data = pd.read_csv("classification_data.csv")
    data.loc[len(data)] = new_row
    data.to_csv("classification_data.csv", index=False)
    
    return {"success": True}

@app.get("/data")
def read_root(api_key: APIKey = Depends(auth.get_api_key)):
    data = pd.read_csv("classification_data.csv")
    return data.to_dict(orient="records")
