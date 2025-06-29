import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'attendance.db')

# Thư mục
DATA_DIR = os.path.join(BASE_DIR, 'datas')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# Face Recognition
FACE_DETECTION_THRESHOLD = 0.5  # Giảm ngưỡng để tăng độ chính xác
RESIZE_SCALE = 0.25