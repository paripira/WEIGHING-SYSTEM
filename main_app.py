# File: main_app.py (Final dengan Pengaturan Dinamis dari config.json)

import sys
import time
import random
from datetime import datetime
import re
import serial
from collections import deque 
import json # <-- DITAMBAHKAN: Untuk membaca file konfigurasi

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, 
    QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QFrame, QMessageBox, QStatusBar,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView
)
from PySide6.QtCore import QThread, Qt, Signal, QObject, QTimer
from PySide6.QtGui import QFont, QColor, QBrush, QDoubleValidator, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog

from database import init_db, create_first_weigh, complete_second_weigh, get_filtered_transactions, find_pending_by_plate_number, get_transaction_by_id, generate_transaction_id
from report_window import ReportWindow
from login_window import LoginWindow
from settings_window import SettingsWindow 

STABILITY_WINDOW_SIZE = 5
STABILITY_TOLERANCE = 2.0
CONFIG_FILE = "config.json" # <-- DITAMBAHKAN: Nama file konfigurasi

# --- DITAMBAHKAN: Fungsi untuk memuat pengaturan dari file ---
def load_config():
    """Membaca file config.json dan mengembalikan pengaturannya."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Pastikan nilai baudrate adalah integer
            config['baudrate'] = int(config.get('baudrate', 9600))
            return config
    except (FileNotFoundError, json.JSONDecodeError):
        # Jika file tidak ada atau rusak, kembalikan pengaturan default
        return {"port": "COM1", "baudrate": 9600}
# -------------------------------------------------------------

STYLESHEET = """
    #main_window, #main_widget { background-color: #1A2C2C; } 
    QFrame#card { background-color: #2D3748; border-radius: 8px; } 
    QLabel { color: #E2E8F0; font-size: 10pt; } 
    QLabel#header { font-size: 14pt; font-weight: bold; } 
    QLabel#live_weight_label { color: #A0AEC0; font-size: 10pt; font-weight: normal; }
    QLabel#live_weight_display { color: #38B2AC; font-size: 28pt; font-weight: bold; }
    QLineEdit#potongan_input { color: #F6E05E; }
    QLineEdit#total_bersih_display { color: #48BB78; }
    QLabel#transaction_id_label { color: #38B2AC; font-size: 11pt; font-weight: bold; }
    QLineEdit { background-color: #1A202C; color: #E2E8F0; border: 1px solid #4A5568; border-radius: 4px; padding: 6px; font-size: 10pt; } 
    QPushButton#input_button { background-color: #38B2AC; color: white; padding: 12px; border-radius: 4px; font-size: 12pt; font-weight: bold; } 
    QPushButton#input_button:hover { background-color: #319795; }
    QPushButton#input_button:disabled { background-color: #4A5568; }
    QPushButton#nav_button { background: none; border: none; font-size: 10pt; color: #A0AEC0; font-weight: bold; padding: 10px; }
    QPushButton#nav_button:hover { color: white; }
    QPushButton#clear_button { background-color: #E53E3E; color: white; font-size: 9pt; font-weight: bold; padding: 5px 10px; border-radius: 4px; }
    QPushButton#clear_button:hover { background-color: #C53030; }
    QPushButton#print_button { background-color: #3182CE; color: white; font-size: 9pt; font-weight: bold; padding: 5px 10px; border-radius: 4px; }
    QPushButton#print_button:hover { background-color: #2B6CB0; }
    QStatusBar { background-color: #2D3748; color: #A0AEC0; font-size: 9pt; }
    QTableWidget { background-color: #2D3748; border-radius: 8px; border: 1px solid #4A5568; gridline-color: #4A5568; }
    QTableWidget::item { padding: 5px; }
    QHeaderView::section { background-color: #1A202C; color: #E2E8F0; padding: 8px; border-bottom: 1px solid #4A5568; border-right: 1px solid #4A5568; font-size: 9pt; font-weight: bold; }
    QMessageBox { background-color: #2D3748; }
    QMessageBox QLabel { color: #E2E8F0; font-size: 10pt; font-weight: normal; }
    QMessageBox QPushButton { background-color: #38B2AC; color: white; border: none; padding: 8px 24px; border-radius: 4px; font-weight: bold; }
    QMessageBox QPushButton:hover { background-color: #319795; }
"""

class TimbanganSimulatorWorker(QObject):
    data_terbaca = Signal(float)
    def __init__(self): super().__init__(); self.is_running = True; self.base_weight = 12500.0; self.stability_counter = 0
    def run(self):
        while self.is_running:
            if self.stability_counter < 10: simulated_weight = self.base_weight + random.uniform(-1.5, 1.5)
            else: simulated_weight = self.base_weight + random.uniform(-5.0, 5.0)
            self.data_terbaca.emit(simulated_weight); self.stability_counter = (self.stability_counter + 1) % 16; time.sleep(0.5)
    def stop(self): self.is_running = False

class TimbanganSerialWorker(QObject):
    data_terbaca = Signal(float)
    error_terjadi = Signal(str)
    def __init__(self, port, baudrate): super().__init__(); self.port = port; self.baudrate = baudrate; self.is_running = True; self.ser = None
    def run(self):
        try: self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
        except serial.SerialException as e: self.error_terjadi.emit(f"Gagal terhubung ke port {self.port}.\nPastikan kabel terhubung dan port sudah benar."); return
        while self.is_running and self.ser.isOpen():
            try:
                line = self.ser.readline()
                if line:
                    decoded_line = line.decode('utf-8', errors='ignore').strip(); match = re.search(r'[-+]?\d*\.\d+|\d+', decoded_line)
                    if match: self.data_terbaca.emit(float(match.group(0)))
            except serial.SerialException: self.error_terjadi.emit("Koneksi ke timbangan terputus."); break
            except Exception as e: print(f"Error saat membaca data: {e}")
        if self.ser and self.ser.isOpen(): self.ser.close()
    def stop(self): self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("main_window"); self.setWindowTitle("RTM - Weighing System"); self.setGeometry(100, 100, 1400, 800); self.setStyleSheet(STYLESHEET)
        self.db_conn = init_db()
        self.weight_readings = deque(maxlen=STABILITY_WINDOW_SIZE); self.is_stable = False
        self.report_win = None; self.settings_win = None
        self.last_selected_transaction_id = None
        main_widget = QWidget(objectName="main_widget"); self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget); main_layout.setSpacing(15); main_layout.setContentsMargins(15, 15, 15, 15)
        top_area_layout = QHBoxLayout()
        weight_card = QFrame(objectName="card")
        weight_card_layout = QGridLayout(weight_card)
        weight_card_layout.setContentsMargins(15, 15, 15, 15)
        self.live_weight_label = QLabel("Timbangan Saat Ini", objectName="live_weight_label")
        self.live_weight_display = QLabel("0.00", objectName="live_weight_display")
        self.stability_status_label = QLabel("CONNECTING...")
        self.stability_status_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #A0AEC0;")
        summary_display_style = "background-color: #1A202C; color: #E2E8F0; border: 1px solid #4A5568; border-radius: 4px; padding: 6px; font-size: 12pt; font-weight: bold;"
        self.display_gross = QLineEdit("0.0"); self.display_gross.setReadOnly(True); self.display_gross.setAlignment(Qt.AlignmentFlag.AlignRight); self.display_gross.setStyleSheet(summary_display_style)
        self.display_tare = QLineEdit("0.0"); self.display_tare.setReadOnly(True); self.display_tare.setAlignment(Qt.AlignmentFlag.AlignRight); self.display_tare.setStyleSheet(summary_display_style)
        self.display_net = QLineEdit("0.0"); self.display_net.setReadOnly(True); self.display_net.setAlignment(Qt.AlignmentFlag.AlignRight); self.display_net.setStyleSheet(summary_display_style)
        self.input_potongan = QLineEdit("0.0"); self.input_potongan.setValidator(QDoubleValidator()); self.input_potongan.setAlignment(Qt.AlignmentFlag.AlignRight); self.input_potongan.setObjectName("potongan_input"); self.input_potongan.setStyleSheet(summary_display_style + "color: #F6E05E;")
        self.display_total_bersih = QLineEdit("0.0"); self.display_total_bersih.setReadOnly(True); self.display_total_bersih.setAlignment(Qt.AlignmentFlag.AlignRight); self.display_total_bersih.setObjectName("total_bersih_display"); self.display_total_bersih.setStyleSheet(summary_display_style + "color: #48BB78; font-size: 14pt;")
        weight_card_layout.addWidget(self.live_weight_label, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter); weight_card_layout.addWidget(self.live_weight_display, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter); weight_card_layout.addWidget(self.stability_status_label, 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter); weight_card_layout.addWidget(QFrame(styleSheet="border-bottom: 1px solid #4A5568;"), 3, 0, 1, 2)
        summary_label_style = "font-size: 10pt; font-weight: bold; color: #A0AEC0;"
        label_gross = QLabel("Gross"); label_gross.setStyleSheet(summary_label_style); label_tare = QLabel("Tare"); label_tare.setStyleSheet(summary_label_style); label_net = QLabel("Net"); label_net.setStyleSheet(summary_label_style); label_potongan = QLabel("Deduction "); label_potongan.setStyleSheet(summary_label_style); label_total_bersih = QLabel("Total Bersih"); label_total_bersih.setStyleSheet(summary_label_style)
        weight_card_layout.addWidget(label_gross, 4, 0); weight_card_layout.addWidget(self.display_gross, 4, 1); weight_card_layout.addWidget(label_tare, 5, 0); weight_card_layout.addWidget(self.display_tare, 5, 1); weight_card_layout.addWidget(label_net, 6, 0); weight_card_layout.addWidget(self.display_net, 6, 1); weight_card_layout.addWidget(label_potongan, 7, 0); weight_card_layout.addWidget(self.input_potongan, 7, 1); weight_card_layout.addWidget(label_total_bersih, 8, 0); weight_card_layout.addWidget(self.display_total_bersih, 8, 1)
        input_card = QFrame(objectName="card")
        input_card_layout = QGridLayout(input_card)
        input_card_layout.setContentsMargins(20, 20, 20, 20)
        self.next_transaction_id_label = QLabel("Loading...", objectName="transaction_id_label")
        self.btn_clear = QPushButton("New Transaction", objectName="clear_button")
        self.btn_print = QPushButton("Print", objectName="print_button")
        top_right_buttons_layout = QHBoxLayout(); top_right_buttons_layout.addWidget(self.btn_print); top_right_buttons_layout.addWidget(self.btn_clear)
        self.input_nomor_kendaraan = QLineEdit(); self.input_nama_sopir = QLineEdit()
        self.input_jenis_barang = QLineEdit(); self.input_quantity = QLineEdit()
        self.input_asal = QLineEdit(); self.input_tujuan = QLineEdit()
        self.input_remake = QLineEdit()
        input_card_layout.addWidget(QLabel("Next Transaction ID:"), 0, 0); input_card_layout.addWidget(self.next_transaction_id_label, 0, 1); input_card_layout.addLayout(top_right_buttons_layout, 0, 3, alignment=Qt.AlignmentFlag.AlignRight)
        input_card_layout.addWidget(QLabel("Plate No.:"), 1, 0); input_card_layout.addWidget(self.input_nomor_kendaraan, 1, 1); input_card_layout.addWidget(QLabel("Driver Name:"), 1, 2); input_card_layout.addWidget(self.input_nama_sopir, 1, 3)
        input_card_layout.addWidget(QLabel("Goods Type:"), 2, 0); input_card_layout.addWidget(self.input_jenis_barang, 2, 1); input_card_layout.addWidget(QLabel("Quantity:"), 2, 2); input_card_layout.addWidget(self.input_quantity, 2, 3)
        input_card_layout.addWidget(QLabel("Goods Origin:"), 3, 0); input_card_layout.addWidget(self.input_asal, 3, 1); input_card_layout.addWidget(QLabel("Goods Destination:"), 3, 2); input_card_layout.addWidget(self.input_tujuan, 3, 3)
        input_card_layout.addWidget(QLabel("Remake:"), 4, 0); input_card_layout.addWidget(self.input_remake, 4, 1, 1, 3)
        self.btn_input = QPushButton("INPUT", objectName="input_button")
        input_card_layout.addWidget(self.btn_input, 5, 0, 1, 4)
        nav_layout = QVBoxLayout(); nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        for nav in ["REVIEW", "SETTINGS"]: btn = QPushButton(nav, objectName="nav_button"); btn.clicked.connect(self.open_report_window if nav == "REVIEW" else self.open_settings_window); nav_layout.addWidget(btn)
        top_area_layout.addWidget(weight_card, 2); top_area_layout.addWidget(input_card, 5); top_area_layout.addLayout(nav_layout, 1)
        bottom_area_card = QFrame(objectName="card"); bottom_area_layout = QVBoxLayout(bottom_area_card); history_label = QLabel("Today's History", objectName="header"); bottom_area_layout.addWidget(history_label); self.history_table = QTableWidget(); self.history_table.setColumnCount(12); headers = ["Transaction ID", "Date", "Plate No.", "Goods Type", "Origin", "Destination", "Status", "Gross", "Tare", "Net", "Quantity", "Remake"]; self.history_table.setHorizontalHeaderLabels(headers); header = self.history_table.horizontalHeader(); header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch); header.setSectionResizeMode(11, QHeaderView.ResizeMode.Stretch); self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.history_table.verticalHeader().setVisible(False); self.history_table.verticalHeader().setDefaultSectionSize(35); self.history_table.setAlternatingRowColors(True); bottom_area_layout.addWidget(self.history_table)
        main_layout.addLayout(top_area_layout, 1); main_layout.addWidget(bottom_area_card, 2)
        self.statusBar = QStatusBar(); self.setStatusBar(self.statusBar); self.status_datetime_label = QLabel(""); self.status_datetime_label.setStyleSheet("color: #A0AEC0; margin: 0 10px;"); self.statusBar.addPermanentWidget(self.status_datetime_label)
        self.setup_timbangan()
        self.btn_input.clicked.connect(self.proses_input_cerdas); self.btn_clear.clicked.connect(self.clear_form)
        self.btn_print.clicked.connect(self.print_selected_slip)
        self.input_potongan.textChanged.connect(self.recalculate_total_net)
        self.timer = QTimer(self); self.timer.setInterval(1000); self.timer.timeout.connect(self.update_datetime_status_bar); self.timer.start()
        self.update_datetime_status_bar(); self.history_table.cellClicked.connect(self.load_transaction_by_id); self.refresh_history_table(); self.update_next_transaction_id()

    # --- DIUBAH: Fungsi ini sekarang membaca dari config.json ---
    def setup_timbangan(self):
        self.thread = QThread()
        config = load_config() # Memuat pengaturan

        # --- PILIH MODE TIMBANGAN ---
        # Ganti variabel di bawah ini menjadi False untuk menggunakan timbangan fisik
        USE_SIMULATOR = False 

        if USE_SIMULATOR:
            self.worker = TimbanganSimulatorWorker()
            print(f">>> MENJALANKAN DALAM MODE SIMULATOR <<<")
        else:
            port = config.get("port", "COM1")
            baudrate = config.get("baudrate", 9600)
            self.worker = TimbanganSerialWorker(port=port, baudrate=baudrate)
            self.worker.error_terjadi.connect(self.tampilkan_error_koneksi)
            print(f">>> MENCOBA KONEKSI KE TIMBANGAN FISIK di {port} ({baudrate} baud) <<<")
        # ---------------------------

        self.worker.moveToThread(self.thread)
        self.worker.data_terbaca.connect(self.update_berat_display)
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        
    def print_selected_slip(self):
        if not self.last_selected_transaction_id:
            QMessageBox.warning(self, "Selection Error", "Please select a transaction from the table to print.")
            return
        t = get_transaction_by_id(self.db_conn, self.last_selected_transaction_id)
        if not t:
            QMessageBox.critical(self, "Error", f"Could not retrieve details for {self.last_selected_transaction_id}.")
            return
        first_w = t['first_weigh_kg'] or 0; second_w = t['second_weigh_kg'] or 0
        gross = max(first_w, second_w); tare = min(first_w, second_w) if second_w > 0 else 0
        html = f"""<html><head><style>body {{ font-family: Arial, sans-serif; font-size: 11pt; color: black; }} h1 {{ text-align: center; font-size: 16pt; margin-bottom: 20px; }} table {{ width: 100%; border-collapse: collapse; }} td {{ padding: 5px 8px; }} .main-container > tbody > tr > td {{ vertical-align: top; padding: 0; }} .info-table td.label {{ font-weight: bold; width: 130px; }} .info-table td.value {{ text-align: right; }} .footer-table td {{ padding-top: 40px; font-size: 10pt; }}</style></head><body><h1>Weighing Slip</h1><table class="header-table"><tr><td><b>Date:</b> {datetime.strptime(t['first_weigh_timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%Y/%m/%d %H:%M:%S')}</td><td align="right"><b>Slip No:</b> {t['transaction_id']}</td></tr></table><hr><br><table class="main-container"><tr><td><table class="info-table"><tr><td class="label">Vehicle Plate No.</td><td>: {t['plate_number']}</td></tr><tr><td class="label">Goods Type</td><td>: {t['goods_type']}</td></tr><tr><td class="label">Supplier</td><td>: {t['goods_origin'] or '-'}</td></tr><tr><td class="label">Receiver</td><td>: {t['goods_destination'] or '-'}</td></tr><tr><td class="label">Remake</td><td>: {t['remake'] or '-'}</td></tr></table></td><td><table class="info-table"><tr><td class="label">Gross</td><td class="value">{gross:,.2f} KG</td></tr><tr><td class="label">Tare</td><td class="value">{tare:,.2f} KG</td></tr><tr><td class="label">Net</td><td class="value"><b>{t['net_weigh_kg'] or 0:,.2f} KG</b></td></tr><tr><td class="label">Quantity</td><td>: {t['quantity'] or '-'}</td></tr></table></td></tr></table><table class="footer-table"><tr><td>Operator: System Admin</td><td align="right">Customer Signature: _________________</td></tr></table></body></html>"""
        document = QTextDocument(); document.setHtml(html); printer = QPrinter(QPrinter.PrinterMode.HighResolution); preview_dialog = QPrintPreviewDialog(printer, self); preview_dialog.setStyleSheet("QWidget { background-color: white; color: black; }"); preview_dialog.resize(1000, 800); preview_dialog.paintRequested.connect(document.print_); preview_dialog.exec()
    def recalculate_total_net(self):
        try: net_str = self.display_net.text().replace(',', ''); potongan_str = self.input_potongan.text().replace(',', ''); net = float(net_str) if net_str else 0.0; potongan = float(potongan_str) if potongan_str else 0.0; total_bersih = net - potongan; self.display_total_bersih.setText(f"{total_bersih:,.2f}")
        except ValueError: self.display_total_bersih.setText(self.display_net.text())
    def tampilkan_error_koneksi(self, message):
        QMessageBox.critical(self, "Connection Error", message); self.live_weight_display.setText("ERROR"); self.stability_status_label.setText("CONNECTION ERROR"); self.stability_status_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #E53E3E;"); self.btn_input.setEnabled(False)
    def refresh_history_table(self):
        today_str = datetime.now().strftime("%Y-%m-%d"); transactions = get_filtered_transactions(self.db_conn, today_str, today_str); self.history_table.setRowCount(0); self.history_table.setRowCount(len(transactions)); color_default = QColor("#E2E8F0"); color_pending = QColor("#F6E05E"); color_completed = QColor("#48BB78"); color_row_bg_even = QColor("#2D3748"); color_row_bg_odd = QColor("#293241")
        for row, transaction in enumerate(transactions):
            try:
                first_w = transaction['first_weigh_kg'] or 0; second_w = transaction['second_weigh_kg'] or 0; gross = max(first_w, second_w); tare = min(first_w, second_w) if second_w > 0 else 0
                if transaction['first_weigh_timestamp']: date_str = datetime.strptime(transaction['first_weigh_timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m %H:%M')
                else: date_str = "N/A"
                quantity = transaction['quantity'] or '-'; remake = transaction['remake'] or '-'
                columns_data = [transaction['transaction_id'], date_str, transaction['plate_number'], transaction['goods_type'], transaction['goods_origin'], transaction['goods_destination'], transaction['status'], f"{gross:,.2f}", f"{tare:,.2f}", f"{transaction['net_weigh_kg'] or 0:,.2f}", quantity, remake]
                current_row_bg_color = color_row_bg_even if row % 2 == 0 else color_row_bg_odd
                for col, cell_data in enumerate(columns_data):
                    item = QTableWidgetItem(str(cell_data)); item.setForeground(QBrush(color_default)); item.setBackground(QBrush(current_row_bg_color))
                    if col in [7, 8, 9]: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    elif col == 6: item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    else: item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    if col == 6:
                        if cell_data == 'PENDING': item.setForeground(QBrush(color_pending)); item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                        elif cell_data == 'COMPLETED': item.setForeground(QBrush(color_completed)); item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                    self.history_table.setItem(row, col, item)
            except Exception as e:
                print(f"Error processing row {row} for transaction {transaction.get('transaction_id', 'N/A')}: {e}")
                continue
    def update_next_transaction_id(self): next_id = generate_transaction_id(self.db_conn); self.next_transaction_id_label.setText(next_id)
    def update_datetime_status_bar(self): now = datetime.now(); formatted_datetime = now.strftime("%A, %d %B %Y | %H:%M:%S"); self.status_datetime_label.setText(formatted_datetime)
    def update_berat_display(self, berat):
        self.live_weight_display.setText(f"{berat:,.2f}")
        self.weight_readings.append(berat)
        if len(self.weight_readings) == STABILITY_WINDOW_SIZE:
            max_val = max(self.weight_readings); min_val = min(self.weight_readings)
            if (max_val - min_val) <= STABILITY_TOLERANCE: self.set_stability_status(True)
            else: self.set_stability_status(False)
        else: self.set_stability_status(False)
    def set_stability_status(self, stable):
        self.is_stable = stable
        if stable: self.btn_input.setEnabled(True); self.stability_status_label.setText("STABLE"); self.stability_status_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #48BB78;")
        else: self.btn_input.setEnabled(False); self.stability_status_label.setText("UNSTABLE"); self.stability_status_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #F6E05E;")
    def proses_input_cerdas(self):
        if not self.is_stable: QMessageBox.warning(self, "Weight Unstable", "Cannot input data, weight is unstable. Please wait."); return
        plate_number = self.input_nomor_kendaraan.text().strip()
        if not plate_number: QMessageBox.warning(self, "Input Error", "Plate No. is required!"); return
        try: current_weight = float(self.live_weight_display.text().replace(',', ''))
        except ValueError: QMessageBox.critical(self, "Error", "Could not read weight from scale."); return
        pending_transaction = find_pending_by_plate_number(self.db_conn, plate_number)
        if pending_transaction:
            gross_str = self.display_gross.text().replace(',', ''); gross = float(gross_str) if gross_str else 0.0
            tare = current_weight; net = abs(gross - tare)
            self.display_tare.setText(f"{tare:,.2f}"); self.display_net.setText(f"{net:,.2f}")
            self.recalculate_total_net()
            final_net_str = self.display_total_bersih.text().replace(',', ''); final_net = float(final_net_str) if final_net_str else 0.0
            transaction_id = pending_transaction['transaction_id']
            potongan_str = self.input_potongan.text().replace(',', ''); potongan = float(potongan_str) if potongan_str else 0.0
            original_remake = self.input_remake.text().strip(); remake_info = original_remake
            if potongan > 0: remake_info = f"(Deduction : {potongan:,.2f} KG.) {original_remake}".strip()
            if complete_second_weigh(self.db_conn, transaction_id, tare, final_net, remake_info):
                QMessageBox.information(self, "Success", f"Second weigh for {plate_number} was successful.")
                self.refresh_history_table(); self.clear_form()
            else: QMessageBox.critical(self, "Database Error", "Failed to complete second weigh.")
        else:
            self.display_gross.setText(f"{current_weight:,.2f}")
            data = {'plate_number': plate_number, 'goods_type': self.input_jenis_barang.text().strip(), 'goods_origin': self.input_asal.text().strip(),'goods_destination': self.input_tujuan.text().strip(),'driver_name': self.input_nama_sopir.text().strip(),'vendor': "", 'customer': "", 'quantity': self.input_quantity.text().strip(),'remake': self.input_remake.text().strip(), 'weight': current_weight}
            if create_first_weigh(self.db_conn, data):
                QMessageBox.information(self, "Success", f"First weigh for {plate_number} has been saved.")
                self.refresh_history_table(); self.clear_form()
            else: QMessageBox.critical(self, "Database Error", "Failed to save data to database.")
    def load_transaction_by_id(self, row, column):
        transaction_id = self.history_table.item(row, 0).text()
        if not transaction_id: return
        self.last_selected_transaction_id = transaction_id
        t = get_transaction_by_id(self.db_conn, transaction_id)
        if t:
            self.clear_form(keep_selection=True)
            self.input_nomor_kendaraan.setText(t['plate_number'] or ""); self.input_jenis_barang.setText(t['goods_type'] or ""); self.input_asal.setText(t['goods_origin'] or ""); self.input_tujuan.setText(t['goods_destination'] or ""); self.input_quantity.setText(t['quantity'] or ""); self.input_remake.setText(t['remake'] or ""); self.input_nama_sopir.setText(t['driver_name'] or "")
            first_w = t['first_weigh_kg'] or 0; second_w = t['second_weigh_kg'] or 0
            gross = max(first_w, second_w); tare = min(first_w, second_w) if second_w > 0 else 0; net = t['net_weigh_kg'] or 0
            self.display_gross.setText(f"{gross:,.2f}"); self.display_tare.setText(f"{tare:,.2f}"); self.display_net.setText(f"{net:,.2f}"); self.input_potongan.setText("0.0"); self.display_total_bersih.setText(f"{net:,.2f}")
            if t['status'] == 'PENDING':
                self.input_nomor_kendaraan.setReadOnly(True); self.input_nomor_kendaraan.setStyleSheet("background-color: #4A5568;")
                QMessageBox.information(self, "Data Loaded", f"Data PENDING untuk {t['plate_number']} dimuat. Siap untuk timbang kedua.")
            else:
                self.input_nomor_kendaraan.setReadOnly(False); self.input_nomor_kendaraan.setStyleSheet("background-color: #1A202C;")
                QMessageBox.information(self, "Data Loaded", f"Data COMPLETED untuk {t['plate_number']} dimuat (mode review).")
        else: QMessageBox.warning(self, "Data Not Found", f"Transaction with ID {transaction_id} not found."); self.last_selected_transaction_id = None
    def clear_form(self, keep_selection=False):
        for widget in [self.input_nomor_kendaraan, self.input_jenis_barang, self.input_asal, self.input_tujuan, self.input_quantity, self.input_remake, self.input_nama_sopir]: widget.clear()
        for widget in [self.display_gross, self.display_tare, self.display_net, self.input_potongan, self.display_total_bersih]: widget.setText("0.0")
        if not keep_selection:
            self.history_table.clearSelection(); self.last_selected_transaction_id = None
        self.input_nomor_kendaraan.setReadOnly(False); self.input_nomor_kendaraan.setStyleSheet("background-color: #1A202C;")
        self.update_next_transaction_id()
    def open_report_window(self):
        if self.report_win is None: self.report_win = ReportWindow(self.db_conn)
        self.report_win.show()
    def open_settings_window(self):
        if self.settings_win is None: self.settings_win = SettingsWindow(self.db_conn)
        self.settings_win.show()
    def closeEvent(self, event):
        if hasattr(self, 'worker'): self.worker.stop()
        if hasattr(self, 'thread'): self.thread.quit(); self.thread.wait()
        if self.db_conn: self.db_conn.close(); print("Database connection closed.")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv); login_win = LoginWindow(); main_win = None
    def show_main_window(username): global main_win; main_win = MainWindow(); main_win.show()
    login_win.login_successful.connect(show_main_window); login_win.show(); sys.exit(app.exec())