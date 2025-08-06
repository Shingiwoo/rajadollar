# RajaDollar_trading

Bot trading scalping crypto modular untuk Binance Futures — siap deploy, bisa dikontrol lewat Streamlit dan Telegram.

Kini RajaDollar hanya entry pada setup paling presisi hasil optimasi, multi-symbol, dan multi-timeframe. Target harian 1–4 sinyal profit dari seluruh pair, menghindari overtrade.

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
├── backtest/
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

Kini tersedia pilihan timeframe (`1m`, `5m`, `15m`) langsung di UI. Semua proses pengambilan data, training, backtest, hingga trading live otomatis memakai timeframe yang dipilih.
Semua pengaturan parameter (timeframe, modal awal, risk per trade, leverage) dapat diatur dari UI dan hanya berlaku untuk sesi pengguna. Global config hanya diubah oleh admin.

3. **Jalankan bot Streamlit UI:**
    ```sh
    streamlit run main.py
    ```

Selama backtest berjalan, akan muncul peringatan agar tidak me-refresh halaman sampai proses selesai.

4. **Jalankan unit test:**
    ```sh
    python -m tests.test_scalping_strategy
    # atau
    pytest tests/
    ```

### Persiapan Data Historical

Pastikan folder penyimpanan data historis tersedia dan dapat ditulis:

```bash
sudo mkdir -p data/historical_data/5m
sudo chown -R 1000:1000 data/historical_data
sudo chmod -R u+w data/historical_data
```

Optimasi dan training akan otomatis memakai data yang sudah ada, melakukan konversi timeframe jika memungkinkan, dan hanya mengunduh baru bila diperlukan.

> **Catatan:** Konfirmasi multi-timeframe membutuhkan minimal 20–30 bar pada timeframe lebih besar (15m/1h), pastikan data historis yang diambil memenuhi syarat tersebut.

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
- Optimasi parameter paralel ringan (default 2 worker, data maks 1000 bar, `n_iter` 30, pencarian acak dengan early stop opsional) dengan progress bar serta penyesuaian `n_iter`, `n_jobs`, dan `max_bars`
- Pencarian lokal sekitar parameter dasar untuk menemukan kombinasi paling presisi dengan batas jumlah transaksi dan profit per trade
- Konfirmasi multi timeframe (5m ke 15m) yang otomatis memperlebar trailing stop saat mode swing
- Audit metrik rolling (winrate, profit factor, sharpe) guna memastikan konsistensi strategi

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
## 🛠️ Deployment Notes

Sebelum menjalankan bot di Docker, siapkan direktori berikut di host:

- `./data/training_data/`
- `./models/`
- `./logs/`
- `./runtime_state/`

Ketika menjalankan container, pasang volume supaya folder tersebut tersimpan di host:

```
-v $PWD/data:/app/data \
-v $PWD/models:/app/models \
-v $PWD/logs:/app/logs \
-v $PWD/runtime_state:/app/runtime_state
```

Contoh perintah lengkap:

```bash
sudo docker run -d \
  --name rajadollar_bot \
  --env-file .env \
  -v $PWD/data:/app/data \
  -v $PWD/models:/app/models \
  -v $PWD/logs:/app/logs \
  -v $PWD/runtime_state:/app/runtime_state \
  -p 8588:8588 \
  rajadollar:latest
```

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
Optimasi strategi kini mencakup semua parameter utama per simbol dan otomatis memperbarui file config setelah proses optimasi selesai.
Kini UI backtest mendukung Optimasi Parameter per-simbol. Jika parameter belum ada, sistem akan otomatis optimasi sebelum backtest.
Setiap simbol dapat memilih jenis engine sinyal melalui field `signal_engine` dengan opsi `legacy` atau `pythontrading_style`.

Konfigurasi tambahan tersedia di `config/strategy.json`:

```
{
  "enable_optimizer": true,
  "manual_parameters": {
    "DEFAULT": { ... }
  }
}
```

