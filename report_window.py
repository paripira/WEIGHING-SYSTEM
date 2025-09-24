from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
                               QDateEdit, QLineEdit, QFrame, QMessageBox,
                               QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor, QBrush, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from datetime import datetime
import os
import re 
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


from database import get_filtered_transactions, delete_transaction_by_id, get_transaction_by_id
class ReportWindow(QWidget):
    def __init__(self, db_conn):
        super().__init__()
        self.db_conn = db_conn; self.filtered_data = []
        self.setWindowTitle("Transaction Report"); self.setGeometry(150, 150, 1200, 700)
        self.setStyleSheet("""
            QWidget { background-color: #1A202C; color: #E2E8F0; font-size: 10pt; }
            QFrame#card { background-color: #2D3748; border-radius: 8px; }
            QLabel { font-weight: bold; color: #A0AEC0; }
            QLineEdit, QDateEdit { background-color: #1A202C; border: 1px solid #4A5568; border-radius: 4px; padding: 6px; color: #E2E8F0; }
            QPushButton { background-color: #38B2AC; border: none; padding: 10px; border-radius: 4px; font-weight: bold; color: white; }
            QPushButton:hover { background-color: #319795; }
            QPushButton#delete_button { background-color: #E53E3E; }
            QPushButton#delete_button:hover { background-color: #C53030; }
            QTableWidget { background-color: #2D3748; border-radius: 8px; border: 1px solid #4A5568; gridline-color: #4A5568; }
            QHeaderView::section { background-color: #1A202C; color: #E2E8F0; padding: 8px; border-bottom: 1px solid #4A5568; border-right: 1px solid #4A5568; font-size: 9pt; font-weight: bold; }
        """)

        main_layout = QVBoxLayout(self)
        filter_frame = QFrame(objectName="card"); filter_layout = QHBoxLayout(filter_frame)
        self.start_date_edit = QDateEdit(calendarPopup=True); self.start_date_edit.setDisplayFormat("dd/MM/yyyy"); self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.end_date_edit = QDateEdit(calendarPopup=True); self.end_date_edit.setDisplayFormat("dd/MM/yyyy"); self.end_date_edit.setDate(QDate.currentDate())
        self.goods_filter_edit = QLineEdit(); self.goods_filter_edit.setPlaceholderText("Filter by Goods Type (leave empty for all)...")
        filter_button = QPushButton("Apply Filter"); filter_button.clicked.connect(self.apply_filter)
        filter_layout.addWidget(QLabel("From:")); filter_layout.addWidget(self.start_date_edit)
        filter_layout.addWidget(QLabel("To:")); filter_layout.addWidget(self.end_date_edit)
        filter_layout.addSpacing(20); filter_layout.addWidget(self.goods_filter_edit, 1); filter_layout.addWidget(filter_button)
        
        self.report_table = QTableWidget(); self.report_table.setColumnCount(12)
        headers = ["Transaction ID", "Date", "Vehicle Plate No.", "Goods Type", "Origin", "Destination", "Status", "Gross", "Tare", "Net", "Quantity", "Remake"]
        self.report_table.setHorizontalHeaderLabels(headers)
        header = self.report_table.horizontalHeader(); header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(11, QHeaderView.ResizeMode.Stretch)

        self.report_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.report_table.verticalHeader().setVisible(False); self.report_table.verticalHeader().setDefaultSectionSize(35); self.report_table.setAlternatingRowColors(True); self.report_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.report_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.status_label = QLabel("Showing results..."); self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        action_layout = QHBoxLayout()
        export_button = QPushButton("Export to PDF"); export_button.clicked.connect(self.export_pdf)
        print_button = QPushButton("Print Slip"); print_button.clicked.connect(self.print_slip)
        delete_button = QPushButton("Delete Transaction", objectName="delete_button"); delete_button.clicked.connect(self.delete_transaction)
        
        action_layout.addWidget(self.status_label, 1); action_layout.addWidget(delete_button); action_layout.addWidget(print_button); action_layout.addWidget(export_button)

        main_layout.addWidget(filter_frame); main_layout.addWidget(self.report_table); main_layout.addLayout(action_layout)
        self.apply_filter()

    # Ganti total fungsi print_slip:
    def print_slip(self):
        selected_rows = self.report_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selection Error", "Please select a transaction from the table to print.")
            return
        
        transaction_id = self.report_table.item(selected_rows[0].row(), 0).text()
        t = get_transaction_by_id(self.db_conn, transaction_id)
        if not t:
            QMessageBox.critical(self, "Error", "Could not retrieve transaction details.")
            return

        first_w = t['first_weigh_kg'] or 0
        second_w = t['second_weigh_kg'] or 0
        gross = max(first_w, second_w)
        tare = min(first_w, second_w) if second_w > 0 else 0
        
        # --- Menambahkan 'color: black;' pada style HTML ---
        html = f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    font-size: 11pt; 
                    color: black; /* <-- Teks default dibuat hitam */
                }}
                h1 {{ text-align: center; font-size: 16pt; margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                td {{ padding: 5px 8px; }}
                .main-container > tbody > tr > td {{ vertical-align: top; padding: 0; }}
                .info-table td.label {{ font-weight: bold; width: 130px; }}
                .info-table td.value {{ text-align: right; }}
                .footer-table td {{ padding-top: 40px; font-size: 10pt; }}
            </style>
        </head>
        <body>
            <h1>Weighing Slip</h1>
            <table class="header-table">
                <tr>
                    <td><b>Date:</b> {datetime.strptime(t['first_weigh_timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%Y/%m/%d %H:%M:%S')}</td>
                    <td align="right"><b>Slip No:</b> {t['transaction_id']}</td>
                </tr>
            </table>
            <hr>
            <br>
            <table class="main-container">
                <tr>
                    <td>
                        <table class="info-table">
                            <tr><td class="label">Vehicle Plate No.</td><td>: {t['plate_number']}</td></tr>
                            <tr><td class="label">Goods Type</td><td>: {t['goods_type']}</td></tr>
                            <tr><td class="label">Supplier</td><td>: {t['goods_origin'] or '-'}</td></tr>
                            <tr><td class="label">Receiver</td><td>: {t['goods_destination'] or '-'}</td></tr>
                            <tr><td class="label">Amount (Words)</td><td>: ( ***** )</td></tr>
                            <tr><td class="label">Remake</td><td>: {t['remake'] or '-'}</td></tr>
                        </table>
                    </td>
                    <td>
                        <table class="info-table">
                            <tr><td class="label">Gross</td><td class="value">{gross:,.2f} KG</td></tr>
                            <tr><td class="label">Tare</td><td class="value">{tare:,.2f} KG</td></tr>
                            <tr><td class="label">Net</td><td class="value"><b>{t['net_weigh_kg'] or 0:,.2f} KG</b></td></tr>
                            <tr><td class="label">Unit Price</td><td>: </td></tr>
                            <tr><td class="label">Total Amount</td><td>: </td></tr>
                            <tr><td class="label">Quantity</td><td>: {t['quantity'] or '-'}</td></tr>
                        </table>
                    </td>
                </tr>
            </table>

            <table class="footer-table">
                <tr>
                    <td>Operator: System Admin</td>
                    <td align="right">Customer Signature: _________________</td>
                </tr>
            </table>
        </body>
        </html>
        """

        document = QTextDocument()
        document.setHtml(html)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        preview_dialog = QPrintPreviewDialog(printer, self)
        
        # --- Paksa dialog preview menggunakan tema terang ---
        preview_dialog.setStyleSheet("QWidget { background-color: white; color: black; }")
        
        preview_dialog.resize(1000, 800)
        preview_dialog.paintRequested.connect(document.print_)
        preview_dialog.exec()

    def apply_filter(self):
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd"); end_date = self.end_date_edit.date().toString("yyyy-MM-dd"); goods_type = self.goods_filter_edit.text().strip()
        self.filtered_data = get_filtered_transactions(self.db_conn, start_date, end_date, goods_type); self.populate_table(); self.status_label.setText(f"Showing {len(self.filtered_data)} results.")
    def populate_table(self):
        self.report_table.setRowCount(0); self.report_table.setRowCount(len(self.filtered_data)); font_data = QFont("Arial", 9); color_default = QColor("#E2E8F0"); color_pending = QColor("#F6E05E"); color_completed = QColor("#48BB78"); color_row_bg_even = QColor("#2D3748"); color_row_bg_odd = QColor("#293241")
        for row, transaction in enumerate(self.filtered_data):
            first_w = transaction['first_weigh_kg'] or 0; second_w = transaction['second_weigh_kg'] or 0; gross = max(first_w, second_w); tare = min(first_w, second_w) if second_w > 0 else 0
            date_str = datetime.strptime(transaction['first_weigh_timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%y %H:%M'); quantity = transaction['quantity'] or '-'; remake = transaction['remake'] or '-'
            columns_data = [transaction['transaction_id'], date_str, transaction['plate_number'], transaction['goods_type'], transaction['goods_origin'], transaction['goods_destination'], transaction['status'], f"{gross:,.2f}", f"{tare:,.2f}", f"{transaction['net_weigh_kg'] or 0:,.2f}", quantity, remake]; current_row_bg_color = color_row_bg_even if row % 2 == 0 else color_row_bg_odd
            for col, cell_data in enumerate(columns_data):
                item = QTableWidgetItem(str(cell_data)); item.setFont(font_data); item.setForeground(QBrush(color_default)); item.setBackground(QBrush(current_row_bg_color))
                if col in [7, 8, 9]: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                elif col == 6: item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else: item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if col == 6:
                    if cell_data == 'PENDING': item.setForeground(QBrush(color_pending)); item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                    elif cell_data == 'COMPLETED': item.setForeground(QBrush(color_completed)); item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                self.report_table.setItem(row, col, item)
    def delete_transaction(self):
        selected_rows = self.report_table.selectionModel().selectedRows()
        if not selected_rows: QMessageBox.warning(self, "Selection Error", "Please select a transaction from the table to delete."); return
        transaction_id = self.report_table.item(selected_rows[0].row(), 0).text()
        reply = QMessageBox.question(self, 'Confirm Deletion', f"Are you sure you want to permanently delete transaction {transaction_id}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if delete_transaction_by_id(self.db_conn, transaction_id): QMessageBox.information(self, "Success", f"Transaction {transaction_id} has been deleted."); self.apply_filter()
            else: QMessageBox.critical(self, "Error", f"Failed to delete transaction {transaction_id}.")
    def export_pdf(self):
        #print_slip kini menjadi cara utama untuk cetak per data
        if not self.filtered_data: QMessageBox.warning(self, "No Data", "No data to export."); return
        pass

    # Ganti total fungsi export_pdf dengan yang ini:
    def export_pdf(self):
        if not self.filtered_data:
            QMessageBox.warning(self, "No Data", "No data to export.")
            return

        default_filename = f"Transaction_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", default_filename, "PDF Files (*.pdf)")
        if not filepath:
            return

        doc = SimpleDocTemplate(filepath, pagesize=letter, 
                                leftMargin=0.5*inch, rightMargin=0.5*inch, 
                                topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        styles.add(ParagraphStyle(name='ReportTitle', parent=styles['h1'], fontSize=16, alignment=TA_CENTER, spaceAfter=14))
        styles.add(ParagraphStyle(name='ReportSubtitle', parent=styles['h2'], fontSize=12, alignment=TA_CENTER, spaceAfter=12))

        story.append(Paragraph("Laporan Transaksi Weighing", styles['ReportTitle']))
        story.append(Paragraph(f"Periode: {self.start_date_edit.text()} - {self.end_date_edit.text()}", styles['ReportSubtitle']))
        story.append(Spacer(1, 0.2*inch))
        
        # --- PERUBAHAN 1: Menghapus kolom "Status" ---
        header = ["ID Transaksi", "Tanggal", "No. Plat", "Jenis Barang", "Asal", "Tujuan", "Kotor (kg)", "Tara (kg)", "Bersih (kg)", "Qty", "Keterangan"]
        pdf_data = [header]
        for t in self.filtered_data:
            first_w = t['first_weigh_kg'] or 0; second_w = t['second_weigh_kg'] or 0
            gross = max(first_w, second_w); tare = min(first_w, second_w) if second_w > 0 else 0
            date_str = datetime.strptime(t['first_weigh_timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%y %H:%M')
            pdf_data.append([
                t['transaction_id'], 
                date_str, 
                t['plate_number'], 
                t['goods_type'], 
                t['goods_origin'], 
                t['goods_destination'], 
                f"{gross:,.2f}", 
                f"{tare:,.2f}", 
                f"{t['net_weigh_kg'] or 0:,.2f}", 
                t['quantity'] or '-', 
                t['remake'] or '-'
            ])
        
        # Sesuaikan lebar kolom (kini hanya 11 kolom)
        col_widths = [
            0.8*inch, 0.8*inch, 0.8*inch, 1.1*inch, 0.6*inch, 0.6*inch, 
            0.7*inch, 0.7*inch, 0.7*inch, 0.4*inch, 1.1*inch
        ]
        
        # --- PERUBAHAN 2: Mengatur tabel agar center di halaman ---
        pdf_table = Table(pdf_data, colWidths=col_widths, hAlign='CENTER') # Menggunakan hAlign='CENTER'
        
        style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ])
        pdf_table.setStyle(style)
        
        story.append(pdf_table)
        
        try:
            doc.build(story)
            QMessageBox.information(self, "Export Successful", f"Report successfully saved at:\n{filepath}")
            os.startfile(filepath)
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"Failed to generate PDF report.\nError: {e}")