# Inference Model Machine Learning

Modul ini menerangkan cara penggunaan model Machine Learning saat backtest untuk membentuk sinyal trading.

## 1. Memuat Model per Simbol
- Ketika backtest dimulai untuk suatu simbol, sistem mencoba memuat model dari `models/{symbol}_scalping.pkl`.
- Fungsi `load_ml_model(symbol)` memakai `pickle.load` untuk memuat model yang telah dilatih.
- Model disimpan di memori agar tidak perlu dimuat ulang pada setiap bar.

## 2. Menyusun Fitur Masukan
- Fitur harus sama persis seperti saat pelatihan.
- Dari bar terakhir, ambil indikator: `EMA`, `SMA`, `MACD`, `RSI`.
- Susun ke dalam `DataFrame` dengan urutan kolom yang identik dengan data pelatihan.
- Gunakan `ffill` untuk mengisi `NaN` sebelum prediksi.

## 3. Prediksi Sinyal
- Lakukan `model.predict(features)` untuk mendapat `ml_signal`.
- Nilai `1` berarti bias naik, `0` berarti bias turun.
- Sinyal disimpan sebagai kolom `ml_signal` pada `DataFrame`.

## 4. Penanganan Kesalahan
- Bila file model tidak ada atau gagal dimuat, tampilkan peringatan dan gunakan `ml_signal = 1`.
- Jika fitur mengandung `NaN` atau `predict` melempar kesalahan, log masalah dan set `ml_signal = 1`.

## 5. Penggunaan di Strategi
- Strategi hanya membuka posisi jika `ml_signal` searah dengan indikator teknikal.
- Kondisi long mensyaratkan `ml_signal == 1`, kondisi short mensyaratkan `ml_signal == 0`.
- Kombinasi ini membentuk sinyal hibrida antara indikator klasik dan model ML.

Dengan modul inference ini, backtest meniru perilaku strategi yang memanfaatkan Machine Learning secara tangguh.
