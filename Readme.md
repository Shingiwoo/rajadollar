# RajaDollar_trading

Bot trading scalping crypto modular untuk Binance Futures — siap deploy, bisa dikontrol lewat Streamlit dan Telegram.

---

## 📦 Struktur Folder Modular

rajadollar/
│
├── main.py
├── config.py
├── requirements.txt
├── .env
├── notifications/
├── utils/
├── risk_management/
├── execution/
├── strategies/
├── backtesting/
├── database/
├── ui/
├── tests/
└── ...

---

## 🚀 **Cara Install & Jalanin (Local/Dev)**

1. **Clone repo & install dependencies:**
    ```sh
    git clone <repo>
    cd rajadollar
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2. **Siapkan file `.env` di root:**
    ```
    TELEGRAM_TOKEN=xxx
    TELEGRAM_CHAT_ID=xxx
    testnet_api_key=xxx
    testnet_secret=xxx
    real_api_key=xxx
    real_api_secret=xxx
    ```

Setelah `.env` terisi, jalankan Streamlit dan pilih `Mode` di sidebar.
Pilih `testnet` untuk simulasi atau `real` untuk trading sungguhan.

3. **Jalankan bot Streamlit UI:**
    ```sh
    streamlit run main.py
    ```

4. **Jalankan unit test:**
    ```sh
    python -m tests.test_scalping_strategy
    # atau
    pytest tests/
    ```

---

## 🔧 **Fitur Utama**

- Modular, mudah maintain
- Trading loop live/auto
- Backtest engine
- Sinyal hybrid ML + indikator
- Resume otomatis & notifikasi Telegram
- Telegram remote command (`/status`, `/entry`, `/stop`, `/ml`, `/log`, `/chart`)
- Logging ke SQLite & visualisasi Streamlit
- Risk management SL/TP/trailing/anti-liquidation
- Slippage checker & minNotional/step checker
- Rate limit API
- Bisa running di testnet/realnet Binance

---

## 🛠️ Deployment & Setup

### Build Docker
```bash
docker build -t rajadollar:latest .
```

### Jalankan Container
```bash
docker run -d --name rajadollar_bot \
  --env-file .env \
  --cpus="2" --memory="2g" \
  -p 8588:8588 \
  -v $PWD/rajadollar_state:/app/runtime_state \
  rajadollar:latest
```
Keterangan:
- `--env-file .env` memuat API key dan token Telegram.
- `--cpus` dan `--memory` membatasi resource container.
- `-p 8588:8588` membuka port Streamlit.
- `-v` membuat direktori `runtime_state` persisten agar aman saat restart.

### Reverse Proxy Nginx
1. Install nginx: `sudo apt install nginx`
2. Salin `docs/nginx_rajadollar.conf` ke `/etc/nginx/sites-available/rajadollar.conf`
3. Aktifkan: `sudo ln -s /etc/nginx/sites-available/rajadollar.conf /etc/nginx/sites-enabled/`
4. Cek dan reload: `sudo nginx -t && sudo systemctl reload nginx`

### Format `.env`
```
TELEGRAM_TOKEN=xxx
TELEGRAM_CHAT_ID=xxx
testnet_api_key=xxx
testnet_secret=xxx
real_api_key=xxx
real_api_secret=xxx
```

Strategi dikonfigurasi lewat `config/strategy_params.json`. Model ML akan dilatih otomatis. Untuk manual gunakan `python ml/training.py --symbol BTCUSDT` atau `--symbol all` juga bisa lewat Telegram (`/ml`, `/mltrain`).

### FAQ
- **Apakah aman restart?** Ya, data di `runtime_state` dipulihkan otomatis.
- **Bagaimana menghindari rate limit?** Semua panggilan Binance melalui `utils/safe_api.py`.
- **Debugging?** Gunakan perintah `/status`, `/log`, atau cek file log di `logs/`.

---
## 🐳 VPS Deployment on /var/www/rajadollar
Untuk produksi di VPS, clone repo ini di `/var/www/rajadollar` lalu bangun dan jalankan container:

```bash
cd /var/www/rajadollar
sudo docker build -t rajadollar:latest .

