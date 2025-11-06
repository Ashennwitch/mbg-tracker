# Sistem Pelacakan Stok dan Distribusi Makanan Program MBG

[cite_start]Ini adalah implementasi backend untuk **Sistem Pelacakan Stok dan Distribusi Makanan Program MBG**[cite: 2, 64]. [cite_start]Proyek ini didasarkan pada proposal desain proyek (Kelompok 17 Universitas Indonesia) yang bertujuan menggantikan proses manual dengan sistem pelacakan berbasis teknologi[cite: 58].

Repositori ini berisi kode untuk dua komponen utama sistem:
1.  **Server Utama (<code>mbg-main-server</code>)**: Backend terpusat yang berjalan di server/cloud untuk mengagregasi data dari semua lokasi.
2.  [cite_start]**Gateway Lokal (<code>mbg-gateway</code>)**: Backend ringan yang berjalan di perangkat lapangan (seperti Raspberry Pi) di setiap checkpoint (sekolah/dapur)[cite: 365].

## 🏛️ Arsitektur Alur Data

[cite_start]Sistem ini dirancang untuk bekerja secara andal bahkan dengan koneksi internet yang tidak stabil, sesuai dengan arsitektur yang diusulkan[cite: 301, 302, 346].

1.  **Pencatatan Lokal**: Petugas lapangan (via Aplikasi Android) mengirim data scan NFC ke **Gateway Lokal** (Raspberry Pi).
2.  [cite_start]**Cache Lokal**: Gateway segera menyimpan data scan ke database **SQLite** lokal (`local_gateway.db`) [cite: 402] dan menandainya sebagai "belum disinkronkan".
3.  **Sinkronisasi**: Sebuah proses background di Gateway secara berkala (setiap 60 detik) memeriksa data yang "belum disinkronkan".
4.  **Agregasi Data**: Gateway mengirim data tersebut ke API **Server Utama**.
5.  **Penyimpanan Pusat**: Server Utama menerima data dan menyimpannya secara permanen di database **PostgreSQL** terpusat (di-host di Neon).
6.  **Pembaruan Status**: Setelah berhasil, Server Utama mengirim respons sukses. Gateway kemudian menandai data di database SQLite lokalnya sebagai "sudah disinkronkan".

## 🚀 Tumpukan Teknologi (Tech Stack)

| Komponen | Teknologi | Keterangan |
| :--- | :--- | :--- |
| **Server Utama** | **Flask** | [cite_start]Micro-framework Python untuk API[cite: 378]. |
| | **PostgreSQL (Neon)** | Database RDBMS terpusat (cloud). |
| | **Flask-SQLAlchemy** | ORM untuk interaksi database. |
| | **Flask-Migrate** | Untuk mengelola perubahan skema database. |
| | **psycopg2-binary** | Driver Python untuk PostgreSQL. |
| **Gateway Lokal** | **Flask** | [cite_start]Micro-framework Python untuk API lokal[cite: 378]. |
| | **SQLite** | [cite_start]Database RDBMS file-based, ringan untuk Pi[cite: 402]. |
| | **Flask-SQLAlchemy** | ORM untuk interaksi database. |
| | **Flask-Migrate** | Untuk mengelola perubahan skema database. |
| | **requests** | Untuk mengirim data ke Server Utama. |
| **Hardware (Gateway)** | **Raspberry Pi** | [cite_start]Perangkat yang menjalankan Gateway Lokal[cite: 367, 400]. |

## 📁 Struktur Proyek

