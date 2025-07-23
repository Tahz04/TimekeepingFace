import os
import sqlite3
import face_recognition
from datetime import datetime
from tkinter import messagebox
import pandas as pd


class AdminModel:
    def __init__(self):
        self.DATA_DIR = 'datas'
        self.DB_PATH = 'database/attendance.db'
        self.EXPORT_DIR = 'exports'

        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.EXPORT_DIR, exist_ok=True)
        os.makedirs('database', exist_ok=True)

        self.conn = sqlite3.connect(self.DB_PATH)
        self.cursor = self.conn.cursor()
        self.upgrade_database_structure()
        self.sync_employee_data()
        self.fix_wrong_attendance_data()

    def upgrade_database_structure(self):
        """Nâng cấp cấu trúc database nếu cần"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    image_path TEXT NOT NULL
                )
            ''')

            self.cursor.execute("PRAGMA table_info(attendance)")
            columns = [col[1] for col in self.cursor.fetchall()]

            if 'employee_id' not in columns:
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS attendance_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        time_in TEXT,
                        time_out TEXT,
                        status TEXT,
                        FOREIGN KEY (employee_id) REFERENCES employees (id)
                    )
                ''')

                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance'")
                if self.cursor.fetchone():
                    self.cursor.execute('''
                        INSERT INTO attendance_new (employee_id, date, time_in, time_out, status)
                        SELECT 1, date, time_in, time_out, status FROM attendance
                    ''')
                    self.cursor.execute("DROP TABLE attendance")
                    self.cursor.execute("ALTER TABLE attendance_new RENAME TO attendance")

            self.conn.commit()
        except Exception as e:
            messagebox.showerror("Database Error", f"Không thể nâng cấp database: {str(e)}")
            self.conn.rollback()

    def sync_employee_data(self):
        """Đồng bộ dữ liệu nhân viên giữa database và thư mục ảnh"""
        try:
            self.cursor.execute("SELECT id, name, image_path FROM employees")
            db_employees = self.cursor.fetchall()

            image_files = [f for f in os.listdir(self.DATA_DIR) if f.lower().endswith(('.jpg', '.png'))]

            for emp in db_employees:
                emp_id, name, image_path = emp
                if not os.path.exists(image_path):
                    self.cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
                    self.conn.commit()

            for img_file in image_files:
                img_path = os.path.join(self.DATA_DIR, img_file)
                name = os.path.splitext(img_file)[0].replace('_', ' ')

                self.cursor.execute("SELECT id FROM employees WHERE image_path=?", (img_path,))
                if not self.cursor.fetchone():
                    try:
                        img = face_recognition.load_image_file(img_path)
                        if face_recognition.face_encodings(img):
                            self.cursor.execute(
                                "INSERT INTO employees (name, image_path) VALUES (?, ?)",
                                (name, img_path)
                            )
                            self.conn.commit()
                    except Exception:
                        pass

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đồng bộ dữ liệu nhân viên: {str(e)}")

    def fix_wrong_attendance_data(self):
        """Sửa dữ liệu chấm công bị nhầm lẫn giữa các nhân viên"""
        try:
            self.cursor.execute('''
                SELECT a.id, a.employee_id, e.name, e.image_path 
                FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                WHERE e.name = 'Bill Gates'
            ''')
            bill_gates_records = self.cursor.fetchall()

            self.cursor.execute("SELECT id, name, image_path FROM employees")
            all_employees = {emp[1]: emp for emp in self.cursor.fetchall()}

            for record in bill_gates_records:
                att_id, emp_id, name, image_path = record
                if not os.path.exists(image_path):
                    continue

                img = face_recognition.load_image_file(image_path)
                face_encodings = face_recognition.face_encodings(img)
                if not face_encodings:
                    continue

                for emp_name, emp_data in all_employees.items():
                    if emp_name == name:
                        continue

                    other_img = face_recognition.load_image_file(emp_data[2])
                    other_encodings = face_recognition.face_encodings(other_img)
                    if not other_encodings:
                        continue

                    matches = face_recognition.compare_faces([face_encodings[0]], other_encodings[0])
                    if matches[0]:
                        self.cursor.execute(
                            "UPDATE attendance SET employee_id=? WHERE id=?",
                            (emp_data[0], att_id))
                        self.conn.commit()
                        break

        except Exception as e:
            print(f"Lỗi khi sửa dữ liệu chấm công: {str(e)}")

    def get_employees(self):
        """Lấy danh sách nhân viên"""
        self.cursor.execute("SELECT id, name FROM employees ORDER BY name")
        return self.cursor.fetchall()

    def search_employees(self, search_term):
        """Tìm kiếm nhân viên"""
        self.cursor.execute("SELECT id, name FROM employees WHERE LOWER(name) LIKE ? ORDER BY name",
                            (f"%{search_term.lower()}%",))
        return self.cursor.fetchall()

    def get_employee_details(self, emp_id):
        """Lấy chi tiết nhân viên"""
        self.cursor.execute("SELECT name, image_path FROM employees WHERE id=?", (emp_id,))
        return self.cursor.fetchone()

    def register_employee(self, name, image_path):
        """Đăng ký nhân viên mới"""
        try:
            self.cursor.execute("INSERT INTO employees (name, image_path) VALUES (?, ?)", (name, image_path))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_employee(self, emp_id, name, image_path=None):
        """Cập nhật thông tin nhân viên"""
        try:
            if image_path:
                self.cursor.execute("UPDATE employees SET name=?, image_path=? WHERE id=?",
                                    (name, image_path, emp_id))
            else:
                self.cursor.execute("UPDATE employees SET name=? WHERE id=?", (name, emp_id))
            self.conn.commit()
            return True
        except Exception:
            return False

    def delete_employee(self, emp_id):
        """Xóa nhân viên"""
        try:
            self.cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_attendance_data(self):
        """Lấy dữ liệu chấm công"""
        self.cursor.execute('''
            SELECT a.id, e.name, a.date, a.time_in, a.time_out, a.status 
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            ORDER BY a.date DESC, a.time_in DESC
        ''')
        return self.cursor.fetchall()

    def export_attendance(self, date_from, date_to):
        """Xuất dữ liệu chấm công"""
        self.cursor.execute('''
            SELECT a.id, e.name, a.date, a.time_in, a.time_out, a.status 
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            WHERE a.date BETWEEN ? AND ?
            ORDER BY a.date, a.time_in
        ''', (date_from, date_to))
        return self.cursor.fetchall()

    def close(self):
        """Đóng kết nối database"""
        if hasattr(self, 'conn'):
            self.conn.close()