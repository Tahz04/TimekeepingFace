import sqlite3
from datetime import datetime
from face_utils import FaceRecognizer
from config import DATABASE_PATH, DATA_DIR

class EmployeeModel:
    def __init__(self):
        self.DB_PATH = DATABASE_PATH
        self.face_recognizer = FaceRecognizer()
        self.face_recognizer.load_known_faces(DATA_DIR)
        self.conn = sqlite3.connect(self.DB_PATH)
        self.cursor = self.conn.cursor()

    def recognize_employee(self, face_encoding):
        try:
            name = self.face_recognizer.recognize_face(face_encoding)
            if not name:
                return None, None

            self.cursor.execute("SELECT id FROM employees WHERE name=?", (name,))
            result = self.cursor.fetchone()
            return (result[0], name) if result else (None, None)
        except sqlite3.Error as e:
            print(f"Lỗi truy vấn database: {str(e)}")
            return None, None

    def recognize_employee_by_name(self, name):
        """Nhận diện nhân viên bằng tên (đã xác thực)"""
        try:
            self.cursor.execute("SELECT id FROM employees WHERE name=?", (name,))
            result = self.cursor.fetchone()
            return (result[0], name) if result else (None, None)
        except sqlite3.Error as e:
            print(f"Lỗi truy vấn database: {str(e)}")
            return None, None

    def mark_attendance(self, emp_id, name):
        """Chấm công cho nhân viên và trả về trạng thái hiện tại"""
        if not emp_id or not name:
            return False, None

        try:
            today = datetime.now().strftime('%Y-%m-%d')
            now = datetime.now().strftime('%H:%M:%S')

            # Kiểm tra lần chấm công gần nhất
            self.cursor.execute('''
                SELECT id, time_out FROM attendance 
                WHERE employee_id=? AND date=?
                ORDER BY time_in DESC LIMIT 1
            ''', (emp_id, today))
            record = self.cursor.fetchone()

            current_status = None
            if record and not record[1]:  # Đã chấm vào nhưng chưa chấm ra
                self.cursor.execute('''
                    UPDATE attendance SET time_out=?, status='OUT' WHERE id=?
                ''', (now, record[0]))
                current_status = 'OUT'
            else:  # Chấm công vào
                self.cursor.execute('''
                    INSERT INTO attendance (employee_id, date, time_in, status)
                    VALUES (?, ?, ?, 'IN')
                ''', (emp_id, today, now))
                current_status = 'IN'

            self.conn.commit()
            return True, current_status
        except sqlite3.Error as e:
            print(f"Lỗi chấm công: {str(e)}")
            self.conn.rollback()
            return False, None

    def close(self):
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
        except sqlite3.Error as e:
            print(f"Lỗi đóng kết nối: {str(e)}")
