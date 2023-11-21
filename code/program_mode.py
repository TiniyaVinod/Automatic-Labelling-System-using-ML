# program mode
import cv2
from os import mkdir
from os.path import exists, join

# Real-time mode
def realtime_mode(cam_num):
    try:
        cam_no = int(cam_num)  # webcam : 0, other: 1
    except:
        msg = "Error : Camera Number must be Integer"
        return [0, msg]
    cap = cv2.VideoCapture(cam_no)
    msg = "STATUS : Camera active "

    return [cap, msg]


# Video mode
def video_mode(video_path):
    if not exists(video_path):
        msg = "path [ " + video_path + " ] does not exist!"
        return [0, msg]
    else:
        cap = cv2.VideoCapture(video_path)

    msg = "STATUS : Video File Feed"
    return [cap, msg]


# Record mode
def record_mode(cap, export_folder, export_filename):
    export_path = join(export_folder, export_filename)

    # if there is no directory, create one
    if not exists(export_folder):
        mkdir(export_folder)

    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    write_fps = 15

    video_writer = cv2.VideoWriter(
        export_path, fourcc, write_fps, (int(w), int(h)), True
    )

    return video_writer
