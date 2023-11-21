import numpy as np
import tkinter as tk
from tkinter import ttk
from app_gui_top import app_gui_top
from app_gui_down import app_gui_down

# --- GUI ---
class app_gui:
    def __init__(self, window_app, img1, img2, width, height, config):

        # Variables
        # self.winapp = window_app
        self.canvas_w = width
        self.canvas_h = height

        # Gui Components
        # ------------------------------------
        # |                |                 |
        # |             Gui upper part       |
        # |                |                 |
        # | left_display   | right_display   |
        # ------------------------------------
        # |                |                 |
        # |             Gui lower part       |
        # |                |                 |
        # | scroll_txt_left| tab_control     |
        # ------------------------------------

        # Create a canvas that can fit the video size
        self.gui_top = app_gui_top(window_app, img1, img2, width, height)

        self.gui_down = app_gui_down(window_app, width, height, config)
