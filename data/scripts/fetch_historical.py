"""
BitMEXから過去データを取得し、ParquetDataCatalogに格納するスクリプト。

Usage:
    python data/scripts/fetch_historical.py [--symbol XBTUSDT] [--timeframe 15m] [--limit 1000]

依存関係: ccxt, nautilus_trader
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def _to_base_quote(symbol: str) -> tuple[str, str]:
    """Convert project symbol style (e.g. XBTUSDT) to base/quote tuple for lookup."""
    if "/" in symbol:
        base, quote = symbol.split("/", maxsplit=1)
    elif symbol.endswith("USDT"):
        base, quote = symbol[:-4], "USDT"
    else:
        return symbol, ""

    # CCXT uses BTC as unified code for Bitcoin.
    if base == "XBT":
        base = "BTC"

    return base, quote


def _resolve_ccxt_symbol(exchange: object, symbol: str) -> str:
    """Resolve a Nautilus-style symbol into a valid CCXT BitMEX market symbol."""
    base, quote = _to_base_quote(symbol)

    if not quote:
        return symbol

    markets = exchange.load_markets()

    # Prefer linear perpetual market for this project (e.g. BTC/USDT:USDT).
    for market in markets.values():
        if (
            market.get("base") == base
            and market.get("quote") == quote
            and market.get("swap") is True
            and market.get("linear") is True
        ):
            return str(market["symbol"])

    # Fallback to regular market symbol if perpetual contract is unavailable.
    regular_symbol = f"{base}/{quote}"
    if regular_symbol in markets:
        return regular_symbol

    raise ValueError(f"BitMEX でシンボルを解決できません: {symbol}")


def _resolve_fetch_timeframe(timeframe: str) -> tuple[str, int]:
    """Return (source_timeframe, compression_factor) for BitMEX fetch."""
    fallback: dict[str, tuple[str, int]] = {
        "3m": ("1m", 3),
        "15m": ("5m", 3),
        "30m": ("5m", 6),
        "4h": ("1h", 4),
    }
    return fallback.get(timeframe, (timeframe, 1))


def _timeframe_to_pandas_freq(timeframe: str) -> str:
    mapping = {
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1D",
    }
    return mapping[timeframe]


def _timeframe_to_ms(timeframe: str) -> int:
    mapping = {
        "1m": 60_000,
        "5m": 300_000,
        "1h": 3_600_000,
        "1d": 86_400_000,
    }
    return mapping[timeframe]


def _fetch_ohlcv_paginated(
    exchange: object,
    ccxt_symbol: str,
    timeframe: str,
    since_ms: int | None,
    limit: int,
) -> list[list[float]]:
    """Fetch OHLCV with pagination because BitMEX has request size limits."""
    if limit <= 1000 and since_ms is None:
        return exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, since=None, limit=limit)

    tf_ms = _timeframe_to_ms(timeframe)
    current_since = since_ms
    if current_since is None:
        current_since = exchange.milliseconds() - (limit * tf_ms)

    all_rows: list[list[float]] = []
    while len(all_rows) < limit:
        batch_limit = min(1000, limit - len(all_rows))
        batch = exchange.fetch_ohlcv(
            ccxt_symbol,
            timeframe=timeframe,
            since=current_since,
            limit=batch_limit,
        )
        if not batch:
            break

        last_ts = all_rows[-1][0] if all_rows else None
        for row in batch:
            if last_ts is None or row[0] > last_ts:
                all_rows.append(row)
                last_ts = row[0]

        if len(batch) < batch_limit:
            break

        current_since = int(all_rows[-1][0]) + tf_ms

    return all_rows


def _read_existing_intervals_ns(bar_dir: Path) -> list[tuple[int, int]]:
    """Read existing parquet intervals from filenames under a bar directory."""
    if not bar_dir.exists():
        return []

    pattern = re.compile(
        r"^(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})-(\d{9})Z_"
        r"(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})-(\d{9})Z\.parquet$",
    )
    intervals: list[tuple[int, int]] = []

    for file in bar_dir.iterdir():
        if not file.is_file() or file.suffix != ".parquet":
            continue

        name = file.name
        match = pattern.match(name)
        if not match:
            continue

        (
            s_date,
            s_hour,
            s_min,
            s_sec,
            s_ns,
            e_date,
            e_hour,
            e_min,
            e_sec,
            e_ns,
        ) = match.groups()

        start_dt = datetime.fromisoformat(f"{s_date}T{s_hour}:{s_min}:{s_sec}+00:00")
        end_dt = datetime.fromisoformat(f"{e_date}T{e_hour}:{e_min}:{e_sec}+00:00")
        start_ns = int(start_dt.timestamp()) * 1_000_000_000 + int(s_ns)
        end_ns = int(end_dt.timestamp()) * 1_000_000_000 + int(e_ns)
        intervals.append((start_ns, end_ns))

    intervals.sort(key=lambda x: x[0])
    return intervals


def _is_in_intervals(ts_ns: int, intervals: list[tuple[int, int]]) -> bool:
    for start_ns, end_ns in intervals:
        if start_ns <= ts_ns <= end_ns:
            return True
    return False


def _split_by_time_gap(bars: list[object], step_ns: int) -> list[list[object]]:
    """Split bars when there is a large timestamp gap.

    This avoids creating a single wide interval that could span over existing stored ranges.
    """
    if not bars:
        return []

    segments: list[list[object]] = [[bars[0]]]
    max_gap_ns = int(step_ns * 1.5)

    for bar in bars[1:]:
        prev = segments[-1][-1]
        if int(bar.ts_event) - int(prev.ts_event) > max_gap_ns:
            segments.append([bar])
        else:
            segments[-1].append(bar)

    return segments


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

    exchange = ccxt.bitmex({"enableRateLimit": True})
    ccxt_symbol = _resolve_ccxt_symbol(exchange=exchange, symbol=symbol)

    print(f"BitMEX から {ccxt_symbol} {timeframe} データを取得中... (limit={limit})")

    since_ms: int | None = None
    if since_dt is not None:
        since_ms = int(since_dt.timestamp() * 1000)

    source_timeframe, compression = _resolve_fetch_timeframe(timeframe)
    source_limit = limit * compression

    if source_timeframe != timeframe:
        print(
            f"BitMEX は {timeframe} 非対応のため {source_timeframe} で取得後に {timeframe} へ再集計します...",
        )

    ohlcv = _fetch_ohlcv_paginated(
        exchange=exchange,
        ccxt_symbol=ccxt_symbol,
        timeframe=source_timeframe,
        since_ms=since_ms,
        limit=source_limit,
    )

    if not ohlcv:
        print("データが取得できませんでした。")
        return

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    if compression > 1:
        freq = _timeframe_to_pandas_freq(timeframe)
        df = (
            df.set_index("timestamp")
            .resample(freq, label="left", closed="left")
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                },
            )
            .dropna()
            .reset_index()
        )

    if since_dt is None and len(df) > limit:
        df = df.tail(limit).reset_index(drop=True)
    elif since_dt is not None and len(df) > limit:
        df = df.head(limit).reset_index(drop=True)

    print(f"{len(df)} 本のバーを取得しました: {df['timestamp'].iloc[0]} 〜 {df['timestamp'].iloc[-1]}")

    # NautilusTrader の Bar オブジェクトに変換
    instrument_id = InstrumentId(Symbol(symbol), Venue("BITMEX"))
    bar_spec = BarSpecification(step=step, aggregation=aggregation, price_type=PriceType.LAST)
    bar_type = BarType(
        instrument_id=instrument_id,
        bar_spec=bar_spec,
        aggregation_source=AggregationSource.EXTERNAL,
    )

    bars: list[Bar] = []
    for _, row in df.iterrows():
        ts_event = int(row["timestamp"].timestamp() * 1_000_000_000)  # nanoseconds

        # Defensive normalization for occasional malformed upstream candles.
        open_px = float(row["open"])
        high_px = float(row["high"])
        low_px = float(row["low"])
        close_px = float(row["close"])
        normalized_high = max(open_px, high_px, low_px, close_px)
        normalized_low = min(open_px, high_px, low_px, close_px)

        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(str(open_px)),
            high=Price.from_str(str(normalized_high)),
            low=Price.from_str(str(normalized_low)),
            close=Price.from_str(str(close_px)),
            volume=Quantity.from_str(str(max(row["volume"], 0.001))),
            ts_event=ts_event,
            ts_init=ts_event,
        )
        bars.append(bar)

    # ParquetDataCatalog に保存
    catalog_path = PROJECT_ROOT / "data" / "catalog"
    catalog_path.mkdir(parents=True, exist_ok=True)
    catalog = ParquetDataCatalog(str(catalog_path))

    bar_dir = catalog_path / "data" / "bar" / str(bar_type)
    existing_intervals = _read_existing_intervals_ns(bar_dir)

    new_bars = [bar for bar in bars if not _is_in_intervals(int(bar.ts_event), existing_intervals)]

    if not new_bars:
        print("保存対象の新規バーがありません（既存データと重複）。")
        print(f"Bar Type: {bar_type}")
        return

    target_step_ns = {
        "1m": 60_000_000_000,
        "3m": 180_000_000_000,
        "5m": 300_000_000_000,
        "15m": 900_000_000_000,
        "30m": 1_800_000_000_000,
        "1h": 3_600_000_000_000,
        "4h": 14_400_000_000_000,
        "1d": 86_400_000_000_000,
    }[timeframe]

    segments = _split_by_time_gap(new_bars, target_step_ns)
    for segment in segments:
        catalog.write_data(segment)

    print(f"データを {catalog_path} に保存しました。")
    if existing_intervals:
        skipped = len(bars) - len(new_bars)
        print(f"既存重複を {skipped} 本スキップして {len(new_bars)} 本を保存しました。")
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
