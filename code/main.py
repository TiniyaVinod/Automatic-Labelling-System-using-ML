import tkinter as tk
from datetime import datetime
from os.path import exists, join, splitext

import cv2
import numpy as np
from PIL import Image, ImageTk
from timeit import default_timer as timer

from app_gui import app_gui
from model_class import model_class
from common_functions import read_config
from program_mode import *
import json, os, time
from datetime import datetime

from multiprocessing import Value, Array, Event
import multiprocessing
import socket
from contextlib import contextmanager
import subprocess
import psutil
import numpy, random
import struct
import ctypes
from get_data_from_sensor import acquire_data_from_rp

# --- main ---

global cap, run_camera, global_frame, roi_points, roi_img, isconnect_cam
roi_flag = False
run_camera = False
window_app_run = False
isconnect_cam = False
status_text = ""
roi_points = []
config_filename = "config.json"
output_score = []

update_loop_count = 0

chair_count = 0
non_chair_count = 0
person_count = 0
non_person_count = 0


# global variables
parallel_func_loop_count = 0
loop_count = 0
buffer_size = 65536
process_id = 0

if not exists(config_filename):
    print("Cannot find configuration file")

config = read_config(config_filename)

model_filename = config["model_classification"]["model_filename"]
device = config["model_classification"]["computing_device"]

# create window application
window_app = tk.Tk()
config_gui = config["gui_prop"]
window_app.title(config_gui["window_title"])
window_app.geometry = config_gui["window_geometry"]
window_app.resizable(width=False, height=False)

canvas_w = config_gui["canvas_width"]
canvas_h = config_gui["canvas_height"]

# first frame with clear white image and init filter_image
white_img = np.zeros([canvas_w, canvas_h, 3], dtype=np.uint8)
roi_img = white_img.copy()
white_img.fill(255)
roi_img.fill(0)

default_img = Image.fromarray(white_img)
default_img = ImageTk.PhotoImage(default_img)

default_img2 = Image.fromarray(white_img)
default_img2 = ImageTk.PhotoImage(default_img2)
global_frame = white_img

model = model_class(config["model_classification"])


# region matplotlib for reusing figure

# initializing matplotlib and using the same figure again
import matplotlib.pyplot as plt

fig, ax = plt.subplots(1, 1)
ax.set_xlabel("X")
ax.set_ylabel("Y")

ax.set(yticklabels=[])
ax.set(xticklabels=[])

fig.set_size_inches(3.2, 3.2)

initial_array = [0 for i in range(buffer_size)]

ax.plot(initial_array)

# endregion matlab

# region clean1

if not window_app_run:
    window_app_run = True
    gui = app_gui(window_app, default_img, default_img2, canvas_w, canvas_h, config)


# Button Functions ----------------------------------------------------------
def connect_cam():
    global cap, video_writer, isconnect_cam, update_loop_count, parallel_func_loop_count, output_score
    if isconnect_cam:
        return 0

    # Check current selected tab
    select_mode = gui.gui_down.get_select_mode()
    record_status = gui.gui_down.get_record_status()

    cam_num = gui.gui_down.get_camera_number()
    video_path = gui.gui_down.get_video_path()

    # Check mode
    cam_mode = (select_mode == 0) & (record_status == 0)
    vid_mode = select_mode == 1

    # Behave according to mode
    if cam_mode:  # CAMERA
        [cap, msg] = realtime_mode(cam_num)

    elif vid_mode:  # VIDEO
        [cap, msg] = video_mode(video_path)

    else:  # Auto Mode ( Not implemented )
        return 0

    display_status(msg)
    if cap == 0:
        stop()
        return 0

    isconnect_cam = True
    print("------connect cam clicked-----------")

    button_play["state"] = "normal"
    button_stop["state"] = "disabled"
    button_connectcam["state"] = "disabled"
    button_disconnectcam["state"] = "normal"

    # start a parallel process
    shared_value.value = 1
    event_p1_for_sync.clear()
    event_p2_for_sync.clear()
    update_loop_count = 0
    output_score = []


def disconnect_cam():
    global isconnect_cam

    shared_value.value = 0
    if isconnect_cam:
        cap.release()
        isconnect_cam = False
    else:
        return 0

    display_status("STATUS: Camera inactive")

    isconnect_cam = False

    button_play["state"] = "disabled"
    button_stop["state"] = "disabled"
    button_connectcam["state"] = "normal"
    button_disconnectcam["state"] = "disabled"

    # remove the child process
    # Terminate the process when parent is done
    try:
        child_process = psutil.Process(shared_child_pid.value)
        print("inside disconnect ")
        print("child pid", shared_child_pid.value)
        print(child_process)
        child_process.terminate()
        print("Terminated child : ", shared_child_pid.value)
    except Exception as e:
        print("Exception occured : ", e)


