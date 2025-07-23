import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2

class EmployeeView:
    def __init__(self, root):
        self.root = root
        self.root.title("Hệ thống chấm công nhân viên")
        self.setup_ui()

    def setup_ui(self):
        self.camera_frame = tk.LabelFrame(self.root, text="Camera")
        self.camera_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.video_label = tk.Label(self.camera_frame)
        self.video_label.pack()

        self.message_frame = tk.Frame(self.root)
        self.message_frame.pack(pady=5, fill="x")

        self.message_label = tk.Label(
            self.message_frame,
            text="",
            font=('Arial', 12, 'bold'),
            height=2
        )
        self.message_label.pack()

        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        self.btn_manual = tk.Button(
            control_frame,
            text="CHẤM CÔNG THỦ CÔNG",
            bg="#4CAF50",
            fg="white",
            width=20
        )
        self.btn_manual.pack(side="left", padx=5)

        self.btn_exit = tk.Button(
            control_frame,
            text="THOÁT",
            bg="#F44336",
            fg="white",
            width=20
        )
        self.btn_exit.pack(side="left", padx=5)

    def display_video_frame(self, frame):
        if frame is not None:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

    def display_message(self, message, color="blue"):
        colors = {
            "blue": "#0000FF",
            "green": "#00AA00",
            "red": "#FF0000",
            "orange": "#FFA500"
        }
        self.message_label.config(text=message, fg=colors.get(color, "#000000"))
        self.root.update()