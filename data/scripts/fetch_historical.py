"""
BitMEXから過去データを取得し、ParquetDataCatalogに格納するスクリプト。

Usage:
    python data/scripts/fetch_historical.py [--symbol XBTUSDT] [--timeframe 15m] [--limit 1000]

依存関係: ccxt, nautilus_trader
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def fetch_and_store(
    symbol: str = "XBTUSDT",
    timeframe: str = "15m",
    limit: int = 1000,
    since_dt: datetime | None = None,
) -> None:
    """BitMEXからOHLCVデータを取得し、ParquetDataCatalogに保存します。

    Args:
        symbol: BitMEXシンボル（例: "XBTUSDT"）
        timeframe: 時間足（例: "15m", "1h", "1d"）
        limit: 取得するバー数
        since_dt: 取得開始日時 (UTC)。None の場合は最新の limit 本を取得。
    """
    try:
        import ccxt
    except ImportError:
        print("ccxt がインストールされていません。pip install ccxt を実行してください。")
        sys.exit(1)

    try:
        import pandas as pd
        from nautilus_trader.model.data import Bar, BarSpecification, BarType
        from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
        from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
        from nautilus_trader.model.objects import Price, Quantity
        from nautilus_trader.persistence.catalog import ParquetDataCatalog
    except ImportError:
        print("nautilus_trader がインストールされていません。pip install nautilus_trader を実行してください。")
        sys.exit(1)

    # 時間足を BarAggregation に変換
    timeframe_map: dict[str, tuple[int, BarAggregation]] = {
        "1m": (1, BarAggregation.MINUTE),
        "3m": (3, BarAggregation.MINUTE),
        "5m": (5, BarAggregation.MINUTE),
        "15m": (15, BarAggregation.MINUTE),
        "30m": (30, BarAggregation.MINUTE),
        "1h": (1, BarAggregation.HOUR),
        "4h": (4, BarAggregation.HOUR),
        "1d": (1, BarAggregation.DAY),
    }

    if timeframe not in timeframe_map:
        print(f"未対応の時間足: {timeframe}。対応: {list(timeframe_map.keys())}")
        sys.exit(1)

    step, aggregation = timeframe_map[timeframe]

    # シンボルを ccxt 形式に変換 (例: XBTUSDT → XBT/USDT)
    if symbol.endswith("USDT") and symbol != "XBTUSDT":
        ccxt_symbol = symbol[:-4] + "/USDT"
    elif symbol == "XBTUSDT":
        ccxt_symbol = "XBT/USDT"
    else:
        ccxt_symbol = symbol

    print(f"BitMEX から {ccxt_symbol} {timeframe} データを取得中... (limit={limit})")

    exchange = ccxt.bitmex({"enableRateLimit": True})

    since_ms: int | None = None
    if since_dt is not None:
        since_ms = int(since_dt.timestamp() * 1000)

    ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, since=since_ms, limit=limit)

    if not ohlcv:
        print("データが取得できませんでした。")
        return

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    print(f"{len(df)} 本のバーを取得しました: {df['timestamp'].iloc[0]} 〜 {df['timestamp'].iloc[-1]}")

    # NautilusTrader の Bar オブジェクトに変換
    instrument_id = InstrumentId(Symbol(symbol), Venue("BITMEX"))
    bar_spec = BarSpecification(step=step, aggregation=aggregation, price_type=PriceType.LAST)
    bar_type = BarType(
        instrument_id=instrument_id,
        spec=bar_spec,
        aggregation_source=AggregationSource.EXTERNAL,
    )

    bars: list[Bar] = []
    for _, row in df.iterrows():
        ts_event = int(row["timestamp"].timestamp() * 1_000_000_000)  # nanoseconds
        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(str(row["open"])),
            high=Price.from_str(str(row["high"])),
            low=Price.from_str(str(row["low"])),
            close=Price.from_str(str(row["close"])),
            volume=Quantity.from_str(str(max(row["volume"], 0.001))),
            ts_event=ts_event,
            ts_init=ts_event,
        )
        bars.append(bar)

    # ParquetDataCatalog に保存
    catalog_path = PROJECT_ROOT / "data" / "catalog"
    catalog_path.mkdir(parents=True, exist_ok=True)
    catalog = ParquetDataCatalog(str(catalog_path))
    catalog.write_data(bars)

    print(f"データを {catalog_path} に保存しました。")
    print(f"Bar Type: {bar_type}")


def main() -> None:
    parser = argparse.ArgumentParser(description="BitMEXから過去データを取得してParquetDataCatalogに格納します")
    parser.add_argument(
        "--symbol",
        default="XBTUSDT",
        help="BitMEXシンボル (例: XBTUSDT, ETHUSDT, SOLUSDT) [default: XBTUSDT]",
    )
    parser.add_argument(
        "--timeframe",
        default="15m",
        help="時間足 (例: 1m, 15m, 1h, 1d) [default: 15m]",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="取得するバー数 [default: 1000]",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="取得開始日時 (UTC, ISO 8601形式: 2024-01-01T00:00:00Z)",
    )
    parser.add_argument(
        "--all-symbols",
        action="store_true",
        help="対応する全シンボルのデータを取得します",
    )

    args = parser.parse_args()

    since_dt: datetime | None = None
    if args.since:
        since_dt = datetime.fromisoformat(args.since.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)

    symbols = ["XBTUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"] if args.all_symbols else [args.symbol]

    for sym in symbols:
        fetch_and_store(
            symbol=sym,
            timeframe=args.timeframe,
            limit=args.limit,
            since_dt=since_dt,
        )


if __name__ == "__main__":
    main()
