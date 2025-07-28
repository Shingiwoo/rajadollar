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

Strategi dikonfigurasi lewat `config/strategy_params.json`. Model ML akan dilatih otomatis, bisa juga manual dengan `python ml/training.py` atau via Telegram (`/ml`, `/mltrain`).

### FAQ
- **Apakah aman restart?** Ya, data di `runtime_state` dipulihkan otomatis.
- **Bagaimana menghindari rate limit?** Semua panggilan Binance melalui `utils/safe_api.py`.
- **Debugging?** Gunakan perintah `/status`, `/log`, atau cek file log di `logs/`.

---

## 👨‍💻 Pengembang & Dukungan
Bot ini didukung dan didokumentasikan oleh [Shingiwoo].
Support/kontribusi open di [shingiwoo.ind@gmail.com].

---