sudo docker run -d --name rajabot \
  --env-file .env \
  --cpus="2" \
  --memory="2g" \
  -p 8588:8588 \
  -v /var/www/rajadollar/runtime_state:/app/runtime_state \
  rajadollar:latest
```

Pastikan folder `runtime_state` dipasang (`-v`) agar data trading tidak hilang saat container restart.

### Nginx Reverse Proxy
Buat file `/etc/nginx/sites-available/rajabot.conf` dengan isi seperti `docs/rajabot.conf`, lalu aktifkan:

```bash
sudo ln -s /etc/nginx/sites-available/rajabot.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Setelah itu bot dapat diakses di `http://bot.appshin.xyz`.

### Catatan tambahan
- Perintah Telegram: `/status`, `/entry`, `/stop`, `/ml`, `/mltrain`, `/log`, `/chart`.
- Strategi diatur lewat `config/strategy_params.json`.
- Model ML bisa dilatih ulang dengan `python ml/training.py --symbol SYMBOL` atau via Telegram `/mltrain`.

## 📊 Machine Learning Flow

Berikut alur lengkap fitur ML pada bot ini:

1. **Pencatatan Indikator**
   - Setiap simbol yang dipantau akan terus mencatat data pasar dan indikator (EMA, SMA, MACD, RSI).
   - Data bar terbaru selalu ditambahkan ke `data/training_data/<symbol>.csv`.
   - Perhitungan indikator memakai rolling window sehingga bar pertama mungkin berisi `NaN`.
   - Proses pencatatan berlangsung pasif, tidak tergantung ada sinyal trading atau tidak.

2. **Training Manual**
   - Pengguna dapat melatih model kapan saja melalui perintah Telegram `/mltrain <symbol>` atau tombol "Train" di UI Streamlit.
   - Data CSV akan dibersihkan (missing value dibuang), diberi label, lalu dilatih menggunakan `RandomForestClassifier`.
   - Hasil model disimpan ke `models/<symbol>_scalping.pkl` dan akurasi ditampilkan ke pengguna.

3. **Training Otomatis (Mode Test)**
   - Jika bot dijalankan pada mode test dan model belum ada, sistem otomatis mengunduh data 30 hari dari Binance lalu melatih model tersebut sekali saat startup.
   - Fitur ini hanya untuk kemudahan pengujian sehingga tiap simbol baru tetap punya model ML.

4. **Penggunaan Model Saat Trading**
   - Saat berjalan, strategi memuat model dari folder `models/`.
   - Untuk setiap bar baru, indikator dihitung dan model memprediksi `ml_signal` (1 = bias long, 0 = bias short).
   - Sinyal ML digabung dengan indikator klasik untuk menentukan keputusan akhir.

5. **Perilaku Fallback**
   - Jika model tidak ada atau prediksi gagal, sistem memberi peringatan dan `ml_signal` dianggap `1` sehingga strategi tetap berjalan dengan indikator biasa.

6. **Prasyarat Mode Live**
   - Sebelum trading sungguhan, pastikan model sudah dilatih. Tanpa model, sinyal ML selalu `1`.
   - Data log tersimpan di `data/training_data/`, sedangkan model berada di `models/`.

```
Market Data → CSV → Training → Model (*.pkl) → Prediksi ML → Keputusan Trading
```

### 🔁 Update Model Secara Berkala
Untuk performa terbaik, latih ulang model secara rutin dengan data terbaru agar akurasi tetap terjaga.

## 👨‍💻 Pengembang & Dukungan
Bot ini didukung dan didokumentasikan oleh [Shingiwoo].
Support/kontribusi open di [shingiwoo.ind@gmail.com].

---