# endregion clean1


def play():
    """
    start_timer stream (run_camera and update_image)
    and change state of buttons_left
    """
    print("--------play clicked -------------")
    global cap, run_camera, record_result, video_writer, shared_value, event_is_updated

    record_result = []
    rec_mode = gui.gui_down.get_record_status()

    # Set Event

    event_waiting_for_prediciton_result.clear()

    # Check if it is record mode
    if rec_mode:
        # Path to write record
        export_folder = config["export"]["export_record_folder"]
        export_filename = gui.gui_down.get_record_export_path()

        video_writer = record_mode(cap, export_folder, export_filename)

    if not run_camera:
        run_camera = True

        button_play["state"] = "disabled"
        button_stop["state"] = "normal"
        button_connectcam["state"] = "disabled"
        button_disconnectcam["state"] = "disabled"

        gui.gui_down.disable_setting()

        event_p1_for_sync.set()
        event_p2_for_sync.set()
        print("hered...........")
        update_frame()

    # Clear Text
    if isconnect_cam == True:
        gui.gui_down.scroll_txt_left.config(state=tk.NORMAL)
        gui.gui_down.scroll_txt_left.delete("1.0", tk.END)


def stop():
    """
    stop stream (run_camera)
    and change state of buttons_left
    """
    global run_camera, video_writer, shared_value, global_socket_obj

    shared_value.value = 0

    event_p1_for_sync.clear()
    event_p2_for_sync.clear()

    if isconnect_cam == False:
        return 0

    if run_camera:
        run_camera = False
        shared_value.value = 0

    # if record mode is activated, release the object
    if gui.gui_down.get_record_status() == 1:
        video_writer.release()
        export_result()
    else:
        gui.gui_down.btn_record["state"] = "normal"

    button_play["state"] = "normal"
    button_stop["state"] = "disabled"
    button_connectcam["state"] = "disabled"
    button_disconnectcam["state"] = "normal"

    gui.gui_down.enable_setting()

    display_status("STATUS : STOP Frame")


# Region of Interest functions--------------------------------------------------


def apply_ROI():
    global roi_flag, roi_points

    if roi_points:
        roi_flag = True
    else:
        display_status("STATUS : ROI points are not specified")
        roi_flag = False


def remove_ROI():
    global roi_flag
    roi_flag = False


def default_roi(config):
    """
    Set roi points to default
    """

    global roi_points, roi_img

    roi_points = config["preprocess"]["roi_points"]

    # Connect dots and create polygon
    pts = np.array(roi_points, np.int32)
    roi_img = cv2.fillPoly(roi_img, [pts], (255, 255, 255))


def draw_polygon_roi(frame):
    global roi_points

    # draw polygon if with the specified points
    if roi_points:  # not empty
        pts = np.array(roi_points, np.int32)
        frame_roi = cv2.polylines(
            frame, [pts], isClosed=True, color=(255, 0, 0), thickness=1
        )

        return frame_roi
    else:  # empty
        return frame


def preprocess_frame(frame):
    # Resize frame
    dim = (gui.canvas_w, gui.canvas_h)
    frame_resize = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)

    # Correct the color
    frame_corr_color = cv2.cvtColor(frame_resize, cv2.COLOR_BGR2RGB)

    # Mirror horizontally
    frame_flip = np.fliplr(frame_corr_color)

    return frame_flip


