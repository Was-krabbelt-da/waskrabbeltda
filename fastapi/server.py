# import io

from pathlib import Path
from typing import Annotated
from datetime import datetime
from fastapi import FastAPI, File
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

data = pd.read_csv("new_classification_data.csv")

#TODO: Continue working here!
#TODO: Make async
#TODO: Receive filename and timestamp
#TODO: checkout what top1_prob_mean is and how to get it
@app.post("/classify/{tracking_id}")
async def classify(tracking_id: int, files: Annotated[list[bytes], File(timestamp=datetime)]):
    data_path = Path("data", str(tracking_id))
    print(data_path)
    data_path.mkdir(exist_ok=True)
    for i, file in enumerate(files):
        with open(data_path / f"{i}.jpg", "wb") as f:
            f.write(file)
    #get json object with date,time,track_ID,track_ID_imgs,top1,top1_prob
    classification_results = run_classification(tracking_id=tracking_id)
    new_row = {'date': datetime.today().date(),
               'time': datetime.now().time(),
               'track_ID': tracking_id,
               'track_ID_imgs': len(files),
               'top1': classification_results["top1"],
               'top1_prob': classification_results["top1_prob"],
               }
    data.loc[len(data)] = new_row
    data.to_csv("new_classification_data.csv", index=False)
    return {"success": True}

# #TODO: Make async
# @app.post("/classify")
# def classify():
#     """Classify"""
#     run_classification(tracking_id=139)
#     return {"status": "success"}
#     # segmented_image = get_segments(model, file)
#     # bytes_io = io.BytesIO()
#     # segmented_image.save(bytes_io, format="PNG")
#     # return Response(bytes_io.getvalue(), media_type="image/png")

@app.get("/data")
def read_root():
    return data.to_dict(orient="records")
