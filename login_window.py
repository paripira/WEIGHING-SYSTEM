# File: login_window.py (Versi Baru dengan Verifikasi Database)

from PySide6.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from database import verify_user, init_db # Import fungsi baru

class LoginWindow(QWidget):
    login_successful = Signal(str)

    def __init__(self):
        super().__init__()
        self.db_conn = init_db() # Buka koneksi DB
        
        self.setWindowTitle("WAIO System - Login"); self.setGeometry(0, 0, 400, 250)
        self.setStyleSheet("""
            QWidget { background-color: #1A202C; color: #E2E8F0; } QLabel { font-size: 10pt; } QLineEdit { background-color: #2D3748; border: 1px solid #4A5568; border-radius: 4px; padding: 8px; font-size: 11pt; } QPushButton { background-color: #38B2AC; color: white; padding: 12px; border-radius: 4px; font-size: 11pt; font-weight: bold; } QPushButton:hover { background-color: #319795; }
        """)
        main_layout = QVBoxLayout(self); main_layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("Login to Weighing System"); title.setFont(QFont("Arial", 16, QFont.Weight.Bold)); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.username_input = QLineEdit(); self.username_input.setPlaceholderText("Enter username")
        self.password_input = QLineEdit(); self.password_input.setPlaceholderText("Enter password"); self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_button = QPushButton("Login")
        main_layout.addWidget(title); main_layout.addSpacing(20); main_layout.addWidget(QLabel("Username:")); main_layout.addWidget(self.username_input); main_layout.addSpacing(10); main_layout.addWidget(QLabel("Password:")); main_layout.addWidget(self.password_input); main_layout.addSpacing(20); main_layout.addWidget(self.login_button)
        self.login_button.clicked.connect(self.check_login); self.password_input.returnPressed.connect(self.check_login)

    def check_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        # Ganti pengecekan hardcoded dengan verifikasi ke database
        if verify_user(self.db_conn, username, password):
            print(f"Login berhasil untuk user: {username}")
            self.login_successful.emit(username)
            self.close()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
            
    def closeEvent(self, event):
        if self.db_conn: self.db_conn.close()
        event.accept()