def update_frame():
    global global_frame, roi_img, roi_flag, record_result
    global shared_time, shared_value, shared_array, shared_prediction
    global event_p1_for_sync, event_p2_for_sync
    global person_count, non_person_count, update_loop_count, output_score

    # reading timestamp
    timestamp = (
        datetime.today() - datetime.today().replace(hour=0, minute=0, second=0)
    ).seconds
    shared_time.value = timestamp

    start_timer = timer()

    # Read frame capture object
    ret, frame = cap.read()
    curr_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
    datetime_format = "%m/%d/%Y, %H:%M:%S"  # .f

    # If can't read frame
    if (ret is None) | (ret == False):
        display_status("STATUS : Cannot capture frame from source")
        stop()
        return 0

    frame_flip = preprocess_frame(frame)

    global_frame = frame_flip.copy()

    # Record Mode
    if gui.gui_down.get_record_status() == 1:
        video_writer.write(frame)

    # Apply ROI filter
    if roi_flag == True:
        frame_show = frame_flip.copy()
        frame_show = draw_polygon_roi(frame_show)
        frame_flip[roi_img == 0] = 0

    else:
        frame_show = frame_flip

    # region plot graph in gui

    from PIL import Image
    import matplotlib
    import matplotlib.pyplot as plt
    import io

    global ax, fig

    # matplotlib.use("agg")
    # plt.figure(figsize=(3.3, 3.3))
    # plt.plot(shared_array[:])
    # img_buf = io.BytesIO()
    # plt.savefig(img_buf, format="png")
    # im = Image.open(img_buf)
    ax.clear()
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    ax.set(yticklabels=[])
    ax.set(xticklabels=[])

    ax.plot(shared_array[:])

    buf = io.BytesIO()
    # fig.clf()
    fig.savefig(buf)
    # buf.seek(0)

    im = Image.open(buf)

    # img = Image.fromarray(frame_show)

    # print(type(img))

    gui.gui_top.canvas_l_img.paste(im)

    # endregion

    select_mode = gui.gui_down.select_mode

    # region model prediction and object classification

    # Classification
    # Set parameter
    # model.model.conf = gui.gui_down.get_conf_thresh()
    predicted_result_from_model = model.predict_result(frame_flip)
    predictions = predicted_result_from_model[0]
    output_result_text = predicted_result_from_model[1]
    predictions_all_class = predicted_result_from_model[2]
    #print("Check predictions test ")
    #print(predictions, type(predictions))

    categories = predictions[:, 5]

    sec = cap.get(cv2.CAP_PROP_POS_MSEC)
    second = "{:.2f}".format(sec * 0.001)

    img_with_keypoints = frame_flip.copy()
    for obj in predictions_all_class:
        x1 = int(obj["x1"])
        y1 = int(obj["y1"])
        x2 = int(obj["x2"])
        y2 = int(obj["y2"])
        label = obj["label"]
        confidence = obj["confidence"]
        text = f"{label.upper()} : {confidence} %"

        color_val = min(255, obj["label_int"] * 3)
        box_color = (255, color_val, color_val)

        cv2.rectangle(img_with_keypoints, (x1, y1), (x2, y2), box_color, (1))
        cv2.putText(
            img_with_keypoints,
            text,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            box_color,
            1,
        )
    img2 = Image.fromarray(img_with_keypoints)

    img_array = np.array(img2)

    font = cv2.FONT_HERSHEY_SIMPLEX

    # increase_other_count = False
    # increase total_count
    current_time = time.strftime("%Y %m %d")
    update_loop_count += 1
    print(f"inside update loop : {update_loop_count} : {shared_time.value}",event_p1_for_sync.is_set(),event_p2_for_sync.clear())
    image_name = f"{current_time}_{update_loop_count}_{timestamp}_"
    output_result = " ".join(output_result_text[:3])
    print(output_result, " JOINED RESULT")
    if ("PERSON" in output_result):
            output_label = "person"
            person_count += 1
            image_name += f"person_{person_count}"
    else:
         output_label = "noperson"
         non_person_count += 1
         image_name += f"noperson_{non_person_count}"
         

    predictions = {
        "total_count": update_loop_count,
        "timestamp": timestamp,
        "prediction": output_label,
        "creationdate": current_time,
    }

    output_score.insert(0, predictions)

    with open(
        "experiments/json_files/prediction_result.json", "w", encoding="utf-8"
    ) as f:
        json.dump(output_score, f, ensure_ascii=False, indent=4)

    img2 = Image.fromarray(img_array)

    if "noperson" in image_name:
        img2.save(f"experiments/images/frames_noperson/{image_name}.jpg")
    else:
        img2.save(f"experiments/images/frames_person/{image_name}.jpg")

    text = f"Timestamp: {shared_time.value}, Prediction: {output_label}, Creation Date: {current_time}"

    # endregion image prediction and save

    # Save record result
    if gui.gui_down.get_record_status() == 1:
        record_result.append(text)

    gui.gui_down.display_scrolltext(text)
    gui.gui_top.canvas_r_img.paste(img2)

    # Compute FPS
    sec_fps = timer() - start_timer
    fps = 1 / sec_fps
    str_fps = "{:.2f}".format(fps)

    msg = "FPS : " + str_fps
    display_status(msg)

    # saving the prediction in shared memory
    shared_prediction.value = output_label[0]
    event_waiting_for_prediciton_result.set()

    # for syncing and calling the function recursively
    event_p1_for_sync.set()
    if event_p2_for_sync.wait(15):
        event_p2_for_sync.clear()
        if run_camera:
            window_app.after(10, update_frame)


