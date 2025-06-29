import os
import numpy as np
import cv2
import face_recognition
from datetime import datetime

# Constants
PATH_DATA = 'datas'
ATTENDANCE_FILE = 'Attendance.csv'

def load_images(path):
    images = []
    class_names = []
    for img_name in os.listdir(path):
        img_path = os.path.join(path, img_name)
        img = cv2.imread(img_path)
        if img is not None:
            images.append(img)
            class_names.append(os.path.splitext(img_name)[0])
        else:
            print(f"Warning: Could not read image {img_path}")
    return images, class_names

def find_encodings(images):
    encode_list = []
    for img in images:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodes = face_recognition.face_encodings(img_rgb)
        if encodes:
            encode_list.append(encodes[0])
        else:
            print("Warning: No face found in an image, skipping!")
    return encode_list

def mark_attendance(name):
    # Check if name already exists
    try:
        with open(ATTENDANCE_FILE, 'r+') as f:
            lines = f.readlines()
            names = [line.split(',')[0] for line in lines]
            if name not in names:
                now = datetime.now()
                dt_str = now.strftime('%Y-%m-%d, %H:%M:%S')
                f.write(f'{name}, {dt_str}\n')
    except FileNotFoundError:
        # Create file if not exists
        with open(ATTENDANCE_FILE, 'w') as f:
            now = datetime.now()
            dt_str = now.strftime('%Y-%m-%d, %H:%M:%S')
            f.write(f'{name}, {dt_str}\n')

def draw_face_info(img, name, face_loc, color=(0, 255, 0)):
    y1, x2, y2, x1 = [coord * 4 for coord in face_loc]  # Scale back up
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.rectangle(img, (x1, y2), (x2, y2 + 35), color, cv2.FILLED)
    cv2.putText(img, name, (x1 + 6, y2 + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

def main():
    # Load known faces
    images, class_names = load_images(PATH_DATA)
    encode_list_known = find_encodings(images)
    print(f'Encoding complete. {len(encode_list_known)} faces loaded.')

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    while True:
        success, img = cap.read()
        if not success:
            print("Error: Could not read frame.")
            break

        img = cv2.flip(img, 1)  # Mirror effect
        img_small = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        img_small_rgb = cv2.cvtColor(img_small, cv2.COLOR_BGR2RGB)

        # Face detection
        face_locs = face_recognition.face_locations(img_small_rgb)
        face_encodes = face_recognition.face_encodings(img_small_rgb, face_locs)

        for encode_face, face_loc in zip(face_encodes, face_locs):
            matches = face_recognition.compare_faces(encode_list_known, encode_face)
            face_distances = face_recognition.face_distance(encode_list_known, encode_face)
            best_match_idx = np.argmin(face_distances)

            if matches[best_match_idx] and face_distances[best_match_idx] < 0.6:  # Threshold
                name = class_names[best_match_idx].upper()
                mark_attendance(name)
                draw_face_info(img, name, face_loc)
            else:
                draw_face_info(img, "UNKNOWN", face_loc, (0, 0, 255))

        cv2.imshow('Face Attendance', img)
        key = cv2.waitKey(1)
        if key == ord('q') or key == 27:  # 'q' or ESC
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()