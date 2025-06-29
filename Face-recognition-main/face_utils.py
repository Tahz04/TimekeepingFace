import os
import cv2
import face_recognition
import numpy as np
from config import RESIZE_SCALE, DATA_DIR, FACE_DETECTION_THRESHOLD
import time

class FaceRecognizer:
    def __init__(self):
        self.known_encodings = []
        self.known_names = []
        self.last_detection_time = None
        self.no_detection_threshold = 10  # 10 giây

    def load_known_faces(self):
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp']

        for img_name in os.listdir(DATA_DIR):
            if img_name.startswith('.') or not os.path.splitext(img_name)[1].lower() in valid_extensions:
                continue

            img_path = os.path.join(DATA_DIR, img_name)
            try:
                img = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(img)
                if encodings:
                    self.known_encodings.append(encodings[0])
                    self.known_names.append(os.path.splitext(img_name)[0])
            except Exception as e:
                print(f"Không thể xử lý ảnh {img_name}: {str(e)}")
                continue

    def process_frame(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_SCALE, fy=RESIZE_SCALE)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        return face_locations, face_encodings

    def recognize_face(self, face_encoding):
        if not self.known_encodings:
            return None

        try:
            matches = face_recognition.compare_faces(self.known_encodings, face_encoding)
            face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)

            if len(face_distances) == 0:
                return None

            best_match_idx = np.argmin(face_distances)
            # Kiểm tra ngưỡng độ chính xác
            if face_distances[best_match_idx] < FACE_DETECTION_THRESHOLD:
                return self.known_names[best_match_idx].upper()
            return None
        except Exception as e:
            print(f"Lỗi nhận diện: {str(e)}")
            return None

    def check_no_detection(self):
        """Kiểm tra nếu không nhận diện được khuôn mặt trong 10 giây"""
        if self.last_detection_time is None:
            self.last_detection_time = time.time()
            return False

        current_time = time.time()
        if current_time - self.last_detection_time > self.no_detection_threshold:
            self.last_detection_time = None  # Reset thời gian
            return True
        return False