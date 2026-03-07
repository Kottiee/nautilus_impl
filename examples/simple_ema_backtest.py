"""
Simple EMA Cross Backtest Example

Demonstrates a minimal backtest using the EMACrossStrategy
with synthetically generated bar data (no external data required).

Usage:
    python examples/simple_ema_backtest.py
"""

from decimal import Decimal

import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import BTC, USDT
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.test_kit.providers import TestInstrumentProvider

# Import our strategy
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instruments.definitions import create_xbtusdt_perpetual
from strategies.ema_cross import EMACrossConfig, EMACrossStrategy


def generate_synthetic_bars(bar_type: BarType, n: int = 200) -> list[Bar]:
    """Generate simple sine-wave price bars for testing."""
    import math
    import time

    bars = []
    base_price = 50_000.0
    ts_ns = int(pd.Timestamp("2024-01-01").timestamp() * 1e9)
    bar_duration_ns = 15 * 60 * 1_000_000_000  # 15 minutes in nanoseconds

    for i in range(n):
        # Sine wave to create crossover signals
        price = base_price + 1_000 * math.sin(i * 0.15)
        open_ = price
        high = price + 50
        low = price - 50
        close = price + 10 * math.sin(i * 0.3)
        volume = 1.0

        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(f"{open_:.1f}"),
            high=Price.from_str(f"{high:.1f}"),
            low=Price.from_str(f"{low:.1f}"),
            close=Price.from_str(f"{close:.1f}"),
            volume=Quantity.from_str(f"{volume:.3f}"),
            ts_event=ts_ns + i * bar_duration_ns,
            ts_init=ts_ns + i * bar_duration_ns,
        )
        bars.append(bar)

    return bars


def run_backtest() -> None:
    instrument = create_xbtusdt_perpetual()

    bar_type = BarType.from_str("XBTUSDT.BITMEX-15-MINUTE-LAST-EXTERNAL")

    engine = BacktestEngine(
        config=BacktestEngineConfig(
            logging=LoggingConfig(log_level="ERROR"),
        )
    )

    engine.add_venue(
        venue=Venue("BITMEX"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=None,
        starting_balances=[Money(10_000, USDT)],
    )

    engine.add_instrument(instrument)

    bars = generate_synthetic_bars(bar_type, n=200)
    engine.add_data(bars)

    config = EMACrossConfig(
        instrument_id=instrument.id,
        bar_type=bar_type,
        fast_ema_period=10,
        slow_ema_period=20,
        trade_size=Decimal("0.001"),
    )
    strategy = EMACrossStrategy(config=config)
    engine.add_strategy(strategy)

    print("Running EMA Cross backtest on synthetic XBTUSDT data...")
    engine.run()

    # Print summary statistics
    print("\n=== Backtest Results ===")
    stats = engine.trader.generate_account_report(Venue("BITMEX"))
    print(stats)

    orders = engine.trader.generate_orders_report()
    fills = engine.trader.generate_fills_report()
    positions = engine.trader.generate_positions_report()

    print(f"\nTotal orders:    {len(orders)}")
    print(f"Total fills:     {len(fills)}")
    print(f"Total positions: {len(positions)}")

    engine.dispose()
    print("\nDone.")


if __name__ == "__main__":
    run_backtest()
