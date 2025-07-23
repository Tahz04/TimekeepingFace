import tkinter as tk
from tkinter import messagebox, simpledialog
from controllers.admin_controller import AdminController
from controllers.employee_controller import EmployeeController
import bcrypt

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hệ thống chấm công khuôn mặt")
        self.setup_auth_ui()

    def setup_auth_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        lbl_title = tk.Label(self.root, text="HỆ THỐNG CHẤM CÔNG", font=("Arial", 16, "bold"))
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
            height=3,
            font=("Arial", 10, "bold")
        )
        btn_employee.grid(row=0, column=0, padx=10)

        btn_admin = tk.Button(
            frame,
            text="QUẢN TRỊ",
            command=self.authenticate_admin,
            bg="#FF9800",
            fg="white",
            width=15,
            height=3,
            font=("Arial", 10, "bold")
        )
        btn_admin.grid(row=0, column=1, padx=10)

    def open_employee_mode(self):
        try:
            self.root.withdraw()
            employee_window = tk.Toplevel()
            employee_window.protocol("WM_DELETE_WINDOW", lambda: self.on_subwindow_close(employee_window))
            EmployeeController(employee_window, lambda: self.on_subwindow_close(employee_window))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở chế độ nhân viên: {str(e)}")
            self.root.deiconify()

    def authenticate_admin(self):
        password = simpledialog.askstring("Xác thực", "Nhập mật khẩu quản trị:", show='*')
        stored_hash = b'$2a$12$BhtYu/sFAT9z1Sm0bxzyce9NghWmUocNGHHw7LKQQd3hqRjXXmdiq'  # Hash của "admin123"

        if password and bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            try:
                self.root.withdraw()
                admin_window = tk.Toplevel()
                admin_window.protocol("WM_DELETE_WINDOW", lambda: self.on_subwindow_close(admin_window))
                AdminController(admin_window)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể mở chế độ quản trị: {str(e)}")
                self.root.deiconify()
        elif password:
            messagebox.showerror("Lỗi", "Mật khẩu không đúng!")

    def on_subwindow_close(self, window):
        window.destroy()
        self.root.deiconify()

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
