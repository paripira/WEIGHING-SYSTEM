from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, QTabWidget, QLineEdit, QComboBox, QMessageBox, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QDialog, QDialogButtonBox, QApplication, QHBoxLayout)
from PySide6.QtCore import Qt
import json
from database import get_all_users, add_user, delete_user

CONFIG_FILE = "config.json"

class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Add New User")
        layout = QVBoxLayout(self); form = QFormLayout()
        self.username_input = QLineEdit(); self.password_input = QLineEdit(); self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.role_combo = QComboBox(); self.role_combo.addItems(["Administrator", "Operator"])
        form.addRow("Username:", self.username_input); form.addRow("Password:", self.password_input); form.addRow("Role:", self.role_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addLayout(form); layout.addWidget(buttons)
    def get_data(self): return {"username": self.username_input.text().strip(), "password": self.password_input.text(), "role": self.role_combo.currentText()}

class SettingsWindow(QWidget):
    def __init__(self, db_conn):
        super().__init__()
        self.db_conn = db_conn
        self.setWindowTitle("Settings"); self.setGeometry(200, 200, 600, 400)
        self.setStyleSheet("""
            QWidget { background-color: #2D3748; color: #E2E8F0; } QLabel { font-weight: bold; } QLineEdit, QComboBox { background-color: #1A202C; border: 1px solid #4A5568; border-radius: 4px; padding: 6px; } QPushButton { background-color: #38B2AC; border: none; padding: 10px; border-radius: 4px; font-weight: bold; color: white; } QPushButton:hover { background-color: #319795; } QTabWidget::pane { border: 1px solid #4A5568; } QTabBar::tab { background: #2D3748; padding: 10px; border-top-left-radius: 4px; border-top-right-radius: 4px; } QTabBar::tab:selected { background: #38B2AC; color: white; } QTableWidget { background-color: #1A202C; } QPushButton#delete_button { background-color: #E53E3E; } QPushButton#delete_button:hover { background-color: #C53030; }
        """)
        main_layout = QVBoxLayout(self); self.tabs = QTabWidget()
        self.create_connection_tab(); self.create_general_tab(); self.create_users_tab()
        main_layout.addWidget(self.tabs)

    def create_connection_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); form = QFormLayout()
        self.port_input = QLineEdit(); self.baudrate_combo = QComboBox(); self.baudrate_combo.addItems(["9600", "4800", "19200", "38400", "57600", "115200"])
        form.addRow("COM Port :", self.port_input); form.addRow("Baud Rate:", self.baudrate_combo)
        save_button = QPushButton("Save Connection Settings"); save_button.setToolTip("Aplikasi perlu dimulai ulang agar pengaturan baru diterapkan."); save_button.clicked.connect(self.save_connection_settings)
        layout.addLayout(form); layout.addStretch(); layout.addWidget(save_button)
        self.tabs.addTab(tab, "Connection"); self.load_connection_settings()
        
    def create_general_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.addWidget(QLabel("General settings will be available in a future update."))
        self.tabs.addTab(tab, "General")
        
    def create_users_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        self.users_table = QTableWidget(); self.users_table.setColumnCount(3); self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Role"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        button_layout = QHBoxLayout(); add_button = QPushButton("Add User"); delete_button = QPushButton("Delete User", objectName="delete_button")
        add_button.clicked.connect(self.add_user_dialog); delete_button.clicked.connect(self.delete_user_action)
        button_layout.addStretch(); button_layout.addWidget(add_button); button_layout.addWidget(delete_button)
        layout.addWidget(self.users_table); layout.addLayout(button_layout)
        self.tabs.addTab(tab, "Users"); self.refresh_users_table()
    
    def refresh_users_table(self):
        users = get_all_users(self.db_conn)
        self.users_table.setRowCount(0); self.users_table.setRowCount(len(users))
        for row, user in enumerate(users):
            self.users_table.setItem(row, 0, QTableWidgetItem(str(user['id']))); self.users_table.setItem(row, 1, QTableWidgetItem(user['username'])); self.users_table.setItem(row, 2, QTableWidgetItem(user['role']))

    def add_user_dialog(self):
        dialog = AddUserDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['username'] or not data['password']: QMessageBox.warning(self, "Input Error", "Username and Password cannot be empty."); return
            if add_user(self.db_conn, data['username'], data['password'], data['role']): QMessageBox.information(self, "Success", "New user added successfully."); self.refresh_users_table()
            else: QMessageBox.critical(self, "Error", "Username already exists.")
                
    def delete_user_action(self):
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows: QMessageBox.warning(self, "Selection Error", "Please select a user to delete."); return
        user_id = self.users_table.item(selected_rows[0].row(), 0).text(); username = self.users_table.item(selected_rows[0].row(), 1).text()
        if username == 'admin': QMessageBox.critical(self, "Permission Denied", "The default 'admin' user cannot be deleted."); return
        reply = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete user '{username}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if delete_user(self.db_conn, int(user_id)): QMessageBox.information(self, "Success", f"User '{username}' deleted."); self.refresh_users_table()
            else: QMessageBox.critical(self, "Error", "Failed to delete user.")

    def load_connection_settings(self):
        try:
            with open(CONFIG_FILE, 'r') as f: config = json.load(f)
            self.port_input.setText(config.get("port", "COM1")); self.baudrate_combo.setCurrentText(str(config.get("baudrate", 9600)))
        except FileNotFoundError: self.port_input.setText("COM1"); self.baudrate_combo.setCurrentText("9600")

    def save_connection_settings(self):
        config = {"port": self.port_input.text().strip().upper(), "baudrate": int(self.baudrate_combo.currentText())}
        with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)
        QMessageBox.information(self, "Settings Saved", "Pengaturan telah disimpan.\nAplikasi akan ditutup. Silakan buka kembali untuk menerapkan perubahan.")
        QApplication.instance().quit()