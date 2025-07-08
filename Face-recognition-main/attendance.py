# attendance_system.py

import os
import sqlite3
from datetime import datetime, date
from pathlib import Path

# Mặc định lưu vào thư mục data/attendance.db
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / 'data' / 'attendance.db'


class AttendanceSystem:
    def __init__(self, db_path: Path = DATABASE_PATH):
        # Tạo folder nếu chưa có
        os.makedirs(db_path.parent, exist_ok=True)
        # Kết nối SQLite và dùng Row factory để trả về dict-like
        self.conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        """Tạo bảng attendance nếu chưa tồn tại."""
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    name      TEXT    NOT NULL,
                    date      DATE    NOT NULL,
                    time_in   TIME    NOT NULL,
                    time_out  TIME,
                    status    TEXT
                )
            ''')

    def mark_attendance(self, name: str):
        """
        Nếu hôm nay chưa có bản ghi IN thì insert (status='IN'),
        nếu đã IN nhưng chưa OUT thì update time_out và status='OUT'.
        """
        now_dt = datetime.now()
        today = now_dt.date()
        now_time = now_dt.time().strftime('%H:%M:%S')

        cur = self.conn.cursor()
        # Lấy bản ghi mới nhất của name hôm nay
        cur.execute('''
            SELECT id, time_out 
            FROM attendance
            WHERE name = ? AND date = ?
            ORDER BY id DESC
            LIMIT 1
        ''', (name, today))
        row = cur.fetchone()

        if row and row['time_out'] is None:
            # Đã check IN, chưa check OUT => thực hiện OUT
            cur.execute('''
                UPDATE attendance
                SET time_out = ?, status = 'OUT'
                WHERE id = ?
            ''', (now_time, row['id']))
            print(f"[{now_dt}] {name} checked OUT at {now_time}")
        else:
            # Chưa có bản ghi IN tương ứng => tạo mới IN
            cur.execute('''
                INSERT INTO attendance (name, date, time_in, status)
                VALUES (?, ?, ?, 'IN')
            ''', (name, today, now_time))
            print(f"[{now_dt}] {name} checked  IN at {now_time}")

        self.conn.commit()

    def get_report(self):
        """Trả về toàn bộ bảng attendance, sorted mới nhất trước."""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT id, name, date, time_in, time_out, status
            FROM attendance
            ORDER BY date DESC, time_in DESC
        ''')
        return [dict(row) for row in cur.fetchall()]

    def get_daily_report(self, for_date: date):
        """Trả về báo cáo cho đúng một ngày."""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT name, time_in, time_out, status
            FROM attendance
            WHERE date = ?
            ORDER BY time_in
        ''', (for_date,))
        return [dict(row) for row in cur.fetchall()]

    def get_user_report(self, name: str):
        """Trả về toàn bộ bản ghi của một người."""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT date, time_in, time_out, status
            FROM attendance
            WHERE name = ?
            ORDER BY date DESC, time_in DESC
        ''', (name,))
        return [dict(row) for row in cur.fetchall()]

    def clear_all(self):
        """Xoá sạch toàn bộ record (dùng cẩn thận!)."""
        with self.conn:
            self.conn.execute('DELETE FROM attendance')

    def close(self):
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Ví dụ sử dụng
if __name__ == '__main__':
    from datetime import date

    with AttendanceSystem() as ats:
        ats.mark_attendance('Alice')
        ats.mark_attendance('Bob')
        ats.mark_attendance('Alice')   # lần này Alice sẽ OUT
        
        print("=== Full Report ===")
        for r in ats.get_report():
            print(r)

        print("\n=== Report Today ===")
        for r in ats.get_daily_report(date.today()):
            print(r)

        print("\n=== Alice's Log ===")
        for r in ats.get_user_report('Alice'):
            print(r)
