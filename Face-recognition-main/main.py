import tkinter as tk
from tkinter import messagebox, simpledialog
from admin_gui import AdminGUI
from employee_gui import EmployeeGUI
import bcrypt


class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Attendance System")
        self.setup_auth_ui()

    def setup_auth_ui(self):
        # Xóa các widget cũ nếu có
        for widget in self.root.winfo_children():
            widget.destroy()

        lbl_title = tk.Label(self.root, text="HỆ THỐNG CHẤM CÔNG", font=("Arial", 16))
        lbl_title.pack(pady=20)

        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        btn_employee = tk.Button(
            frame,
            text="NHÂN VIÊN",
            command=self.open_employee_mode,
            bg="#2196F3",
            fg="white",
            width=15,
            height=3
        )
        btn_employee.grid(row=0, column=0, padx=10)

        btn_admin = tk.Button(
            frame,
            text="QUẢN TRỊ",
            command=self.authenticate_admin,
            bg="#FF9800",
            fg="white",
            width=15,
            height=3
        )
        btn_admin.grid(row=0, column=1, padx=10)

    def open_employee_mode(self):
        """Mở giao diện nhân viên"""
        self.root.withdraw()
        employee_window = tk.Toplevel()
        employee_window.protocol("WM_DELETE_WINDOW", lambda: self.on_subwindow_close(employee_window))
        EmployeeGUI(employee_window, lambda: self.on_subwindow_close(employee_window))

    def authenticate_admin(self):
        """Xác thực admin"""
        password = simpledialog.askstring("Xác thực", "Nhập mật khẩu quản trị:", show='*')
        stored_hash = b'$2a$12$BhtYu/sFAT9z1Sm0bxzyce9NghWmUocNGHHw7LKQQd3hqRjXXmdiq'  # Hash của "admin123"

        if password and bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            self.root.withdraw()
            admin_window = tk.Toplevel()
            admin_window.protocol("WM_DELETE_WINDOW", lambda: self.on_subwindow_close(admin_window))
            AdminGUI(admin_window)
        elif password:
            messagebox.showerror("Lỗi", "Mật khẩu không đúng!")

    def on_subwindow_close(self, window):
        """Xử lý khi đóng cửa sổ con"""
        window.destroy()
        self.root.deiconify()


if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()