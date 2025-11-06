# app.py
import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Inisialisasi Aplikasi Flask
app = Flask(__name__)

# Konfigurasi Database SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'local_gateway.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inisialisasi Database & Migrasi
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- MODEL DATABASE (RDBMS) ---
# Tabel ini akan mencatat setiap peristiwa pemindaian (scan)
# yang terjadi di gateway ini.
class ScanEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nfc_tag_id = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    # Status bisa berupa 'makanan_keluar' (dari SPPG) atau 'makanan_diterima' (di Sekolah)
    # Ini sesuai dengan alur di diagram 3.5 & 3.6 [cite: 279, 291]
    status_scan = db.Column(db.String(50), nullable=False) 
    
    # Flag untuk sinkronisasi 
    synced_to_main_server = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<ScanEvent {self.nfc_tag_id} at {self.timestamp}>'

# --- Inisialisasi Database ---
# Anda hanya perlu menjalankan ini sekali di terminal
# 1. export FLASK_APP=app.py  (atau 'set FLASK_APP=app.py' di Windows)
# 2. flask db init
# 3. flask db migrate -m "Initial migration."
# 4. flask db upgrade
#
# Perintah ini akan membuat file database 'local_gateway.db'

# --- 1. API UNTUK MENCATAT SCAN LOKAL ---
# Endpoint ini akan dipanggil oleh script NFC reader 
# atau aplikasi Android Petugas [cite: 328, 330]
@app.route('/api/log_scan', methods=['POST'])
def log_scan():
    data = request.get_json()
    
    if not data or 'nfc_tag_id' not in data or 'status_scan' not in data:
        return jsonify({'error': 'Data tidak lengkap. Butuh "nfc_tag_id" dan "status_scan".'}), 400
        
    try:
        new_scan = ScanEvent(
            nfc_tag_id=data['nfc_tag_id'],
            status_scan=data['status_scan']
            # timestamp dan synced_to_main_server sudah memiliki nilai default
        )
        db.session.add(new_scan)
        db.session.commit()
        
        # Cetak ke konsol Pi untuk debugging
        print(f"Scan dicatat: {new_scan}")
        
        return jsonify({'message': 'Scan berhasil dicatat di gateway lokal'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- 2. LOGIKA SINKRONISASI KE SERVER UTAMA ---
# Ini adalah fungsi inti dari gateway 
# Kita akan menggunakan 'requests' untuk ini (pip install requests)
import requests
import time
from threading import Thread

# Alamat server utama (placeholder)
MAIN_SERVER_API_URL = os.environ.get('MAIN_SERVER_API_URL')

def sync_to_main_server():
    # Fungsi ini akan berjalan selamanya di background
    while True:
        # Tunggu 60 detik sebelum mencoba sinkronisasi berikutnya
        time.sleep(60) 
        
        with app.app_context(): # Kita butuh konteks aplikasi untuk akses 'db'
            print("Mencoba sinkronisasi ke server utama...")
            try:
                # 1. Ambil semua event yang BELUM disinkronkan 
                events_to_sync = ScanEvent.query.filter_by(synced_to_main_server=False).all()
                
                if not events_to_sync:
                    print("Tidak ada data baru untuk disinkronkan.")
                    continue
                    
                # Ubah data ke format JSON
                data_payload = [
                    {
                        'nfc_tag_id': event.nfc_tag_id,
                        'timestamp': event.timestamp.isoformat(),
                        'status_scan': event.status_scan,
                        'gateway_id': 'RASPBERRY_PI_SEKOLAH_A' # Anda harus punya ID unik
                    } for event in events_to_sync
                ]

                # 2. Kirim data ke server utama
                response = requests.post(MAIN_SERVER_API_URL, json=data_payload, timeout=10)
                
                # 3. Jika berhasil (HTTP 200 atau 201), tandai sebagai 'synced'
                if response.status_code == 200 or response.status_code == 201:
                    for event in events_to_sync:
                        event.synced_to_main_server = True
                    db.session.commit()
                    print(f"Berhasil sinkronisasi {len(events_to_sync)} data.")
                else:
                    print(f"Gagal sinkronisasi. Server utama merespon: {response.status_code}")
                
            except requests.exceptions.RequestException as e:
                # Ini akan terjadi jika server utama mati atau Pi tidak ada internet
                print(f"Gagal terhubung ke server utama: {e}")
            except Exception as e:
                print(f"Terjadi error saat sinkronisasi: {e}")
                db.session.rollback()


# --- Menjalankan Aplikasi Flask & Background Thread ---
if __name__ == '__main__':
    # Pastikan database sudah dibuat (flask db upgrade)
    
    # Mulai thread sinkronisasi di background
    sync_thread = Thread(target=sync_to_main_server, daemon=True)
    sync_thread.start()
    
    # Jalankan server Flask (bisa diakses dari jaringan lokal)
    app.run(host='0.0.0.0', port=5000, debug=True)