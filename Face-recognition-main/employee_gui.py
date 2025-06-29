import os
import cv2
import numpy as np
import face_recognition
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import sqlite3
import time

class EmployeeGUI:
    def __init__(self, root, return_to_main_callback):
        self.root = root
        self.root.title("Employee Attendance System")
        self.return_to_main = return_to_main_callback

        # Cấu hình
        self.DATA_DIR = 'datas'
        self.DB_PATH = 'database/attendance.db'
        self.THRESHOLD = 0.5  # Giảm ngưỡng để tăng độ chính xác
        self.DETECTION_INTERVAL = 2000  # 2 giây kiểm tra 1 lần
        self.detected = False
        self.last_detection_time = None
        self.no_detection_threshold = 10  # 10 giây

        # Khởi tạo
        self.init_db()
        self.load_known_faces()
        self.setup_ui()
        self.start_camera()

    def init_db(self):
        """Kết nối database với cấu trúc mới"""
        self.conn = sqlite3.connect(self.DB_PATH)
        self.cursor = self.conn.cursor()

        # Kiểm tra xem bảng employees có tồn tại không
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
        if not self.cursor.fetchone():
            messagebox.showerror("Lỗi", "Database không hợp lệ! Thiếu bảng employees")
            self.return_to_main()
            return

    def load_known_faces(self):
        """Tải khuôn mặt từ database thay vì thư mục datas"""
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []

        try:
            # Lấy thông tin nhân viên từ bảng employees
            self.cursor.execute("SELECT id, name, image_path FROM employees")
            employees = self.cursor.fetchall()

            for emp_id, name, image_path in employees:
                if os.path.exists(image_path):
                    img = face_recognition.load_image_file(image_path)
                    encodings = face_recognition.face_encodings(img)
                    if encodings:
                        self.known_face_encodings.append(encodings[0])
                        self.known_face_names.append(name)
                        self.known_face_ids.append(emp_id)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải dữ liệu nhân viên: {str(e)}")
            self.return_to_main()

    def setup_ui(self):
        """Thiết lập giao diện"""
        # Frame camera
        self.camera_frame = tk.LabelFrame(self.root, text="Camera")
        self.camera_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.video_label = tk.Label(self.camera_frame)
        self.video_label.pack()

        # Nút điều khiển
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        self.btn_manual = tk.Button(
            control_frame,
            text="CHẤM CÔNG THỦ CÔNG",
            command=self.manual_attendance,
            bg="#4CAF50",
            fg="white",
            width=20
        )
        self.btn_manual.pack(side="left", padx=5)

        btn_exit = tk.Button(
            control_frame,
            text="THOÁT",
            command=self.return_to_main,
            bg="#F44336",
            fg="white",
            width=20
        )
        btn_exit.pack(side="left", padx=5)

    def start_camera(self):
        """Khởi động camera"""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Lỗi", "Không thể mở camera")
            self.return_to_main()
            return

        # Khởi tạo thời gian bắt đầu khi mở camera
        self.last_detection_time = time.time()
        self.check_face()

    def check_face(self):
        """Kiểm tra khuôn mặt định kỳ"""
        if self.detected:
            return

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            if face_encodings:
                # Có khuôn mặt trong khung hình
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encodings[0])
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encodings[0])

                if True in matches:
                    # Nhận diện thành công nhân viên
                    best_match_idx = np.argmin(face_distances)
                    if face_distances[best_match_idx] < self.THRESHOLD:
                        emp_id = self.known_face_ids[best_match_idx]
                        name = self.known_face_names[best_match_idx].upper()
                        self.process_attendance(emp_id, name)
                        return
                    else:
                        # Khuôn mặt không khớp với nhân viên nào
                        self.handle_no_employee_detected()
                else:
                    # Khuôn mặt không khớp với nhân viên nào
                    self.handle_no_employee_detected()
            else:
                # Không có khuôn mặt trong khung hình
                self.handle_no_face_detected()

            # Hiển thị frame
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

        self.root.after(self.DETECTION_INTERVAL, self.check_face)

    def handle_no_employee_detected(self):
        """Xử lý khi không nhận diện được nhân viên trong datas"""
        current_time = time.time()
        if not hasattr(self, 'last_no_employee_time'):
            self.last_no_employee_time = current_time

        # Kiểm tra nếu quá 10 giây không nhận diện được nhân viên
        if current_time - self.last_no_employee_time > self.no_detection_threshold:
            messagebox.showwarning("Cảnh báo", "Không nhận diện được nhân viên!")
            self.last_no_employee_time = current_time  # Reset thời gian

    def handle_no_face_detected(self):
        """Xử lý khi không có khuôn mặt trong khung hình"""
        # Không làm gì nếu chỉ muốn thông báo khi có khuôn mặt nhưng không nhận diện được
        pass

    def process_attendance(self, emp_id, name):
        """Xử lý chấm công và thoát"""
        self.mark_attendance(emp_id, name)
        messagebox.showinfo("Thành công", f"Đã chấm công cho {name}!")
        self.return_to_main()

    def manual_attendance(self):
        """Chấm công thủ công"""
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            if face_encodings:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encodings[0])
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encodings[0])

                if True in matches:
                    best_match_idx = np.argmin(face_distances)
                    if face_distances[best_match_idx] < self.THRESHOLD:
                        emp_id = self.known_face_ids[best_match_idx]
                        name = self.known_face_names[best_match_idx].upper()
                        self.process_attendance(emp_id, name)
                        return

            messagebox.showerror("Lỗi", "Không nhận diện được nhân viên!")

    def mark_attendance(self, emp_id, name):
        """Lưu dữ liệu chấm công theo cấu trúc mới"""
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%H:%M:%S')

        self.cursor.execute('''
            SELECT id, time_out FROM attendance 
            WHERE employee_id=? AND date=?
            ORDER BY time_in DESC LIMIT 1
        ''', (emp_id, today))
        record = self.cursor.fetchone()

        if record and not record[1]:  # Đã check-in nhưng chưa check-out
            self.cursor.execute('''
                UPDATE attendance SET time_out=?, status='OUT' WHERE id=?
            ''', (now, record[0]))
        else:  # Chưa check-in trong ngày
            self.cursor.execute('''
                INSERT INTO attendance (employee_id, date, time_in, status)
                VALUES (?, ?, ?, 'IN')
            ''', (emp_id, today, now))

        self.conn.commit()

    def return_to_main(self):
        """Trở về màn hình chính"""
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'conn'):
            self.conn.close()
        self.return_to_main()

    def __del__(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()