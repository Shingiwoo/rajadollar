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

## 🖥️ **Deployment ke VPS Ubuntu (Dockerized)**

1. **Build Docker image:**
    ```sh
    docker build -t rajadollar .
    ```

2. **Run container:**
    ```sh
    docker run -d --env-file .env -p 8501:8501 rajadollar
    ```

3. **Akses bot di browser:**
    ```
    http://<IP_VPS>:8501
    ```

---

## 🌐 **Nginx (Reverse Proxy, Optional)**

1. **Install nginx:**
    ```sh
    sudo apt install nginx
    ```

2. **Konfigurasi file `/etc/nginx/sites-available/rajadollar`:**
    ```
    server {
        listen 80;
        server_name <domain_kamu>;

        location / {
            proxy_pass http://localhost:8501;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```

3. **Aktifkan config:**
    ```sh
    sudo ln -s /etc/nginx/sites-available/rajadollar /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
    ```

---

## 🛠️ **Production Checklist**
- [x] Semua variabel `.env` sudah valid
- [x] Port firewall VPS sudah dibuka (`8501`)
- [x] Bot sudah `/start` di Telegram user
- [x] Running di testnet dulu, baru real!
- [x] Uji semua fitur dengan unit test
- [x] Amankan credential API & hapus debug print di deploy
- [x] Tambahkan HTTPS (Let's Encrypt) jika expose ke public

---

## 👨‍💻 **Pengembang & Dukungan**
Bot ini didukung dan didokumentasikan oleh [Shingiwoo].  
Support/kontribusi open di [shingiwoo.ind@gmail.com].

---