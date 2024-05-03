# YOLOv5 🚀 by Ultralytics, AGPL-3.0 license
"""
Run YOLOv5 classification inference on images, videos, directories, globs, YouTube, webcam, streams, etc.

Usage - sources:
    $ python classify/predict.py --weights yolov5s-cls.pt --source 0                               # webcam
                                                                   img.jpg                         # image
                                                                   vid.mp4                         # video
                                                                   screen                          # screenshot
                                                                   path/                           # directory
                                                                   list.txt                        # list of images
                                                                   list.streams                    # list of streams
                                                                   'path/*.jpg'                    # glob
                                                                   'https://youtu.be/LNwODJXcvt4'  # YouTube
                                                                   'rtsp://example.com/media.mp4'  # RTSP, RTMP, HTTP stream

Usage - formats:
    $ python classify/predict.py --weights yolov5s-cls.pt                 # PyTorch
                                           yolov5s-cls.torchscript        # TorchScript
                                           yolov5s-cls.onnx               # ONNX Runtime or OpenCV DNN with --dnn
                                           yolov5s-cls_openvino_model     # OpenVINO
                                           yolov5s-cls.engine             # TensorRT
                                           yolov5s-cls.mlmodel            # CoreML (macOS-only)
                                           yolov5s-cls_saved_model        # TensorFlow SavedModel
                                           yolov5s-cls.pb                 # TensorFlow GraphDef
                                           yolov5s-cls.tflite             # TensorFlow Lite
                                           yolov5s-cls_edgetpu.tflite     # TensorFlow Edge TPU
                                           yolov5s-cls_paddle_model       # PaddlePaddle

---

Modified by:  Maximilian Sittinger (https://github.com/maxsitt)
Website:      https://maxsitt.github.io/insect-detect-docs/
License:      GNU AGPLv3 (https://choosealicense.com/licenses/agpl-3.0/)

Modifications:
- add additional options (argparse arguments):
  '--sort-top1' sort images to folders with predicted top1 class as folder name
  '--sort-prob' sort images first by probability and then by top1 class (requires --sort-top1)
  '--concat-csv' concatenate metadata .csv files and append classification results
  '--new-csv' create new .csv file with classification results
- write only top1 class + prob on to image in top left corner (if not sort-top1)
- save classification results to lists (image filename and top1, top2, top3 class + probability)
- sort images to folders with predicted top1 class as folder name
  and do not write top1 class + prob on to image as text (if sort-top1)
- sort images first by top1 probability (0-0.5, 0.5-0.8, 0.8-1) and then by top1 class
  and do not write top1 class + prob on to image as text (if sort-top1 + sort-prob)
- print estimated inference time per image
- write classification results to 'results/pred_results.csv'
- write mean classification probability per top 1 class to '/results/top1_prob_mean.csv'
- save boxplot with the classification probability per top 1 class as 'results/top1_prob.png'
- save barplot with the mean classification probability per top 1 class as 'results/top1_prob_mean.png'
- concatenate all metadata .csv files in the 'data' folder and add new columns with
  classification results, save to 'results/{name}_metadata_classified.csv' (if concat-csv)
- create new .csv file with classification results and timestamp + tracking ID
  extracted from image filename, save to 'results/{name}_data_classified.csv' (if new-csv)
- print script run time
"""

import argparse
import os
import platform
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import torch
import torch.nn.functional as F

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]  # prediction directory -> START HERE
SERVER_ROOT = FILE.parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from ultralytics.utils.plotting import Annotator

from models.common import DetectMultiBackend
from utils.augmentations import classify_transforms
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from utils.general import (
    LOGGER,
    Profile,
    check_file,
    check_img_size,
    check_imshow,
    check_requirements,
    colorstr,
    cv2,
    increment_path,
    print_args,
    strip_optimizer,
)
from utils.torch_utils import select_device, smart_inference_mode

