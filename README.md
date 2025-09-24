# Weighing System - Aplikasi Jembatan Timbang (Weighbridge Application)

Selamat datang di WAIO System, sebuah aplikasi desktop yang dirancang untuk mengelola proses penimbangan di jembatan timbang industri. Aplikasi ini dibangun untuk menangani transaksi penimbangan kendaraan berat seperti truk dan trailer, dengan koneksi langsung ke indikator timbangan fisik melalui port serial.



## Fitur Utama ✨

* **Koneksi Timbangan Real-time**: Menampilkan angka berat yang diterima dari timbangan fisik secara terus-menerus.
* **Deteksi Berat Stabil**: Tombol input utama hanya akan aktif ketika berat timbangan sudah stabil, memastikan akurasi data yang diinput.
* **Manajemen Transaksi Lengkap**: Mendukung alur kerja dua tahap (timbang pertama/Gross dan timbang kedua/Tare).
* **Kalkulasi Otomatis**: Secara otomatis menghitung berat bersih (Net) dan total bersih setelah adanya potongan.
* **Potongan Berat (Deduction)**: Operator dapat memasukkan nilai potongan manual yang akan mengurangi berat bersih secara otomatis.
* **Histori Transaksi Harian**: Menampilkan semua transaksi yang terjadi pada hari itu di halaman utama untuk akses cepat.
* **Cetak Slip**: Mencetak slip atau tiket timbangan untuk transaksi yang dipilih langsung dari halaman utama atau dari halaman laporan.
* **Manajemen Pengguna**: Sistem login dengan dua level pengguna (Administrator, Operator) yang dapat dikelola melalui jendela pengaturan.
* **Pengaturan Dinamis**: Pengaturan koneksi (Port COM dan Baud Rate) dapat diubah melalui antarmuka pengguna dan akan tersimpan untuk penggunaan selanjutnya.
* **Laporan Transaksi**: Membuat laporan transaksi berdasarkan rentang tanggal dan jenis barang, serta mengekspornya ke format PDF.
* **Mode Simulator**: Dilengkapi dengan simulator timbangan internal untuk keperluan development dan pengetesan tanpa harus terhubung ke timbangan fisik.

## Teknologi yang Digunakan 💻

* **Bahasa Pemrograman**: Python
* **Framework GUI**: PySide6
* **Komunikasi Serial**: pySerial
* **Database**: SQLite3 (untuk menyimpan data transaksi dan pengguna)
* **Laporan PDF**: ReportLab
* **Packaging**: PyInstaller (untuk membuat file `.exe`)

---

## Instalasi & Menjalankan dari Kode Sumber

Untuk menjalankan aplikasi ini dari kode sumber, ikuti langkah-langkah berikut:

1.  **Clone Repository (jika ada)**
    ```bash
    git clone [URL_REPOSITORY_ANDA]
    cd [NAMA_FOLDER_PROYEK]
    ```

2.  **Buat Lingkungan Virtual (Virtual Environment)**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependensi**
    Pastikan semua library yang dibutuhkan terinstal dengan menjalankan:
    ```bash
    pip install pyside6 pyserial reportlab
    ```
    Atau jika Anda memiliki file `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Jalankan Aplikasi**
    Aplikasi akan dimulai dengan menampilkan jendela login.
    ```bash
    python main_app.py
    ```

## Konfigurasi

* **Koneksi Timbangan**: Pengaturan Port COM dan Baud Rate disimpan di file `config.json` yang dibuat secara otomatis. Anda bisa mengubahnya melalui menu **Settings > Connection**.
* **Database**: Semua data transaksi dan pengguna disimpan di file `weighing_system.db` yang juga dibuat secara otomatis.
* **Login Default**: Saat aplikasi dijalankan pertama kali, sebuah pengguna default akan dibuat:
    * **Username**: ***
    * **Password**: ***

---

## Membuat File Executable (.exe)

Untuk mengemas aplikasi ini menjadi satu file `.exe` mandiri, gunakan PyInstaller dengan perintah berikut (jalankan di terminal dari folder proyek):

1.  **Install PyInstaller**
    ```bash
    pip install pyinstaller
    ```

2.  **Jalankan Perintah Build**
    Pastikan Anda memiliki file ikon `.ico` (misalnya `app_icon.ico`) di folder proyek.
    ```bash
    pyinstaller --name "Weighing System" --windowed --onefile --icon="app_icon.ico" --hidden-import="PySide6.QtPrintSupport" main_app.py
    ```

3.  **Hasil Akhir**
    File `Weighing System.exe` yang sudah jadi akan berada di dalam folder `dist`.

---

Dibuat oleh **paripira**

