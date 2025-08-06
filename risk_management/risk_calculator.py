"""Perhitungan ukuran order berdasarkan risiko per transaksi."""


def calculate_order_qty(symbol, entry_price, sl, capital, risk_per_trade, leverage):
    """Hitung jumlah kontrak yang dibeli dengan model fixed fractional.

    Parameter ``leverage`` saat ini tidak mempengaruhi besar risiko dan hanya
    disertakan untuk kompatibilitas antarmuka. Rumus sebelumnya membagi risiko
    dengan faktor leverage yang menyebabkan ukuran posisi terlalu kecil
    (undertrade). Rumus baru memastikan risiko yang diambil sesuai persentase
    modal tanpa dipengaruhi leverage.
    """
    risk_amount = capital * risk_per_trade
    price_diff = abs(entry_price - sl)

    if price_diff == 0:
        return 0

    qty = risk_amount / price_diff
    return max(0, qty)