/
|-- mbg-gateway/
|   |-- app.py                # Server Flask untuk Gateway
|   |-- local_gateway.db      # Database cache lokal (SQLite)
|   |-- migrations/           # Folder migrasi Alembic
|   `-- ...                   # File tambahan
|
`-- mbg-main-server/
    |-- app.py                # Server Flask untuk Server Utama
    |-- migrations/           # Folder migrasi Alembic
    `-- ...                   # File tambahan

## 🛠️ Panduan Instalasi dan Setup

Disarankan untuk memisahkan folder `mbg-gateway` dan `mbg-main-server`.

### 1. Server Utama (<code>mbg-main-server</code>)

Setup ini dilakukan di server/PC Anda yang memiliki koneksi internet.

1.  **Clone & Masuk ke Direktori:**
    ```bash
    git clone [URL_REPO_ANDA]
    cd mbg-main-server
    ```

2.  **Buat & Aktifkan Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependensi:**
    ```bash
    pip install Flask Flask-SQLAlchemy Flask-Migrate psycopg2-binary
    ```

4.  **Konfigurasi Database (PENTING):**
    Buka `app.py` dan pastikan variabel `app.config['SQLALCHEMY_DATABASE_URI']` berisi *connection string* yang benar ke database Neon (PostgreSQL) Anda.
    ```python
    # Contoh di app.py (Server Utama)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@host:port/db?sslmode=require'
    ```

5.  **Inisialisasi Database:**
    Jalankan perintah ini untuk membuat tabel di database Neon Anda.
    ```bash
    export FLASK_APP=app.py
    flask db init  # Hanya dijalankan sekali saat pertama kali
    flask db migrate -m "Inisialisasi database server utama"
    flask db upgrade
    ```

### 2. Gateway Lokal (<code>mbg-gateway</code>)

Setup ini dilakukan di setiap perangkat Raspberry Pi di lapangan.

1.  **Clone & Masuk ke Direktori:**
    ```bash
    git clone [URL_REPO_ANDA]
    cd mbg-gateway
    ```

2.  **Buat & Aktifkan Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependensi:**
    ```bash
    pip install Flask Flask-SQLAlchemy Flask-Migrate requests
    ```

4.  **Konfigurasi Endpoint (PENTING):**
    Buka `app.py` dan atur variabel `MAIN_SERVER_API_URL` agar menunjuk ke alamat IP dan port Server Utama Anda yang sedang berjalan.
    ```python
    # Contoh di app.py (Gateway)
    MAIN_SERVER_API_URL = "http://[IP_SERVER_UTAMA_ANDA]:8000/api/sync_gateway_data"
    ```

5.  **Inisialisasi Database Lokal:**
    Jalankan perintah ini untuk membuat file `local_gateway.db` (SQLite).
    ```bash
    export FLASK_APP=app.py
    flask db init  # Hanya dijalankan sekali saat pertama kali
    flask db migrate -m "Inisialisasi database gateway lokal"
    flask db upgrade
    ```

## 🚀 Menjalankan Sistem

Anda perlu menjalankan kedua server secara bersamaan di terminal yang terpisah.

* **Terminal 1 - Menjalankan Server Utama:**
    ```bash
    cd mbg-main-server
    source venv/bin/activate
    python app.py
    # * Server berjalan di [http://0.0.0.0:8000/](http://0.0.0.0:8000/)
    ```

* **Terminal 2 - Menjalankan Gateway Lokal:**
    ```bash
    cd mbg-gateway
    source venv/bin/activate
    python app.py
    # * Server berjalan di [http://0.0.0.0:5000/](http://0.0.0.0:5000/)
    ```

## ✅ Pengujian Alur Data (End-to-End)

Untuk memverifikasi sistem berfungsi:

1.  **Kirim Scan ke Gateway**: Kirim data scan palsu ke API Gateway.
    ```bash
    curl -X POST http://[IP_RASPBERRY_PI]:5000/api/log_scan \
    -H "Content-Type: application/json" \
    -d '{"nfc_tag_id": "NFC_TAG_ALPHA", "status_scan": "makanan_keluar"}'
    ```
    * **Hasil**: Anda akan melihat log di Terminal Gateway.
    * **Cek DB Lokal**: Cek `local_gateway.db` (SQLite), data akan ada dengan `synced_to_main_server = 0` (false).

2.  **Tunggu Sinkronisasi**: Tunggu hingga 60 detik.
    * **Hasil**: Anda akan melihat log di **Terminal Gateway** (`Mencoba sinkronisasi...`) dan di **Terminal Server Utama** (`Berhasil menerima...`).

3.  **Verifikasi Server Utama**:
    * **Cek DB Pusat**: Periksa database PostgreSQL (Neon) Anda. Data `NFC_TAG_ALPHA` akan muncul di tabel `scan_event`.

4.  **Verifikasi Status Gateway**:
    * **Cek DB Lokal (Lagi)**: Cek kembali `local_gateway.db` (SQLite). Data `NFC_TAG_ALPHA` sekarang harus memiliki `synced_to_main_server = 1` (true).

## 📖 Definisi API

### Gateway Lokal (`mbg-gateway`)

* `POST /api/log_scan`
    * Mencatat data scan baru ke database SQLite lokal.
    * Body (JSON): `{"nfc_tag_id": "string", "status_scan": "string"}`

### Server Utama (`mbg-main-server`)

* `POST /api/sync_gateway_data`
    * Menerima data dari Gateway dan menyimpannya ke database PostgreSQL.
    * Body (JSON): `[{"nfc_tag_id": "...", "timestamp": "...", "status_scan": "...", "gateway_id": "..."}, ...]`

* `GET /api/dashboard/summary`
    * Contoh endpoint untuk mengambil data ringkasan oleh Dashboard Web.