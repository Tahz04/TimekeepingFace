import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'attendance.db')

# Thư mục
DATA_DIR = os.path.join(BASE_DIR, 'datas')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# Face Recognition
FACE_DETECTION_METHOD = 'hog'
FACE_DETECTION_THRESHOLD = 0.45
RESIZE_SCALE = 0.5
NUM_JITTERS = 3
MODEL = 'large'
FACE_DETECTION_UPSAMPLES = 1

# Camera
DETECTION_INTERVAL = 1000
NO_DETECTION_THRESHOLD = 10
MIN_FACE_VISIBILITY = 0.7
HOLD_FACE_TIME = 2

# Image Quality
MIN_FACE_CONTRAST = 30
MIN_FACE_SIZE = 50

# Liveness Detection
RANDOM_ACTIONS = [
    "Vui lòng quay đầu sang trái",
    "Vui lòng quay đầu sang phải",
    "Vui lòng nháy mắt",
    "Vui lòng gật đầu"
]

ACTION_TIMEOUT = 5
LIVENESS_THRESHOLD = 0.7

AUTO_DETECT_IN_OUT = True
