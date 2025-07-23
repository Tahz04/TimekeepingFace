from datetime import datetime

import cv2
import dlib
import face_recognition
import numpy as np
from config import *
import time

class FaceRecognizer:
    def __init__(self):
        self.known_encodings = []
        self.known_names = []
        self.last_detection_time = None
        self.face_hold_start_time = None
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        self.detector = dlib.get_frontal_face_detector()

    def load_known_faces(self, custom_data_dir=None):
        data_dir = custom_data_dir or DATA_DIR
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp']

        for img_name in os.listdir(data_dir):
            if img_name.startswith('.') or not os.path.splitext(img_name)[1].lower() in valid_extensions:
                continue

            img_path = os.path.join(data_dir, img_name)
            try:
                img = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(img, num_jitters=NUM_JITTERS, model=MODEL)
                if encodings:
                    self.known_encodings.append(encodings[0])
                    self.known_names.append(os.path.splitext(img_name)[0])
            except Exception as e:
                print(f"Không thể xử lý ảnh {img_name}: {str(e)}")
                continue

    def preprocess_frame(self, frame):
        if frame is None:
            return None

        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge((l, a, b))
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(enhanced, -1, kernel)

    def process_frame(self, frame):
        if frame is None:
            return None, None

        try:
            processed = self.preprocess_frame(frame)
            small_frame = cv2.resize(processed, (0, 0), fx=RESIZE_SCALE, fy=RESIZE_SCALE)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(
                rgb_small_frame,
                model=FACE_DETECTION_METHOD,
                number_of_times_to_upsample=FACE_DETECTION_UPSAMPLES
            )

            face_encodings = face_recognition.face_encodings(
                rgb_small_frame,
                face_locations,
                num_jitters=NUM_JITTERS,
                model=MODEL
            )

            return face_locations, face_encodings
        except Exception as e:
            print(f"Lỗi xử lý frame: {str(e)}")
            return None, None

    def recognize_face(self, face_encoding):
        if not self.known_encodings or face_encoding is None:
            return None

        try:
            face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)
            best_match_idx = np.argmin(face_distances)

            if face_distances[best_match_idx] < FACE_DETECTION_THRESHOLD:
                if len(face_distances) > 1:
                    face_distances_sorted = np.sort(face_distances)
                    if (face_distances_sorted[1] - face_distances_sorted[0]) > 0.1:
                        return self.known_names[best_match_idx]
                else:
                    return self.known_names[best_match_idx]
            return None
        except Exception as e:
            print(f"Lỗi nhận diện: {str(e)}")
            return None

    def check_face_quality(self, frame, face_location):
        if frame is None or not face_location:
            return False

        try:
            top, right, bottom, left = face_location
            if (bottom - top) < MIN_FACE_SIZE or (right - left) < MIN_FACE_SIZE:
                return False

            face_region = frame[top:bottom, left:right]
            gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            if gray_face.std() < MIN_FACE_CONTRAST:
                return False

            return True
        except Exception as e:
            print(f"Lỗi kiểm tra chất lượng: {str(e)}")
            return False

    def get_facial_landmarks(self, frame, face_location):
        """Lấy facial landmarks sử dụng dlib"""
        top, right, bottom, left = face_location
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rect = dlib.rectangle(left, top, right, bottom)
        shape = self.predictor(gray, rect)
        return np.array([[p.x, p.y] for p in shape.parts()])

    def verify_liveness(self, frame, face_location, action):
        """Xác thực người thật bằng hành động"""
        landmarks = self.get_facial_landmarks(frame, face_location)

        if "quay đầu" in action:
            # Tính toán hướng khuôn mặt dựa trên landmarks
            return self.check_head_pose(landmarks, action)
        elif "nháy mắt" in action:
            return self.check_eye_blink(landmarks)
        elif "mỉm cười" in action:
            return self.check_smile(landmarks)
        elif "gật đầu" in action:
            return self.check_nod(landmarks)
        return False

    def check_head_pose(self, landmarks, action):
        """Kiểm tra hướng quay đầu"""
        nose_bridge = landmarks[27:31]
        left_eye = landmarks[36:42]
        right_eye = landmarks[42:48]

        left_eye_center = np.mean(left_eye, axis=0)
        right_eye_center = np.mean(right_eye, axis=0)

        eye_center = (left_eye_center + right_eye_center) / 2
        nose_tip = landmarks[30]

        if "trái" in action:
            return nose_tip[0] < eye_center[0] - 10
        elif "phải" in action:
            return nose_tip[0] > eye_center[0] + 10
        return False

    def check_eye_blink(self, landmarks):
        """Kiểm tra nháy mắt"""
        left_eye = landmarks[36:42]
        right_eye = landmarks[42:48]

        def eye_aspect_ratio(eye):
            # Tính tỉ lệ nháy mắt
            A = np.linalg.norm(eye[1] - eye[5])
            B = np.linalg.norm(eye[2] - eye[4])
            C = np.linalg.norm(eye[0] - eye[3])
            return (A + B) / (2.0 * C)

        ear_left = eye_aspect_ratio(left_eye)
        ear_right = eye_aspect_ratio(right_eye)
        return (ear_left < 0.2) or (ear_right < 0.2)

    def check_smile(self, landmarks):
        """Kiểm tra nụ cười"""
        mouth = landmarks[48:68]
        mouth_width = np.linalg.norm(mouth[6] - mouth[0])
        mouth_height = np.linalg.norm(mouth[2] - mouth[10])
        return mouth_height > mouth_width * 0.4

    def check_nod(self, landmarks):
        """Kiểm tra gật đầu"""
        # Đơn giản kiểm tra sự thay đổi vị trí landmarks theo thời gian
        if not hasattr(self, 'prev_nose_tip'):
            self.prev_nose_tip = landmarks[30]
            return False

        movement = np.linalg.norm(landmarks[30] - self.prev_nose_tip)
        self.prev_nose_tip = landmarks[30]
        return movement > 5

    def process_frame_with_verification(self, frame):
        """Xử lý frame với xác minh đầy đủ"""
        try:
            if frame is None:
                return None

            # Xử lý frame với HOG
            face_locations, face_encodings = self.process_frame(frame)
            if not face_locations:
                self.face_hold_start_time = None
                return None

            # Lấy khuôn mặt chính
            main_face_location = face_locations[0]

            # Kiểm tra chất lượng
            if not self.check_face_quality(frame, main_face_location):
                self.face_hold_start_time = None
                return None

            # Xử lý thời gian giữ mặt
            current_time = time.time()
            if self.face_hold_start_time is None:
                self.face_hold_start_time = current_time
                return None

            if current_time - self.face_hold_start_time < HOLD_FACE_TIME:
                return None

            return (main_face_location, face_encodings[0], True)

        except Exception as e:
            print(f"Lỗi xử lý xác minh: {str(e)}")
            self.face_hold_start_time = None
            return None

    def log_detection(self, frame, face_location, name, success):
        """Ghi log nhận diện theo ngày"""
        try:
            date_dir = datetime.now().strftime("%d-%m-%Y")
            log_dir = os.path.join(LOG_DIR, date_dir)
            os.makedirs(log_dir, exist_ok=True)

            status = "in" if success else "unknown"
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{name}_{status}_{timestamp}.jpg"
            log_path = os.path.join(log_dir, filename)

            if face_location and frame is not None:
                top, right, bottom, left = face_location
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                cv2.putText(frame, datetime.now().strftime("%H:%M:%S"),
                            (left, bottom + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imwrite(log_path, frame)
            return True
        except Exception as e:
            print(f"Lỗi ghi log: {str(e)}")
            return False