Mulai sekarang, parameter manual indikator bisa diatur spesifik untuk setiap simbol. Form UI akan otomatis menyesuaikan. Jika `enable_optimizer` bernilai `false`, proses optimasi dilewati dan setiap simbol menggunakan parameter manual masing-masing. Bila diaktifkan, backend akan mencari kombinasi optimal secara otomatis (proses ini dapat memakan waktu dan CPU).
Tambahan: ketika `use_optimizer` bernilai `false`, backtest langsung memakai parameter manual tanpa menjalankan optimizer.

Jika penyimpanan ke `config/strategy_params.json` gagal karena izin, parameter optimal tetap tersedia di memori untuk sesi berjalan. Unduh manual atau perbaiki izin dengan:

```
sudo chown -R 1000:1000 config
sudo chmod -R u+w config
```

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

Penjelasan rinci tentang proses inference tersedia di [docs/ml_inference.md](docs/ml_inference.md).

1. **Pencatatan Indikator**
   - Setiap simbol yang dipantau akan terus mencatat data pasar dan indikator (EMA, SMA, MACD, RSI).
   - Data bar terbaru selalu ditambahkan ke `data/training_data/<symbol>_<tf>.csv`.
   - Perhitungan indikator memakai rolling window sehingga bar pertama mungkin berisi `NaN`.
   - Proses pencatatan berlangsung pasif, tidak tergantung ada sinyal trading atau tidak.

2. **Training Manual**
   - Pengguna dapat melatih model kapan saja melalui perintah Telegram `/mltrain <symbol>` atau tombol "Train" di UI Streamlit.
   - Data CSV akan dibersihkan (missing value dibuang), diberi label, lalu dilatih menggunakan `RandomForestClassifier`.
   - Proses training otomatis melabeli data jika kolom `label` belum ada. Pengguna tidak perlu menjalankan labeling manual.
   - Hasil model disimpan ke `models/<symbol>_scalping_<tf>.pkl` dan akurasi ditampilkan ke pengguna.

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
# Penjelasan Parameter Strategi

Berikut adalah penjelasan parameter yang digunakan dalam strategi trading ini, yang dapat dikonfigurasi dalam file JSON untuk menyesuaikan perilaku strategi per simbol (pair/coin).

## Indikator & Sinyal

### `ema_period`
- **Deskripsi**: Periode (jumlah bar) untuk menghitung *Exponential Moving Average* (EMA).
- **Fungsi**: Digunakan untuk mendeteksi arah tren harga utama.

### `sma_period`
- **Deskripsi**: Periode untuk menghitung *Simple Moving Average* (SMA).
- **Fungsi**: Dibandingkan dengan EMA untuk mengkonfirmasi tren (EMA > SMA = *uptrend*).

### `rsi_period`
- **Deskripsi**: Periode untuk menghitung *Relative Strength Index* (RSI).
- **Fungsi**: Mendeteksi momentum pasar dan area *overbought*/*oversold*.

### `macd_fast`, `macd_slow`, `macd_signal`
- **Deskripsi**:
  - `macd_fast`: Periode EMA cepat pada *MACD*.
  - `macd_slow`: Periode EMA lambat pada *MACD*.
  - `macd_signal`: Periode SMA pada *MACD signal line*.
- **Fungsi**: Kombinasi ini digunakan untuk mendeteksi momentum tren (*bullish*/*bearish* crossover).

## Scoring & Filter Sinyal

### `score_threshold`
- **Deskripsi**: Nilai skor total minimum (akumulasi scoring indikator & ML) agar sinyal *entry* dianggap valid.
- **Contoh**: Jika `threshold = 2.0`, hanya *entry* jika kombinasi (trend + ML, atau trend + RSI + MACD, dll.) bernilai >= 2.0.

### `ml_weight`
- **Deskripsi**: Bobot/skor kontribusi sinyal dari *machine learning* (ML).
- **Fungsi**: Jika ML memprediksi searah, skor ML = 1.0. Nilai ini dapat diubah sesuai tingkat kepercayaan pada model.

### `use_crossover_filter`
- **Deskripsi**: Jika `True`, sinyal tren hanya diberikan saat terjadi persilangan EMA/SMA (*cross up/down*) pada bar saat ini.
- **Fungsi**: Membatasi sinyal hanya pada awal tren, bukan selama tren berjalan.

