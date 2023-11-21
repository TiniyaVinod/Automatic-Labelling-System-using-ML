# Read configuration file and return parameters
import cv2
import json


def read_config(config_filename):
    f = open(config_filename)
    config = json.load(f)

    return config
