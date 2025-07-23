import cv2
import time
import random
from tkinter import messagebox
from face_utils import FaceRecognizer
from config import *
from models.employee_model import EmployeeModel
from views.employee_view import EmployeeView

class EmployeeController:
    def __init__(self, root, return_to_main_callback):
        self.view = EmployeeView(root)
        self.model = EmployeeModel()
        self.face_recognizer = self.model.face_recognizer
        self.return_to_main = return_to_main_callback
        self.current_action = None
        self.action_start_time = None
        self.setup_events()
        self.start_camera()

    def setup_events(self):
        self.view.btn_manual.config(command=self.manual_attendance)
        self.view.btn_exit.config(command=self.return_to_main)

    def process_camera_frame(self, frame):
        try:
            if frame is None:
                return None, None

            frame = cv2.flip(frame, 1)

            if self.current_action:
                return self.handle_action_verification(frame)

            result = self.face_recognizer.process_frame_with_verification(frame)
            if result is None:
                if hasattr(self.face_recognizer, 'face_hold_start_time') and self.face_recognizer.face_hold_start_time:
                    current_time = time.time()
                    hold_time = current_time - self.face_recognizer.face_hold_start_time
                    remaining = max(0, HOLD_FACE_TIME - hold_time)
                    self.view.display_message(f"Giữ mặt thêm {remaining:.1f} giây...", "blue")
                return frame, None

            face_location, face_encoding, verified = result
            if verified and face_encoding is not None:
                emp_id, name = self.model.recognize_employee(face_encoding)
                if emp_id and name:
                    self.start_action_verification(name, face_location)
                    return frame, None

            return frame, None
        except Exception as e:
            print(f"Lỗi xử lý frame: {str(e)}")
            return frame, None

    def start_action_verification(self, name, face_location):
        self.current_action = random.choice(RANDOM_ACTIONS)
        self.action_start_time = time.time()
        self.current_face_location = face_location
        self.expected_name = name
        self.view.display_message(f"{name}, {self.current_action}", "orange")

    def handle_action_verification(self, frame):
        if time.time() - self.action_start_time > ACTION_TIMEOUT:
            self.reset_verification()
            self.view.display_message("Hết thời gian xác thực!", "red")
            return frame, None

        if self.face_recognizer.verify_liveness(frame, self.current_face_location, self.current_action):
            name = self.expected_name
            emp_id, _ = self.model.recognize_employee_by_name(name)
            self.face_recognizer.log_detection(frame, self.current_face_location, name, True)
            self.reset_verification()
            return frame, (emp_id, name)

        self.view.display_message(f"{self.expected_name}, {self.current_action}", "orange")
        return frame, None

    def reset_verification(self):
        self.current_action = None
        self.action_start_time = None
        self.current_face_location = None
        self.expected_name = None

    def check_face(self):
        try:
            ret, frame = self.cap.read()
            if not ret:
                self.view.root.after(DETECTION_INTERVAL, self.check_face)
                return

            processed_frame, result = self.process_camera_frame(frame)
            self.view.display_video_frame(processed_frame)

            if result:
                emp_id, name = result
                self.process_attendance(emp_id, name)
                return

            self.view.root.after(DETECTION_INTERVAL, self.check_face)
        except Exception as e:
            print(f"Lỗi kiểm tra khuôn mặt: {str(e)}")
            self.view.root.after(DETECTION_INTERVAL, self.check_face)

    def manual_attendance(self):
        try:
            ret, frame = self.cap.read()
            if not ret:
                messagebox.showerror("Lỗi", "Không đọc được frame từ camera!")
                return

            processed_frame, result = self.process_camera_frame(frame)
            self.view.display_video_frame(processed_frame)

            if result:
                emp_id, name = result
                self.process_attendance(emp_id, name)
            else:
                messagebox.showerror("Lỗi", "Nhận diện thất bại! Vui lòng thử lại.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Có lỗi xảy ra: {str(e)}")

    def start_camera(self):
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise RuntimeError("Không thể mở camera")

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            self.check_face()
        except Exception as e:
            messagebox.showerror("Lỗi Camera", f"Không thể khởi động camera: {str(e)}")
            self.return_to_main()

    def process_attendance(self, emp_id, name):
        if self.model.mark_attendance(emp_id, name):
            self.view.display_message(f"Đã chấm công thành công cho {name}!", "green")
            time.sleep(2)
        else:
            self.view.display_message("Lỗi khi chấm công!", "red")
            time.sleep(2)

        self.return_to_main()

    def return_to_main(self):
        try:
            if hasattr(self, 'cap') and self.cap.isOpened():
                self.cap.release()
            self.model.close()
            self.return_to_main()
        except Exception as e:
            print(f"Lỗi dọn dẹp: {str(e)}")
            self.return_to_main()

    def __del__(self):
        try:
            if hasattr(self, 'cap') and self.cap.isOpened():
                self.cap.release()
        except Exception as e:
            print(f"Lỗi hủy: {str(e)}")
