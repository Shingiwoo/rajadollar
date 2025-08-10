import argparse
from .engine import backtest_symbols


def main():
    parser = argparse.ArgumentParser(description="Jalankan backtest untuk beberapa simbol")
    parser.add_argument("--symbols", required=True, help="Daftar simbol dipisah koma")
    parser.add_argument("--tf", required=True, help="Timeframe data, misal 15m")
    parser.add_argument("--from", dest="start", required=False, help="Tanggal mulai (YYYY-MM-DD)")
    parser.add_argument("--to", dest="end", required=False, help="Tanggal akhir (YYYY-MM-DD)")
    parser.add_argument("--export", required=True, help="Path berkas JSON hasil")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    backtest_symbols(symbols, args.tf, start=args.start, end=args.end, export_path=args.export)


if __name__ == "__main__":
    main()
