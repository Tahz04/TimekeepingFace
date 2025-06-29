import os
import sqlite3
from datetime import datetime
from config import DATABASE_PATH


class AttendanceSystem:
    def __init__(self):
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

        try:
            self.conn = sqlite3.connect(DATABASE_PATH)
            self._create_table()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise

    def _create_table(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time_in TEXT NOT NULL,
                    time_out TEXT,
                    status TEXT
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Create table error: {e}")
            raise

    def mark_attendance(self, name):
        try:
            cursor = self.conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            now = datetime.now().strftime('%H:%M:%S')

            cursor.execute('''
                SELECT id, time_out FROM attendance 
                WHERE name=? AND date=?
                ORDER BY time_in DESC LIMIT 1
            ''', (name, today))
            record = cursor.fetchone()

            if record:
                if not record[1]:  # Chưa check-out
                    cursor.execute('''
                        UPDATE attendance 
                        SET time_out=?, status='OUT' 
                        WHERE id=?
                    ''', (now, record[0]))
                    print(f"{name} checked OUT at {now}")
            else:
                cursor.execute('''
                    INSERT INTO attendance (name, date, time_in, status)
                    VALUES (?, ?, ?, 'IN')
                ''', (name, today, now))
                print(f"{name} checked IN at {now}")

            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Mark attendance error: {e}")
            self.conn.rollback()

    def get_report(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, name, date, time_in, time_out, status 
                FROM attendance 
                ORDER BY date DESC, time_in DESC
            ''')
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Get report error: {e}")
            return []

    def close(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def __del__(self):
        self.close()