# Set start time for script execution timer
start_time = time.monotonic()

@smart_inference_mode()
def run(
    weights=ROOT / "weights/efficientnet-b0_imgsz128.onnx",  # model.pt path(s)
    source=SERVER_ROOT / "data",  # file/dir/URL/glob/screen/0(webcam)
    tracking_id=0,  # source track number
    data=ROOT / "data/coco128.yaml",  # dataset.yaml path
    imgsz=(128, 128),  # inference size (height, width)
    device="cpu",  # cuda device, i.e. 0 or 0,1,2,3 or cpu
    view_img=False,  # show results
    save_txt=False,  # save results to *.txt
    nosave=False,  # do not save images/videos
    augment=False,  # augmented inference
    visualize=False,  # visualize features
    update=False,  # update all models
    project=ROOT / "data",  # save results to project/name
    name="insect-detect-camera",  # save results to project/name
    exist_ok=False,  # existing project/name ok, do not increment
    half=False,  # use FP16 half-precision inference
    dnn=False,  # use OpenCV DNN for ONNX inference
    vid_stride=1,  # video frame-rate stride
    sort_top1=False,  # sort images to folders with predicted top1 class as folder name
    sort_prob=False,  # sort images first by probability and then by top1 class (requires --sort-top1)
    concat_csv=False,  # concatenate metadata .csv files and append classification results
    new_csv=False,  # create new .csv file with classification results
    save_img=False,
):
    source = f"{source}/{tracking_id}"  # add tracking ID to source path
    # Directories
    save_dir = Path(os.path.join(Path(project), "results"))
    save_dir.mkdir(parents=True, exist_ok=True)  # make dir

    # Load model
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt
    imgsz = check_img_size(imgsz, s=stride)  # check image size

    # Dataloader
    bs = 1  # batch_size
    dataset = LoadImages(source, img_size=imgsz, transforms=classify_transforms(imgsz[0]), vid_stride=vid_stride)

    # Create empty lists to save image filename and top1,top2,top3 class + probability
    lst_img = []
    lst_top1 = []
    lst_top2 = []
    lst_top3 = []
    lst_top1_prob = []
    lst_top2_prob = []
    lst_top3_prob = []

    # Set start time of inference
    start_inference = time.monotonic()

    # Run inference
    model.warmup(imgsz=(1 if pt else bs, 3, *imgsz))  # warmup
    seen, windows, dt = 0, [], (Profile(device=device), Profile(device=device), Profile(device=device))
    for path, im, im0s, vid_cap, s in dataset:
        with dt[0]:
            im = torch.Tensor(im).to(model.device)
            im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
            if len(im.shape) == 3:
                im = im[None]  # expand for batch dim

        # Inference
        with dt[1]:
            results = model(im)

        # Post-process
        with dt[2]:
            pred = F.softmax(results, dim=1)  # probabilities

        # Process predictions
        for i, prob in enumerate(pred):  # per image
            seen += 1
            p, im0, frame = path, im0s.copy(), getattr(dataset, "frame", 0)

            p = Path(p)  # to Path

            save_path = str(save_dir / p.name)  # im.jpg
            txt_path = str(save_dir / "labels" / p.stem) + ("" if dataset.mode == "image" else f"_{frame}")  # im.txt

            s += "%gx%g " % im.shape[2:]  # print string
            annotator = Annotator(im0, example=str(names), pil=True)

            # Print results
            top5i = prob.argsort(0, descending=True)[:5].tolist()  # top 5 indices
            s += f"{', '.join(f'{names[j]} {prob[j]:.2f}' for j in top5i)}, "

            # Write results
            # if not sort_top1:
            #     if save_img or view_img:
            #         text = f"{names[top5i[0]]}\n{prob[top5i[0]]:.2f}"
            #         annotator.text([2, 2], text, txt_color=(255, 255, 255))
            # if save_txt:  # Write to file
            #     text = "\n".join(f"{prob[j]:.2f} {names[j]}" for j in top5i)
            #     with open(f"{txt_path}.txt", "a") as f:
            #         f.write(text + "\n")

            # Write image filename and prediction results to lists
            # lst_img.append(f"{p.name}")
            # lst_top1.append(f"{names[top5i[0]]}")
            # lst_top2.append(f"{names[top5i[1]]}")
            # lst_top3.append(f"{names[top5i[2]]}")
            # lst_top1_prob.append(f"{prob[top5i[0]]:.2f}")
            # lst_top2_prob.append(f"{prob[top5i[1]]:.2f}")
            # lst_top3_prob.append(f"{prob[top5i[2]]:.2f}")

            # Print time (inference-only)
            LOGGER.info(f"{s}{dt[1].dt * 1E3:.1f}ms")

            return {
                "top1": names[top5i[0]],
                "top1_prob": round(float(prob[top5i[0]]), 2),
            }

            # Stream results
            # im0 = annotator.result()
            # if view_img:
            #     if platform.system() == "Linux" and p not in windows:
            #         windows.append(p)
            #         cv2.namedWindow(str(p), cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
            #         cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])
            #     cv2.imshow(str(p), im0)
            #     cv2.waitKey(1)  # 1 millisecond

            # Save results
            # if save_img:
            #     if dataset.mode == "image":
            #         if sort_top1 and not sort_prob:
            #             Path(f"{save_path}/top1_classes/{names[top5i[0]]}").mkdir(parents=True, exist_ok=True)
            #             cv2.imwrite(f"{save_path}/top1_classes/{names[top5i[0]]}/{p.name}", im0)
            #         elif sort_top1 and sort_prob:
            #             if prob[top5i[0]] >= 0.8:
            #                 Path(f"{save_path}/top1_classes/prob_0.8-1.0/{names[top5i[0]]}").mkdir(parents=True, exist_ok=True)
            #                 cv2.imwrite(f"{save_path}/top1_classes/prob_0.8-1.0/{names[top5i[0]]}/{p.name}", im0)
            #             elif 0.5 <= prob[top5i[0]] < 0.8:
            #                 Path(f"{save_path}/top1_classes/prob_0.5-0.8/{names[top5i[0]]}").mkdir(parents=True, exist_ok=True)
            #                 cv2.imwrite(f"{save_path}/top1_classes/prob_0.5-0.8/{names[top5i[0]]}/{p.name}", im0)
            #             else:
            #                 Path(f"{save_path}/top1_classes/prob_0.0-0.5/{names[top5i[0]]}").mkdir(parents=True, exist_ok=True)
            #                 cv2.imwrite(f"{save_path}/top1_classes/prob_0.0-0.5/{names[top5i[0]]}/{p.name}", im0)
            #         else:
            #             cv2.imwrite(save_path, im0)
            #     else:  # 'video' or 'stream'
            #         if vid_path[i] != save_path:  # new video
            #             vid_path[i] = save_path
            #             if isinstance(vid_writer[i], cv2.VideoWriter):
            #                 vid_writer[i].release()  # release previous video writer
            #             if vid_cap:  # video
            #                 fps = vid_cap.get(cv2.CAP_PROP_FPS)
            #                 w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            #                 h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            #             else:  # stream
            #                 fps, w, h = 30, im0.shape[1], im0.shape[0]
            #             save_path = str(Path(save_path).with_suffix(".mp4"))  # force *.mp4 suffix on results videos
            #             vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
            #         vid_writer[i].write(im0)
            


    # Print results
    t = tuple(x.t / seen * 1e3 for x in dt)  # speeds per image
    LOGGER.info(f"Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *imgsz)}" % t)
    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ""
        LOGGER.info(f"\nResults saved to {colorstr('bold', save_dir)}{s}")
    if update:
        strip_optimizer(weights[0])  # update model (to fix SourceChangeWarning)

    # Print estimated inference time per image
    inference_runtime = time.monotonic() - start_inference
    LOGGER.info(f"\nEstimated inference time per image: {round((inference_runtime / len(lst_img)) * 1000, 2)} ms")

    # Create folder to save results
    Path(f"{save_dir}/results").mkdir(parents=True, exist_ok=True)

    # Write prediction results to .csv
    df_results = pd.DataFrame(
        {"img_name": lst_img,
         "top1": lst_top1,
         "top1_prob": lst_top1_prob,
         "top2": lst_top2,
         "top2_prob": lst_top2_prob,
         "top3": lst_top3,
         "top3_prob": lst_top3_prob
        })
    df_results["top1_prob"] = pd.to_numeric(df_results["top1_prob"])
    df_results["top2_prob"] = pd.to_numeric(df_results["top2_prob"])
    df_results["top3_prob"] = pd.to_numeric(df_results["top3_prob"])
    df_results.to_csv(f"{save_dir}/results/pred_results.csv", index=False)

    # Write classification results to new .csv file and extract timestamp + tracking ID
    if new_csv:
        df_new = df_results
        df_new.insert(1, "timestamp", df_new["img_name"].str[:24])
        df_new.insert(2, "track_ID", df_new["img_name"].str[10:].str.extract("_(.*)_crop"))
        df_new.to_csv(f"{save_dir}/results/{name}_data_classified.csv", index=False)

    # Print script run time
    script_runtime = time.monotonic() - start_time
    LOGGER.info(f"\nScript run time: {round(script_runtime / 60, 3)} min\n")


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", nargs="+", type=str, default=ROOT / "yolov5s-cls.pt", help="model path(s)")
    parser.add_argument("--source", type=str, default=ROOT / "data/images", help="file/dir/URL/glob/screen/0(webcam)")
    parser.add_argument("--data", type=str, default=ROOT / "data/coco128.yaml", help="(optional) dataset.yaml path")
    parser.add_argument("--imgsz", "--img", "--img-size", nargs="+", type=int, default=[224], help="inference size h,w")
    parser.add_argument("--device", default="", help="cuda device, i.e. 0 or 0,1,2,3 or cpu")
    parser.add_argument("--view-img", action="store_true", help="show results")
    parser.add_argument("--save-txt", action="store_true", help="save results to *.txt")
    parser.add_argument("--nosave", action="store_true", help="do not save images/videos")
    parser.add_argument("--augment", action="store_true", help="augmented inference")
    parser.add_argument("--visualize", action="store_true", help="visualize features")
    parser.add_argument("--update", action="store_true", help="update all models")
    parser.add_argument("--project", default=ROOT / "runs/predict-cls", help="save results to project/name")
    parser.add_argument("--name", default="exp", help="save results to project/name")
    parser.add_argument("--exist-ok", action="store_true", help="existing project/name ok, do not increment")
    parser.add_argument("--half", action="store_true", help="use FP16 half-precision inference")
    parser.add_argument("--dnn", action="store_true", help="use OpenCV DNN for ONNX inference")
    parser.add_argument("--vid-stride", type=int, default=1, help="video frame-rate stride")
    parser.add_argument("--sort-top1", action="store_true", help="sort images to folders with predicted top1 class as folder name")
    parser.add_argument("--sort-prob", action="store_true", help="sort images first by probability and then by top1 class (requires --sort-top1)")
    parser.add_argument("--concat-csv", action="store_true", help="concatenate metadata .csv files and append classification results")
    parser.add_argument("--new-csv", action="store_true", help="create new .csv file with classification results")
    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1  # expand
    print_args(vars(opt))
    return opt


def main(opt):
    check_requirements(ROOT / "requirements.txt", exclude=("tensorboard", "thop"))
    run(**vars(opt))


if __name__ == "__main__":
    opt = parse_opt()
    main(opt)
