# app_gui_top
import tkinter as tk


class app_gui_top:

    # GUI upper part -------------------------------
    def __init__(self, window_app, img1, img2, canvas_w, canvas_h):

        self.canvas_l_img = img1
        self.canvas_r_img = img2

        # left display -------------------------------
        self.left_display = tk.Canvas(window_app, width=canvas_w, height=canvas_h)
        self.left_display.grid(row=0, column=0)
        self.left_display.create_image((0, 0), image=self.canvas_l_img, anchor="nw")

        # right display -------------------------------
        self.right_display = tk.Canvas(window_app, width=canvas_w, height=canvas_h)
        self.right_display.grid(row=0, column=1)
        self.right_display.create_image(
            (canvas_w, 0), image=self.canvas_r_img, anchor="ne"
        )
