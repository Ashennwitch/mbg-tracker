# app.py (Server Utama)
import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Inisialisasi Aplikasi Flask
app = Flask(__name__)

# --- KONFIGURASI SERVER UTAMA (NEON DB) ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inisialisasi Database & Migrasi
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- MODEL DATABASE (RDBMS) ---
# Model ini HARUS SAMA dengan model di gateway Anda
# Ini akan mencatat semua data yang masuk dari BANYAK gateway
class ScanEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nfc_tag_id = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, index=True) # Terima timestamp dari gateway
    status_scan = db.Column(db.String(50), nullable=False)
    
    # Tambahkan kolom ini untuk melacak DARI MANA data berasal
    gateway_id = db.Column(db.String(100), index=True) 

    def __repr__(self):
        return f'<ScanEvent {self.nfc_tag_id} from {self.gateway_id}>'

# --- API UNTUK MENERIMA SINKRONISASI DATA ---
# Ini adalah endpoint yang akan dipanggil oleh gateway Raspberry Pi Anda
@app.route('/api/sync_gateway_data', methods=['POST'])
def sync_gateway_data():
    data_list = request.get_json()
    
    if not isinstance(data_list, list):
        return jsonify({'error': 'Data harus berupa list/array'}), 400
        
    try:
        new_events_count = 0
        for data in data_list:
            # Validasi data
            if not data or 'nfc_tag_id' not in data or 'gateway_id' not in data:
                print(f"Data tidak lengkap, dilewati: {data}")
                continue
            
            # Konversi timestamp string (ISO format) kembali ke objek datetime
            event_timestamp = datetime.fromisoformat(data['timestamp'])
            
            new_scan = ScanEvent(
                nfc_tag_id=data['nfc_tag_id'],
                status_scan=data['status_scan'],
                timestamp=event_timestamp, # Gunakan timestamp asli dari gateway
                gateway_id=data['gateway_id']
            )
            db.session.add(new_scan)
            new_events_count += 1
            
        db.session.commit()
        
        print(f"Berhasil menerima {new_events_count} data baru.")
        return jsonify({'message': f'Berhasil menerima {new_events_count} data'}), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saat sinkronisasi: {e}")
        return jsonify({'error': str(e)}), 500

# --- API UNTUK DASHBOARD WEB ---
# Ini adalah contoh endpoint untuk dashboard React Anda
@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    # Anda bisa membuat query yang kompleks di sini
    total_scans = ScanEvent.query.count()
    unique_gateways = db.session.query(ScanEvent.gateway_id).distinct().count()
    
    return jsonify({
        'total_scans_received': total_scans,
        'active_gateways': unique_gateways
    })

if __name__ == '__main__':
    # Jalankan server di port yang berbeda dari gateway, misal 8000
    app.run(host='0.0.0.0', port=8000, debug=True)