### `only_trend_15m`
- **Deskripsi**: Jika `True`, *entry* hanya dilakukan jika tren pada timeframe lebih tinggi (15 menit) searah dengan sinyal.
- **Fungsi**: Jika `False`, memungkinkan *entry* counter-trend pada timeframe tinggi.

## Risk Management & Exit

### `sl_min_pct`
- **Deskripsi**: Jarak minimal *Stop Loss* (SL) dari harga *entry* (dalam persen).
- **Contoh**: `1.0` = SL minimal 1% dari harga *entry*.

### `sl_atr_multiplier`
- **Deskripsi**: Jarak *Stop Loss* berdasarkan *Average True Range* (ATR).
- **Fungsi**: SL = *entry* ± (ATR × multiplier). Membuat SL adaptif terhadap volatilitas.

### `tp_rr`
- **Deskripsi**: Rasio *Target Profit* (TP) terhadap SL (*Risk Reward Ratio*).
- **Contoh**: `2.0` berarti TP = 2 × SL.

### `trailing_enabled`
- **Deskripsi**: Mengaktifkan atau menonaktifkan *trailing stop-loss*.

### `trailing_mode`
- **Deskripsi**: Mode *trailing*:
  - `"pct"`: *Trailing offset* dalam persen.
  - `"atr"`: *Trailing* berbasis ATR.
- **Fungsi**: Menentukan cara perhitungan *trailing stop-loss*.

### `atr_multiplier`
- **Deskripsi**: Digunakan untuk *trailing stop-loss* berbasis ATR.
- **Fungsi**: *Trailing SL offset* = ATR × `atr_multiplier`.

## Trailing & Breakeven

### `breakeven_trigger_pct`
- **Deskripsi**: Persentase profit dari *entry* (misal 0.5%) yang memicu pergeseran SL ke *breakeven* (modal).

### `trailing_offset_pct`
- **Deskripsi**: Offset *trailing stop-loss* dari harga tertinggi (atau terendah), dalam persen.

### `trailing_trigger_pct`
- **Deskripsi**: *Trailing* baru aktif setelah profit mencapai persentase tertentu dari *entry*.

## Mode Swing (Trend Kuat)

### `swing_atr_multiplier`
- **Deskripsi**: Offset *trailing*/*SL* untuk mode *swing* (mengikuti tren besar), menggunakan ATR × multiplier.
- **Fungsi**: Umumnya lebih lebar dari mode *scalp*.

### `swing_breakeven_trigger_pct`
- **Deskripsi**: Persentase profit untuk memicu *breakeven* pada mode *swing*.

### `swing_trailing_offset_pct`
- **Deskripsi**: Offset *trailing stop-loss* untuk mode *swing*, dalam persen.

### `swing_trailing_trigger_pct`
- **Deskripsi**: Persentase profit yang memicu aktivasi *trailing* pada mode *swing*.

## Filter Market & Limitasi Trading

### `min_bb_width`
- **Deskripsi**: Lebar minimal *Bollinger Band* (persen dari harga).
- **Fungsi**: Jika pasar terlalu sepi (*sideways*, lebar BB sempit), sinyal tidak dikeluarkan untuk menghindari *noise*/*fake breakout*.

### `max_trades_per_day`
- **Deskripsi**: Batas maksimal jumlah trade per hari untuk simbol ini.
- **Fungsi**: Mengontrol *overtrading*.

## Catatan Umum
- Semua parameter dapat berbeda per simbol (pair/coin).
- Kombinasi parameter menentukan karakter strategi: frekuensi sinyal, selektivitas, ketat/lebarnya SL/TP, dan cara *trailing*.
- Config JSON bersifat modular, memungkinkan penyesuaian untuk satu simbol tanpa mengubah simbol lain.

### 🔁 Update Model Secara Berkala
Untuk performa terbaik, latih ulang model secara rutin dengan data terbaru agar akurasi tetap terjaga.

## 👨‍💻 Pengembang & Dukungan
Bot ini didukung dan didokumentasikan oleh [Shingiwoo].
Support/kontribusi open di [shingiwoo.ind@gmail.com].

---
