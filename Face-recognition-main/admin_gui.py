import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
import cv2
from PIL import Image, ImageTk
import os
import sqlite3
import pandas as pd
import face_recognition
from datetime import datetime


class AdminGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Admin Management")

        # Cấu hình đường dẫn
        self.DATA_DIR = 'datas'
        self.DB_PATH = 'database/attendance.db'
        self.EXPORT_DIR = 'exports'
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.EXPORT_DIR, exist_ok=True)
        os.makedirs('database', exist_ok=True)

        # Kết nối database
        self.conn = sqlite3.connect(self.DB_PATH)
        self.cursor = self.conn.cursor()

        # Kiểm tra và nâng cấp cấu trúc database
        self.upgrade_database_structure()

        # Đồng bộ dữ liệu khi khởi động
        self.sync_employee_data()

        # Sửa dữ liệu chấm công bị nhầm lẫn
        self.fix_wrong_attendance_data()

        # Biến tạm
        self.captured_image = None
        self.cap = None
        self.current_employee_id = None
        self.image_width = 400
        self.image_height = 300
        self.camera_running = False  # Thêm biến trạng thái camera

        # Thiết lập giao diện
        self.setup_ui()

    def fix_wrong_attendance_data(self):
        """Sửa dữ liệu chấm công bị nhầm lẫn giữa các nhân viên"""
        try:
            # Kiểm tra xem có bản ghi nào của Bill Gates nhưng không có ảnh mặt không khớp
            self.cursor.execute('''
                SELECT a.id, a.employee_id, e.name, e.image_path 
                FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                WHERE e.name = 'Bill Gates'
            ''')
            bill_gates_records = self.cursor.fetchall()

            # Lấy danh sách tất cả nhân viên
            self.cursor.execute("SELECT id, name, image_path FROM employees")
            all_employees = {emp[1]: emp for emp in self.cursor.fetchall()}

            for record in bill_gates_records:
                att_id, emp_id, name, image_path = record
                if not os.path.exists(image_path):
                    continue

                # Kiểm tra xem ảnh có thực sự là Bill Gates không
                img = face_recognition.load_image_file(image_path)
                face_encodings = face_recognition.face_encodings(img)
                if not face_encodings:
                    continue

                # So sánh với ảnh của các nhân viên khác
                for emp_name, emp_data in all_employees.items():
                    if emp_name == name:
                        continue

                    other_img = face_recognition.load_image_file(emp_data[2])
                    other_encodings = face_recognition.face_encodings(other_img)
                    if not other_encodings:
                        continue

                    # So sánh khuôn mặt
                    matches = face_recognition.compare_faces([face_encodings[0]], other_encodings[0])
                    if matches[0]:
                        # Cập nhật lại employee_id cho bản ghi chấm công
                        self.cursor.execute(
                            "UPDATE attendance SET employee_id=? WHERE id=?",
                            (emp_data[0], att_id))
                        self.conn.commit()
                        print(f"Đã sửa bản ghi {att_id} từ {name} sang {emp_name}")
                        break

        except Exception as e:
            print(f"Lỗi khi sửa dữ liệu chấm công: {str(e)}")

    def upgrade_database_structure(self):
        """Nâng cấp cấu trúc database nếu cần"""
        try:
            # Tạo bảng employees nếu chưa tồn tại
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    image_path TEXT NOT NULL
                )
            ''')

            # Kiểm tra bảng attendance có cột employee_id chưa
            self.cursor.execute("PRAGMA table_info(attendance)")
            columns = [col[1] for col in self.cursor.fetchall()]

            if 'employee_id' not in columns:
                # Tạo bảng tạm và chuyển dữ liệu
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

                # Chuyển dữ liệu từ bảng cũ sang bảng mới
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance'")
                if self.cursor.fetchone():
                    # Tạm thời gán tất cả bản ghi cũ cho employee_id = 1
                    self.cursor.execute('''
                        INSERT INTO attendance_new (employee_id, date, time_in, time_out, status)
                        SELECT 1, date, time_in, time_out, status FROM attendance
                    ''')

                    # Xóa bảng cũ và đổi tên bảng mới
                    self.cursor.execute("DROP TABLE attendance")
                    self.cursor.execute("ALTER TABLE attendance_new RENAME TO attendance")

            self.conn.commit()
        except Exception as e:
            messagebox.showerror("Database Error", f"Không thể nâng cấp database: {str(e)}")
            self.conn.rollback()

    def sync_employee_data(self):
        """Đồng bộ dữ liệu nhân viên giữa database và thư mục ảnh"""
        try:
            # Lấy danh sách nhân viên từ database
            self.cursor.execute("SELECT id, name, image_path FROM employees")
            db_employees = self.cursor.fetchall()

            # Lấy danh sách file ảnh trong thư mục datas (cả .jpg và .png)
            image_files = [f for f in os.listdir(self.DATA_DIR) if f.lower().endswith(('.jpg', '.png'))]

            # Kiểm tra từng nhân viên trong database
            for emp in db_employees:
                emp_id, name, image_path = emp
                # Kiểm tra xem file ảnh có tồn tại không
                if not os.path.exists(image_path):
                    # Xóa nhân viên không có ảnh
                    self.cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
                    self.conn.commit()

            # Kiểm tra file ảnh không có trong database
            for img_file in image_files:
                img_path = os.path.join(self.DATA_DIR, img_file)
                name = os.path.splitext(img_file)[0].replace('_', ' ')

                self.cursor.execute("SELECT id FROM employees WHERE image_path=?", (img_path,))
                if not self.cursor.fetchone():
                    # Thêm nhân viên mới nếu phát hiện ảnh không có trong database
                    try:
                        img = face_recognition.load_image_file(img_path)
                        if face_recognition.face_encodings(img):
                            self.cursor.execute(
                                "INSERT INTO employees (name, image_path) VALUES (?, ?)",
                                (name, img_path)
                            )
                            self.conn.commit()
                    except Exception as e:
                        print(f"Không thể thêm nhân viên từ file ảnh {img_file}: {str(e)}")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đồng bộ dữ liệu nhân viên: {str(e)}")

    def setup_ui(self):
        """Thiết lập giao diện chính"""
        tab_control = ttk.Notebook(self.root)

        # Tab quản lý nhân viên (tích hợp cả đăng ký)
        tab_employees = ttk.Frame(tab_control)
        self.setup_employees_tab(tab_employees)

        # Tab quản lý chấm công
        tab_manage = ttk.Frame(tab_control)
        self.setup_manage_tab(tab_manage)

        # Tab xuất báo cáo
        tab_export = ttk.Frame(tab_control)
        self.setup_export_tab(tab_export)

        tab_control.add(tab_employees, text='Quản lý nhân viên')
        tab_control.add(tab_manage, text='Quản lý chấm công')
        tab_control.add(tab_export, text='Xuất báo cáo')
        tab_control.pack(expand=1, fill="both")

    def setup_employees_tab(self, parent):
        """Thiết lập tab quản lý nhân viên (tích hợp cả đăng ký)"""
        # Frame chứa danh sách nhân viên và thanh tìm kiếm
        list_frame = tk.Frame(parent)
        list_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Frame thanh tìm kiếm
        search_frame = tk.Frame(list_frame)
        search_frame.pack(fill="x", pady=5)

        lbl_search = tk.Label(search_frame, text="Tìm kiếm:")
        lbl_search.pack(side="left", padx=5)

        self.entry_search = tk.Entry(search_frame, width=30)
        self.entry_search.pack(side="left", padx=5)
        self.entry_search.bind("<KeyRelease>", self.search_employee)

        btn_search = tk.Button(
            search_frame,
            text="Tìm",
            command=self.search_employee,
            bg="#2196F3",
            fg="white",
            width=5
        )
        btn_search.pack(side="left", padx=5)

        # Tạo Treeview
        columns = ("id", "name")
        self.employee_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        # Đặt tiêu đề cột
        self.employee_tree.heading("id", text="ID")
        self.employee_tree.heading("name", text="Tên nhân viên")

        # Đặt độ rộng cột
        self.employee_tree.column("id", width=50, anchor="center")
        self.employee_tree.column("name", width=250, anchor="w")

        # Thanh cuộn
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.employee_tree.yview)
        self.employee_tree.configure(yscrollcommand=scrollbar.set)

        # Bố cục Treeview
        self.employee_tree.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Frame chứa các nút chức năng
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(side="bottom", pady=5)

        # Nút làm mới
        btn_refresh = tk.Button(
            btn_frame,
            text="Làm mới",
            command=self.load_employee_data,
            bg="#607D8B",
            fg="white",
            width=10
        )
        btn_refresh.pack(side="left", padx=5)

        # Nút xóa
        btn_delete = tk.Button(
            btn_frame,
            text="Xóa",
            command=self.delete_employee,
            bg="#F44336",
            fg="white",
            width=10
        )
        btn_delete.pack(side="left", padx=5)

        # Frame chứa thông tin chi tiết và đăng ký
        detail_frame = tk.Frame(parent)
        detail_frame.pack(side="right", fill="both", padx=5, pady=5)

        # Phần hiển thị thông tin nhân viên
        self.info_frame = tk.LabelFrame(detail_frame, text="Thông tin nhân viên", width=self.image_width,
                                        height=self.image_height)
        self.info_frame.pack(fill="both", expand=True, pady=5)
        self.info_frame.pack_propagate(False)  # Ngăn frame tự điều chỉnh kích thước

        # Label hiển thị ảnh
        self.employee_image_label = tk.Label(self.info_frame)
        self.employee_image_label.pack(expand=True)

        # Label hiển thị tên
        self.employee_name_label = tk.Label(self.info_frame, text="Chọn nhân viên để xem thông tin", font=('Arial', 12))
        self.employee_name_label.pack(side="bottom", pady=5)

        # Phần đăng ký/cập nhật nhân viên
        register_frame = tk.LabelFrame(detail_frame, text="Đăng ký/Cập nhật nhân viên")
        register_frame.pack(fill="both", expand=True, pady=5)

        # Phần nhập tên
        lbl_name = tk.Label(register_frame, text="Tên nhân viên:")
        lbl_name.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.entry_name = tk.Entry(register_frame, width=30)
        self.entry_name.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Frame hiển thị camera
        self.camera_frame = tk.LabelFrame(register_frame, text="Camera", width=self.image_width,
                                          height=self.image_height)
        self.camera_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        self.camera_frame.grid_propagate(False)  # Ngăn frame tự điều chỉnh kích thước

        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(expand=True)

        # Nút điều khiển
        btn_camera_frame = tk.Frame(register_frame)
        btn_camera_frame.grid(row=2, column=0, columnspan=2, pady=5)

        # Nút bật/tắt camera
        self.btn_toggle_cam = tk.Button(
            btn_camera_frame,
            text="Bật Camera",
            command=self.toggle_camera,
            bg="#2196F3",
            fg="white",
            width=15
        )
        self.btn_toggle_cam.pack(side="left", padx=5)

        self.btn_capture = tk.Button(
            btn_camera_frame,
            text="Chụp Ảnh",
            command=self.capture_image,
            bg="#4CAF50",
            fg="white",
            width=15,
            state="disabled"
        )
        self.btn_capture.pack(side="left", padx=5)

        # Nút đăng ký/cập nhật
        self.btn_register = tk.Button(
            register_frame,
            text="Đăng ký Nhân viên",
            command=self.register_employee,
            bg="#FF9800",
            fg="white",
            width=20
        )
        self.btn_register.grid(row=3, column=0, columnspan=2, pady=10)

        # Nút cập nhật
        self.btn_update = tk.Button(
            register_frame,
            text="Cập nhật Nhân viên",
            command=self.update_employee,
            bg="#9C27B0",
            fg="white",
            width=20,
            state="disabled"
        )
        self.btn_update.grid(row=4, column=0, columnspan=2, pady=5)

        # Bắt sự kiện chọn nhân viên
        self.employee_tree.bind("<<TreeviewSelect>>", self.on_employee_selected)

        # Tải dữ liệu nhân viên
        self.load_employee_data()

    def search_employee(self, event=None):
        """Tìm kiếm nhân viên theo tên"""
        search_term = self.entry_search.get().strip().lower()

        # Xóa dữ liệu cũ
        for item in self.employee_tree.get_children():
            self.employee_tree.delete(item)

        # Lấy dữ liệu từ database
        self.cursor.execute("SELECT id, name, image_path FROM employees ORDER BY name")
        employees = self.cursor.fetchall()

        # Thêm vào Treeview nếu phù hợp với từ khóa tìm kiếm
        for emp in employees:
            emp_id, name, image_path = emp
            if search_term in name.lower() and os.path.exists(image_path):
                self.employee_tree.insert("", "end", values=(emp_id, name))

    def toggle_camera(self):
        """Bật/tắt camera"""
        if self.camera_running:
            self.stop_camera()
        else:
            self.start_camera()

    def on_employee_selected(self, event):
        """Xử lý khi chọn nhân viên từ danh sách"""
        selected = self.employee_tree.selection()
        if not selected:
            return

        item = self.employee_tree.item(selected[0])
        emp_id, name = item['values']
        self.current_employee_id = emp_id

        # Hiển thị tên nhân viên
        self.employee_name_label.config(text=name)
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, name)

        # Hiển thị ảnh nhân viên
        self.cursor.execute("SELECT image_path FROM employees WHERE id=?", (emp_id,))
        result = self.cursor.fetchone()
        if result:
            img_path = result[0]
            try:
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    # Resize ảnh để vừa với khung
                    img.thumbnail((self.image_width, self.image_height))
                    photo = ImageTk.PhotoImage(img)
                    self.employee_image_label.config(image=photo)
                    self.employee_image_label.image = photo
                else:
                    self.employee_image_label.config(image='', text="Không tìm thấy ảnh")
            except Exception as e:
                print(f"Lỗi khi tải ảnh: {str(e)}")
                self.employee_image_label.config(image='', text="Lỗi khi tải ảnh")

        # Kích hoạt nút cập nhật
        self.btn_update.config(state="normal")
        self.btn_register.config(state="disabled")

    def setup_manage_tab(self, parent):
        """Thiết lập tab quản lý chấm công"""
        # Tạo Treeview
        columns = ("id", "name", "date", "time_in", "time_out", "status")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings")

        # Đặt tiêu đề cột
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Tên nhân viên")
        self.tree.heading("date", text="Ngày")
        self.tree.heading("time_in", text="Giờ vào")
        self.tree.heading("time_out", text="Giờ ra")
        self.tree.heading("status", text="Trạng thái")

        # Đặt độ rộng cột
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("name", width=150, anchor="w")
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("time_in", width=100, anchor="center")
        self.tree.column("time_out", width=100, anchor="center")
        self.tree.column("status", width=80, anchor="center")

        # Thanh cuộn
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Bố cục
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Nút làm mới
        btn_refresh = tk.Button(
            parent,
            text="Làm mới dữ liệu",
            command=self.load_attendance_data,
            bg="#607D8B",
            fg="white"
        )
        btn_refresh.pack(side="bottom", pady=5)

        # Tải dữ liệu
        self.load_attendance_data()

    def setup_export_tab(self, parent):
        """Thiết lập tab xuất báo cáo"""
        # Chọn ngày bắt đầu
        lbl_from = tk.Label(parent, text="Từ ngày:")
        lbl_from.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.cal_from = DateEntry(parent, date_pattern='yyyy-mm-dd')
        self.cal_from.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Chọn ngày kết thúc
        lbl_to = tk.Label(parent, text="Đến ngày:")
        lbl_to.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self.cal_to = DateEntry(parent, date_pattern='yyyy-mm-dd')
        self.cal_to.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Nút xuất báo cáo
        btn_export = tk.Button(
            parent,
            text="Xuất Excel",
            command=self.export_to_excel,
            bg="#FF9800",
            fg="white",
            width=20
        )
        btn_export.grid(row=2, column=0, columnspan=2, pady=10)

    def toggle_camera(self):
        """Bật/tắt camera"""
        if self.camera_running:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        """Bật camera để chụp ảnh"""
        try:
            # Đóng camera nếu đang mở
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()

            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("Không thể mở camera")

            # Thiết lập kích thước camera
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.image_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.image_height)

            self.camera_running = True
            self.btn_toggle_cam.config(text="Tắt Camera", bg="#F44336")
            self.btn_capture.config(state="normal")
            self.update_camera()  # Bắt đầu cập nhật hình ảnh từ camera
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể khởi động camera: {str(e)}")
            self.stop_camera()

    def update_camera(self):
        """Cập nhật hình ảnh từ camera liên tục"""
        if self.camera_running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.flip(frame, 1)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Phát hiện khuôn mặt
                    face_locations = face_recognition.face_locations(rgb_frame)
                    for (top, right, bottom, left) in face_locations:
                        cv2.rectangle(rgb_frame, (left, top), (right, bottom), (0, 255, 0), 2)

                    # Chuyển đổi sang định dạng PIL và resize
                    img = Image.fromarray(rgb_frame)
                    img.thumbnail((self.image_width, self.image_height))

                    # Hiển thị lên giao diện
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.camera_label.imgtk = imgtk
                    self.camera_label.config(image=imgtk)

                # Lặp lại sau 10ms
                self.camera_label.after(10, self.update_camera)
            except Exception as e:
                print(f"Lỗi hiển thị camera: {str(e)}")
                self.stop_camera()

    def stop_camera(self):
        """Tắt camera"""
        self.camera_running = False
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
            self.cap = None

        self.btn_toggle_cam.config(text="Bật Camera", bg="#2196F3")
        self.btn_capture.config(state="disabled")
        self.camera_label.config(image='')

    def capture_image(self):
        """Chụp ảnh từ camera"""
        if not self.camera_running:
            messagebox.showerror("Lỗi", "Vui lòng bật camera trước khi chụp ảnh")
            return

        try:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                self.captured_image = frame

                # Tắt camera sau khi chụp
                self.stop_camera()

                # Hiển thị ảnh đã chụp
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                img.thumbnail((self.image_width, self.image_height))
                imgtk = ImageTk.PhotoImage(image=img)

                # Giữ reference để ảnh không bị garbage collected
                self.camera_label.imgtk = imgtk
                self.camera_label.config(image=imgtk)

                messagebox.showinfo("Thành công", "Đã chụp ảnh thành công!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể chụp ảnh: {str(e)}")
            self.stop_camera()

    def register_employee(self):
        """Đăng ký nhân viên mới"""
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên nhân viên")
            return

        if not hasattr(self, 'captured_image'):
            messagebox.showerror("Lỗi", "Vui lòng chụp ảnh trước khi đăng ký")
            return

        try:
            # Tạo tên file
            filename = f"{name.replace(' ', '_')}.jpg"
            filepath = os.path.join(self.DATA_DIR, filename)

            # Kiểm tra trùng tên trong database
            self.cursor.execute("SELECT id FROM employees WHERE name=?", (name,))
            if self.cursor.fetchone():
                messagebox.showerror("Lỗi", "Nhân viên đã tồn tại!")
                return

            # Kiểm tra trùng file ảnh
            if os.path.exists(filepath):
                messagebox.showerror("Lỗi", "File ảnh đã tồn tại!")
                return

            # Lưu ảnh
            cv2.imwrite(filepath, self.captured_image)

            # Kiểm tra khuôn mặt hợp lệ
            img = face_recognition.load_image_file(filepath)
            encodings = face_recognition.face_encodings(img)

            if not encodings:
                os.remove(filepath)
                messagebox.showerror("Lỗi", "Không phát hiện khuôn mặt trong ảnh!")
                return

            # Thêm vào database
            self.cursor.execute(
                "INSERT INTO employees (name, image_path) VALUES (?, ?)",
                (name, filepath)
            )
            self.conn.commit()

            # Reset form
            self.entry_name.delete(0, tk.END)
            self.camera_label.config(image='')
            self.btn_register.config(state="normal")
            if hasattr(self, 'captured_image'):
                del self.captured_image

            # Làm mới danh sách nhân viên
            self.load_employee_data()

            messagebox.showinfo("Thành công", f"Đã đăng ký nhân viên {name}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi đăng ký: {str(e)}")

    def update_employee(self):
        """Cập nhật thông tin nhân viên"""
        if not self.current_employee_id:
            messagebox.showerror("Lỗi", "Vui lòng chọn nhân viên cần cập nhật")
            return

        name = self.entry_name.get().strip()
        if not name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên nhân viên")
            return

        try:
            # Lấy đường dẫn ảnh cũ
            self.cursor.execute("SELECT image_path FROM employees WHERE id=?", (self.current_employee_id,))
            old_img_path = self.cursor.fetchone()[0]

            # Nếu có ảnh mới, cập nhật ảnh
            if hasattr(self, 'captured_image') and self.captured_image is not None:
                # Xóa ảnh cũ nếu tồn tại
                if os.path.exists(old_img_path):
                    try:
                        os.remove(old_img_path)
                    except Exception as e:
                        print(f"Không thể xóa file ảnh cũ: {str(e)}")

                # Tạo tên file mới
                filename = f"{name.replace(' ', '_')}.jpg"
                new_img_path = os.path.join(self.DATA_DIR, filename)

                # Lưu ảnh mới
                cv2.imwrite(new_img_path, self.captured_image)

                # Cập nhật đường dẫn ảnh trong database
                self.cursor.execute(
                    "UPDATE employees SET image_path=? WHERE id=?",
                    (new_img_path, self.current_employee_id)
                )
            else:
                # Nếu không có ảnh mới nhưng tên thay đổi, cần đổi tên file
                if name != self.employee_name_label.cget("text"):
                    # Tạo tên file mới
                    filename = f"{name.replace(' ', '_')}.jpg"
                    new_img_path = os.path.join(self.DATA_DIR, filename)

                    # Đổi tên file
                    if os.path.exists(old_img_path):
                        os.rename(old_img_path, new_img_path)

                    # Cập nhật đường dẫn ảnh trong database
                    self.cursor.execute(
                        "UPDATE employees SET image_path=? WHERE id=?",
                        (new_img_path, self.current_employee_id)
                    )

            # Cập nhật tên trong database
            self.cursor.execute(
                "UPDATE employees SET name=? WHERE id=?",
                (name, self.current_employee_id)
            )

            self.conn.commit()

            # Làm mới danh sách và hiển thị
            self.load_employee_data()
            self.on_employee_selected(None)  # Cập nhật lại thông tin hiển thị

            # Reset camera và ảnh đã chụp
            self.camera_label.config(image='')
            if hasattr(self, 'captured_image'):
                del self.captured_image

            messagebox.showinfo("Thành công", "Đã cập nhật thông tin nhân viên!")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể cập nhật: {str(e)}")
            self.conn.rollback()

    def load_employee_data(self):
        """Tải danh sách nhân viên từ database và kiểm tra file ảnh"""
        try:
            # Xóa dữ liệu cũ
            for item in self.employee_tree.get_children():
                self.employee_tree.delete(item)

            # Lấy dữ liệu từ database
            self.cursor.execute("SELECT id, name, image_path FROM employees ORDER BY name")
            employees = self.cursor.fetchall()

            # Thêm vào Treeview và kiểm tra file ảnh
            valid_employees = []
            for emp in employees:
                emp_id, name, image_path = emp
                if os.path.exists(image_path):
                    self.employee_tree.insert("", "end", values=(emp_id, name))
                    valid_employees.append(emp)
                else:
                    # Xóa nhân viên không có ảnh
                    self.cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
                    self.conn.commit()

            # Nếu có nhân viên bị xóa do không có ảnh
            if len(valid_employees) != len(employees):
                messagebox.showwarning("Cảnh báo", "Đã xóa một số nhân viên không có ảnh hợp lệ")

            # Reset trạng thái nút
            self.btn_update.config(state="disabled")
            self.btn_register.config(state="normal")
            self.current_employee_id = None
            self.employee_name_label.config(text="Chọn nhân viên để xem thông tin")
            self.employee_image_label.config(image='', text="")
            self.entry_name.delete(0, tk.END)
            self.entry_search.delete(0, tk.END)  # Xóa nội dung tìm kiếm

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải danh sách nhân viên: {str(e)}")

    def load_attendance_data(self):
        """Tải dữ liệu chấm công từ database"""
        try:
            # Xóa dữ liệu cũ
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Lấy dữ liệu từ database (kết hợp với bảng employees)
            self.cursor.execute('''
                SELECT a.id, e.name, a.date, a.time_in, a.time_out, a.status 
                FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                ORDER BY a.date DESC, a.time_in DESC
            ''')
            records = self.cursor.fetchall()

            # Thêm vào Treeview
            for row in records:
                self.tree.insert("", "end", values=row)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải dữ liệu: {str(e)}")

    def delete_employee(self):
        """Xóa nhân viên"""
        selected = self.employee_tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn nhân viên cần xóa")
            return

        # Xác nhận trước khi xóa
        item = self.employee_tree.item(selected[0])
        emp_id, name = item['values']

        if not messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa nhân viên {name}?"):
            return

        try:
            # Lấy đường dẫn ảnh để xóa
            self.cursor.execute("SELECT image_path FROM employees WHERE id=?", (emp_id,))
            result = self.cursor.fetchone()

            if result:
                img_path = result[0]
                # Xóa từ database
                self.cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
                # Xóa dữ liệu chấm công liên quan
                self.cursor.execute("DELETE FROM attendance WHERE employee_id=?", (emp_id,))
                self.conn.commit()

                # Xóa file ảnh
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except Exception as e:
                        print(f"Không thể xóa file ảnh: {str(e)}")

            # Làm mới danh sách
            self.load_employee_data()
            self.load_attendance_data()

            messagebox.showinfo("Thành công", f"Đã xóa nhân viên {name}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa nhân viên: {str(e)}")

    def export_to_excel(self):
        """Xuất báo cáo ra file Excel"""
        date_from = self.cal_from.get_date()
        date_to = self.cal_to.get_date()

        try:
            # Lấy dữ liệu từ database (kết hợp với bảng employees)
            self.cursor.execute('''
                SELECT a.id, e.name, a.date, a.time_in, a.time_out, a.status 
                FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                WHERE a.date BETWEEN ? AND ?
                ORDER BY a.date, a.time_in
            ''', (date_from, date_to))
            records = self.cursor.fetchall()

            if not records:
                messagebox.showwarning("Cảnh báo", "Không có dữ liệu trong khoảng thời gian này")
                return

            # Tạo DataFrame và xuất Excel
            df = pd.DataFrame(records, columns=["ID", "Tên", "Ngày", "Giờ vào", "Giờ ra", "Trạng thái"])
            filename = f"attendance_{date_from}_{date_to}.xlsx"
            filepath = os.path.join(self.EXPORT_DIR, filename)

            # Sử dụng engine openpyxl
            df.to_excel(filepath, index=False, engine='openpyxl')

            messagebox.showinfo("Thành công", f"Đã xuất báo cáo thành công:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất báo cáo: {str(e)}")

    def __del__(self):
        """Dọn dẹp khi đóng ứng dụng"""
        if hasattr(self, 'cap') and self.cap and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'conn'):
            self.conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = AdminGUI(root)
    root.mainloop()
