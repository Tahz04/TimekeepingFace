import os
import cv2
import face_recognition
import pandas as pd
import tkinter as tk
from tkinter import messagebox, END
from datetime import datetime

from models.admin_model import AdminModel
from views.admin_view import AdminView


class AdminController:
    def __init__(self, root):
        self.view = AdminView(root)
        self.model = AdminModel()

        # Biến tạm
        self.captured_image = None
        self.cap = None
        self.current_employee_id = None

        # Thiết lập sự kiện
        self.setup_events()

        # Tải dữ liệu ban đầu
        self.load_employee_data()
        self.load_attendance_data()

    def setup_events(self):
        """Thiết lập các sự kiện"""
        self.view.entry_search.bind("<KeyRelease>", self.search_employee)
        self.view.btn_search.config(command=self.search_employee)
        self.view.btn_refresh.config(command=self.load_employee_data)
        self.view.btn_delete.config(command=self.delete_employee)
        self.view.btn_toggle_cam.config(command=self.toggle_camera)
        self.view.btn_capture.config(command=self.capture_image)
        self.view.btn_register.config(command=self.register_employee)
        self.view.btn_update.config(command=self.update_employee)
        self.view.employee_tree.bind("<<TreeviewSelect>>", self.on_employee_selected)
        self.view.btn_refresh_attendance.config(command=self.load_attendance_data)
        self.view.btn_export.config(command=self.export_to_excel)

    def load_employee_data(self):
        """Tải danh sách nhân viên"""
        for item in self.view.employee_tree.get_children():
            self.view.employee_tree.delete(item)

        employees = self.model.get_employees()
        for emp in employees:
            self.view.employee_tree.insert("", "end", values=emp)

        self.reset_employee_form()

    def search_employee(self, event=None):
        """Tìm kiếm nhân viên"""
        search_term = self.view.entry_search.get().strip()
        for item in self.view.employee_tree.get_children():
            self.view.employee_tree.delete(item)

        employees = self.model.search_employees(search_term)
        for emp in employees:
            self.view.employee_tree.insert("", "end", values=emp)

    def on_employee_selected(self, event):
        """Xử lý khi chọn nhân viên"""
        selected = self.view.employee_tree.selection()
        if not selected:
            return

        item = self.view.employee_tree.item(selected[0])
        emp_id, name = item['values']
        self.current_employee_id = emp_id

        # Hiển thị thông tin nhân viên
        details = self.model.get_employee_details(emp_id)
        if details:
            name, image_path = details
            self.view.employee_name_label.config(text=name)
            self.view.entry_name.delete(0, END)
            self.view.entry_name.insert(0, name)
            self.view.display_employee_image(image_path)

            # Kích hoạt nút cập nhật
            self.view.btn_update.config(state="normal")
            self.view.btn_register.config(state="disabled")

    def toggle_camera(self):
        """Bật/tắt camera"""
        if self.view.camera_running:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        """Bật camera"""
        try:
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()

            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("Không thể mở camera")

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.view.image_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.view.image_height)

            self.view.camera_running = True
            self.view.btn_toggle_cam.config(text="Tắt Camera", bg="#F44336")
            self.view.btn_capture.config(state="normal")
            self.update_camera()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể khởi động camera: {str(e)}")
            self.stop_camera()

    def check_single_face(self, frame):
        """Kiểm tra chỉ có 1 khuôn mặt trong ảnh"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        return len(face_locations) == 1

    def update_camera(self):
        """Cập nhật hình ảnh từ camera"""
        if self.view.camera_running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.flip(frame, 1)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Phát hiện khuôn mặt
                    face_locations = face_recognition.face_locations(rgb_frame)
                    face_count = len(face_locations)

                    # Hiển thị cảnh báo nếu có nhiều hơn 1 khuôn mặt
                    if face_count > 1:
                        cv2.putText(frame, "WARNING: Multiple faces detected!", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                    for (top, right, bottom, left) in face_locations:
                        color = (0, 255, 0) if face_count == 1 else (0, 0, 255)
                        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

                    self.view.display_camera_image(frame)

                self.view.camera_label.after(10, self.update_camera)
            except Exception:
                self.stop_camera()

    def stop_camera(self):
        """Tắt camera"""
        self.view.camera_running = False
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
            self.cap = None

        self.view.btn_toggle_cam.config(text="Bật Camera", bg="#2196F3")
        self.view.btn_capture.config(state="disabled")
        self.view.camera_label.config(image='')

    def capture_image(self):
        """Chụp ảnh từ camera"""
        if not self.view.camera_running:
            messagebox.showerror("Lỗi", "Vui lòng bật camera trước khi chụp ảnh")
            return

        try:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)

                # Kiểm tra số lượng khuôn mặt
                if not self.check_single_face(frame):
                    messagebox.showerror("Lỗi", "Vui lòng đảm bảo chỉ có 1 khuôn mặt trong khung hình")
                    return

                self.captured_image = frame
                self.stop_camera()
                self.view.display_camera_image(frame)
                messagebox.showinfo("Thành công", "Đã chụp ảnh thành công!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể chụp ảnh: {str(e)}")
            self.stop_camera()

    def register_employee(self):
        """Đăng ký nhân viên mới"""
        name = self.view.entry_name.get().strip()
        if not name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên nhân viên")
            return

        if not hasattr(self, 'captured_image'):
            messagebox.showerror("Lỗi", "Vui lòng chụp ảnh trước khi đăng ký")
            return

        try:
            # Kiểm tra lại số lượng khuôn mặt trong ảnh đã chụp
            if not self.check_single_face(self.captured_image):
                messagebox.showerror("Lỗi", "Ảnh đã chụp không có hoặc có nhiều hơn 1 khuôn mặt!")
                return

            filename = f"{name.replace(' ', '_')}.jpg"
            filepath = os.path.join(self.model.DATA_DIR, filename)

            if os.path.exists(filepath):
                messagebox.showerror("Lỗi", "File ảnh đã tồn tại!")
                return

            cv2.imwrite(filepath, self.captured_image)

            img = face_recognition.load_image_file(filepath)
            encodings = face_recognition.face_encodings(img)

            if not encodings:
                os.remove(filepath)
                messagebox.showerror("Lỗi", "Không phát hiện khuôn mặt trong ảnh!")
                return

            if not self.model.register_employee(name, filepath):
                messagebox.showerror("Lỗi", "Nhân viên đã tồn tại!")
                return

            # Reset form
            self.view.entry_name.delete(0, END)
            self.view.camera_label.config(image='')
            del self.captured_image

            # Làm mới danh sách
            self.load_employee_data()
            messagebox.showinfo("Thành công", f"Đã đăng ký nhân viên {name}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi đăng ký: {str(e)}")

    def update_employee(self):
        """Cập nhật thông tin nhân viên"""
        if not self.current_employee_id:
            messagebox.showerror("Lỗi", "Vui lòng chọn nhân viên cần cập nhật")
            return

        name = self.view.entry_name.get().strip()
        if not name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên nhân viên")
            return

        try:
            if hasattr(self, 'captured_image') and self.captured_image is not None:
                # Kiểm tra số lượng khuôn mặt trong ảnh đã chụp
                if not self.check_single_face(self.captured_image):
                    messagebox.showerror("Lỗi", "Ảnh đã chụp không có hoặc có nhiều hơn 1 khuôn mặt!")
                    return

                filename = f"{name.replace(' ', '_')}.jpg"
                new_img_path = os.path.join(self.model.DATA_DIR, filename)
                cv2.imwrite(new_img_path, self.captured_image)
                self.model.update_employee(self.current_employee_id, name, new_img_path)
            else:
                self.model.update_employee(self.current_employee_id, name)

            # Làm mới danh sách
            self.load_employee_data()
            self.on_employee_selected(None)

            # Reset camera và ảnh đã chụp
            self.view.camera_label.config(image='')
            if hasattr(self, 'captured_image'):
                del self.captured_image

            messagebox.showinfo("Thành công", "Đã cập nhật thông tin nhân viên!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể cập nhật: {str(e)}")

    def delete_employee(self):
        """Xóa nhân viên"""
        selected = self.view.employee_tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn nhân viên cần xóa")
            return

        item = self.view.employee_tree.item(selected[0])
        emp_id, name = item['values']

        if not messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa nhân viên {name}?"):
            return

        if self.model.delete_employee(emp_id):
            self.load_employee_data()
            self.load_attendance_data()
            messagebox.showinfo("Thành công", f"Đã xóa nhân viên {name}")
        else:
            messagebox.showerror("Lỗi", "Không thể xóa nhân viên")

    def load_attendance_data(self):
        """Tải dữ liệu chấm công"""
        for item in self.view.tree.get_children():
            self.view.tree.delete(item)

        records = self.model.get_attendance_data()
        for row in records:
            self.view.tree.insert("", "end", values=row)

    def export_to_excel(self):
        """Xuất báo cáo ra Excel"""
        date_from = self.view.cal_from.get_date()
        date_to = self.view.cal_to.get_date()

        records = self.model.export_attendance(date_from, date_to)
        if not records:
            messagebox.showwarning("Cảnh báo", "Không có dữ liệu trong khoảng thời gian này")
            return

        try:
            df = pd.DataFrame(records, columns=["ID", "Tên", "Ngày", "Giờ vào", "Giờ ra", "Trạng thái"])
            filename = f"attendance_{date_from}_{date_to}.xlsx"
            filepath = os.path.join(self.model.EXPORT_DIR, filename)

            df.to_excel(filepath, index=False, engine='openpyxl')
            messagebox.showinfo("Thành công", f"Đã xuất báo cáo thành công:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất báo cáo: {str(e)}")

    def reset_employee_form(self):
        """Reset form nhân viên"""
        self.view.btn_update.config(state="disabled")
        self.view.btn_register.config(state="normal")
        self.current_employee_id = None
        self.view.employee_name_label.config(text="Chọn nhân viên để xem thông tin")
        self.view.employee_image_label.config(image='', text="")
        self.view.entry_name.delete(0, END)
        self.view.entry_search.delete(0, END)

    def __del__(self):
        """Dọn dẹp khi đóng ứng dụng"""
        if hasattr(self, 'cap') and self.cap and self.cap.isOpened():
            self.cap.release()
        self.model.close()