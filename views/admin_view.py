import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from PIL import Image, ImageTk
import cv2
import os


class AdminView:
    def __init__(self, root):
        self.root = root
        self.root.title("Quản trị hệ thống chấm công")
        self.image_width = 400
        self.image_height = 300
        self.camera_running = False
        self.setup_ui()

    def setup_ui(self):
        tab_control = ttk.Notebook(self.root)

        # Tab quản lý nhân viên
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
        # Frame danh sách nhân viên
        list_frame = tk.Frame(parent)
        list_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Thanh tìm kiếm
        search_frame = tk.Frame(list_frame)
        search_frame.pack(fill="x", pady=5)

        lbl_search = tk.Label(search_frame, text="Tìm kiếm:")
        lbl_search.pack(side="left", padx=5)

        self.entry_search = tk.Entry(search_frame, width=30)
        self.entry_search.pack(side="left", padx=5)

        # Thêm nút tìm kiếm
        self.btn_search = tk.Button(
            search_frame,
            text="Tìm",
            bg="#2196F3",
            fg="white",
            width=5
        )
        self.btn_search.pack(side="left", padx=5)

        # Treeview nhân viên
        self.employee_tree = ttk.Treeview(list_frame, columns=("id", "name"), show="headings")
        self.employee_tree.heading("id", text="ID")
        self.employee_tree.heading("name", text="Tên nhân viên")
        self.employee_tree.column("id", width=50, anchor="center")
        self.employee_tree.column("name", width=250, anchor="w")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.employee_tree.yview)
        self.employee_tree.configure(yscrollcommand=scrollbar.set)
        self.employee_tree.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Frame nút chức năng
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(side="bottom", pady=5)

        self.btn_refresh = tk.Button(
            btn_frame,
            text="Làm mới",
            bg="#607D8B",
            fg="white",
            width=10
        )
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_delete = tk.Button(
            btn_frame,
            text="Xóa",
            bg="#F44336",
            fg="white",
            width=10
        )
        self.btn_delete.pack(side="left", padx=5)

        # Frame chi tiết nhân viên
        detail_frame = tk.Frame(parent)
        detail_frame.pack(side="right", fill="both", padx=5, pady=5)

        # Hiển thị thông tin nhân viên
        self.info_frame = tk.LabelFrame(
            detail_frame,
            text="Thông tin nhân viên",
            width=self.image_width,
            height=self.image_height
        )
        self.info_frame.pack(fill="both", expand=True, pady=5)
        self.info_frame.pack_propagate(False)

        self.employee_image_label = tk.Label(self.info_frame)
        self.employee_image_label.pack(expand=True)

        self.employee_name_label = tk.Label(
            self.info_frame,
            text="Chọn nhân viên để xem thông tin",
            font=('Arial', 12)
        )
        self.employee_name_label.pack(side="bottom", pady=5)

        # Frame đăng ký/cập nhật
        register_frame = tk.LabelFrame(detail_frame, text="Đăng ký/Cập nhật nhân viên")
        register_frame.pack(fill="both", expand=True, pady=5)

        lbl_name = tk.Label(register_frame, text="Tên nhân viên:")
        lbl_name.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.entry_name = tk.Entry(register_frame, width=30)
        self.entry_name.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Frame camera
        self.camera_frame = tk.LabelFrame(
            register_frame,
            text="Camera",
            width=self.image_width,
            height=self.image_height
        )
        self.camera_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        self.camera_frame.grid_propagate(False)

        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(expand=True)

        # Nút điều khiển camera
        btn_camera_frame = tk.Frame(register_frame)
        btn_camera_frame.grid(row=2, column=0, columnspan=2, pady=5)

        self.btn_toggle_cam = tk.Button(
            btn_camera_frame,
            text="Bật Camera",
            bg="#2196F3",
            fg="white",
            width=15
        )
        self.btn_toggle_cam.pack(side="left", padx=5)

        self.btn_capture = tk.Button(
            btn_camera_frame,
            text="Chụp Ảnh",
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
            bg="#FF9800",
            fg="white",
            width=20
        )
        self.btn_register.grid(row=3, column=0, columnspan=2, pady=10)

        self.btn_update = tk.Button(
            register_frame,
            text="Cập nhật Nhân viên",
            bg="#9C27B0",
            fg="white",
            width=20,
            state="disabled"
        )
        self.btn_update.grid(row=4, column=0, columnspan=2, pady=5)

    def setup_manage_tab(self, parent):
        # Treeview chấm công
        self.tree = ttk.Treeview(
            parent,
            columns=("id", "name", "date", "time_in", "time_out", "status"),
            show="headings"
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Tên nhân viên")
        self.tree.heading("date", text="Ngày")
        self.tree.heading("time_in", text="Giờ vào")
        self.tree.heading("time_out", text="Giờ ra")
        self.tree.heading("status", text="Trạng thái")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("name", width=150, anchor="w")
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("time_in", width=100, anchor="center")
        self.tree.column("time_out", width=100, anchor="center")
        self.tree.column("status", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Nút làm mới
        self.btn_refresh_attendance = tk.Button(
            parent,
            text="Làm mới dữ liệu",
            bg="#607D8B",
            fg="white"
        )
        self.btn_refresh_attendance.pack(side="bottom", pady=5)

    def setup_export_tab(self, parent):
        # Chọn ngày bắt đầu/kết thúc
        lbl_from = tk.Label(parent, text="Từ ngày:")
        lbl_from.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.cal_from = DateEntry(parent, date_pattern='yyyy-mm-dd')
        self.cal_from.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        lbl_to = tk.Label(parent, text="Đến ngày:")
        lbl_to.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self.cal_to = DateEntry(parent, date_pattern='yyyy-mm-dd')
        self.cal_to.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Nút xuất báo cáo
        self.btn_export = tk.Button(
            parent,
            text="Xuất Excel",
            bg="#FF9800",
            fg="white",
            width=20
        )
        self.btn_export.grid(row=2, column=0, columnspan=2, pady=10)

    def display_employee_image(self, image_path):
        """Hiển thị ảnh nhân viên"""
        try:
            if os.path.exists(image_path):
                img = Image.open(image_path)
                img.thumbnail((self.image_width, self.image_height))
                photo = ImageTk.PhotoImage(img)
                self.employee_image_label.config(image=photo)
                self.employee_image_label.image = photo
            else:
                self.employee_image_label.config(image='', text="Không tìm thấy ảnh")
        except Exception:
            self.employee_image_label.config(image='', text="Lỗi khi tải ảnh")

    def display_camera_image(self, frame):
        """Hiển thị ảnh từ camera"""
        if frame is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            img.thumbnail((self.image_width, self.image_height))
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.imgtk = imgtk
            self.camera_label.config(image=imgtk)