def form_predict_text(select_mode, second, datetime_format, pred_result):
    if select_mode == 1:
        text = "Second : " + str(second) + " : " + pred_result
    else:
        dateTimeObj = datetime.now()
        text = dateTimeObj.strftime(datetime_format) + " : " + pred_result
    return text


def create_roi():
    global roi_points

    roi_points = []

    # Get Points from callback functions
    cv2.imshow("ROI", global_frame)
    cv2.setMouseCallback("ROI", click_event_ROI)


def click_event_ROI(event, x, y, flags, params):
    global roi_img

    roi_img = np.zeros([canvas_w, canvas_h, 3], dtype=np.uint8)

    # checking for left mouse clicks
    if event == cv2.EVENT_LBUTTONDOWN:
        # displaying the coordinates
        # on the image window
        font = cv2.FONT_HERSHEY_SIMPLEX

        cv2.putText(
            global_frame, str(x) + "," + str(y), (x, y), font, 1, (255, 0, 0), 2
        )
        roi_points.append([x, y])
        cv2.imshow("ROI", global_frame)
        cv2.waitKey(0)
        cv2.destroyWindow("ROI")

        # Connect dots and create polygon
        pts = np.array(roi_points, np.int32)
        roi_img = cv2.fillPoly(roi_img, [pts], (255, 255, 255))


def display_status(msg):
    status_text.config(text=msg)


def export_result():
    export_filename = splitext(gui.gui_down.get_record_export_path())[0]

    export_folder = config["export"]["export_record_folder"]
    export_filename = join(export_folder, export_filename + ".txt")

    with open(export_filename, "w") as f:
        for line in record_result:
            f.write(line)
            f.write("\n")


# ---- buttons_left ----
buttons_left = tk.Frame(window_app)
buttons_left.grid(row=2, column=0)

button_play = tk.Button(buttons_left, text="Play", command=play, state="disabled")
button_play.pack(side="left")

button_stop = tk.Button(buttons_left, text="Stop", command=stop, state="disabled")
button_stop.pack(side="left")

button_connectcam = tk.Button(
    buttons_left, text="Connect Camera/Video", command=connect_cam
)
button_connectcam.pack(side="left")

button_disconnectcam = tk.Button(
    buttons_left,
    text="Disconnect Camera/Video",
    command=disconnect_cam,
    state="disabled",
)
button_disconnectcam.pack(side="left")

# ---- buttons_right ----
buttons_right = tk.Frame(window_app)
buttons_right.grid(row=2, column=1)

button_apply_ROI = tk.Button(buttons_right, text="Apply ROI", command=apply_ROI)
button_apply_ROI.pack(side="left")

button_default_ROI = tk.Button(buttons_right, text="Remove ROI", command=remove_ROI)
button_default_ROI.pack(side="left")

button_create_ROI = tk.Button(buttons_right, text="Create ROI", command=create_roi)
button_create_ROI.pack(side="left")

button_default_ROI = tk.Button(
    buttons_right, text="default ROI", command=default_roi(config)
)
button_default_ROI.pack(side="left")


# ---- /end buttons_left ----

# Status Bar
status_text = tk.Label(window_app)
status_text.grid(row=3, column=0)


if __name__ == "__main__":
    try:
        multiprocessing.set_start_method("spawn", force=True)
        print("spawned")
    except RuntimeError:
        print("Runtime Error!")
        pass

    context = multiprocessing.get_context("spawn")
    event_is_updated = context.Event()
    event_is_not_stopped = context.Event()
    event_is_run_loop = context.Event()
    event_p1_for_sync = context.Event()
    event_p2_for_sync = context.Event()
    event_waiting_for_prediciton_result = context.Event()

    shared_value = context.Value("i", 1)
    shared_time = context.Value("i", 0)
    shared_array = context.Array("i", size_or_initializer=16384)
    shared_prediction = context.Value("u", "o")
    shared_loop_count = context.Value("i", 0)
    shared_child_pid = context.Value("i", 0)

    process1 = multiprocessing.Process(
        target=acquire_data_from_rp,
        args=(
            parallel_func_loop_count,
            buffer_size,
            shared_time,
            shared_prediction,
            shared_array,
            shared_child_pid,
            event_p1_for_sync,
            event_p2_for_sync,
            event_waiting_for_prediciton_result,
        ),
    )
    process1.start()
    window_app.mainloop()
    process1.join()
