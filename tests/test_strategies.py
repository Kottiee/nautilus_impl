"""
ストラテジーの基本動作テスト

NautilusTrader の BacktestEngine を使用して各ストラテジーが
エラーなく動作することを確認します。
"""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_bars(instrument_id_str: str, bar_type_str: str, n: int = 100) -> list:
    """テスト用のダミーバーデータを生成します。"""
    import random

    from nautilus_trader.model.data import Bar, BarType
    from nautilus_trader.model.objects import Price, Quantity

    bar_type = BarType.from_str(bar_type_str)
    bars = []
    price = 50000.0
    step_ns = 15 * 60 * 1_000_000_000  # 15分 in nanoseconds
    ts = 1_700_000_000_000_000_000  # base timestamp

    for _ in range(n):
        change = random.uniform(-500, 500)
        open_ = price
        close = price + change
        high = max(open_, close) + abs(random.uniform(0, 200))
        low = min(open_, close) - abs(random.uniform(0, 200))
        volume = random.uniform(1, 100)
        price = close

        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(f"{open_:.1f}"),
            high=Price.from_str(f"{high:.1f}"),
            low=Price.from_str(f"{low:.1f}"),
            close=Price.from_str(f"{close:.1f}"),
            volume=Quantity.from_str(f"{volume:.3f}"),
            ts_event=ts,
            ts_init=ts,
        )
        bars.append(bar)
        ts += step_ns

    return bars


def _run_strategy_backtest(strategy_name: str) -> None:
    """指定したストラテジーでバックテストを実行します。"""
    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.config import LoggingConfig
    from nautilus_trader.model.currencies import USDT
    from nautilus_trader.model.data import BarType
    from nautilus_trader.model.enums import AccountType, OmsType
    from nautilus_trader.model.fill_model import FillModel
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.objects import Money

    from instruments.definitions import create_xbtusdt_perpetual
    from strategies.bollinger_mean_reversion import (
        BollingerMeanReversionConfig,
        BollingerMeanReversionStrategy,
    )
    from strategies.ema_cross import EMACrossConfig, EMACrossStrategy
    from strategies.rsi_momentum import RSIMomentumConfig, RSIMomentumStrategy

    instrument = create_xbtusdt_perpetual()
    instrument_id = instrument.id
    bar_type_str = "XBTUSDT.BITMEX-15-MINUTE-LAST-EXTERNAL"
    bar_type = BarType.from_str(bar_type_str)
    instr_id = InstrumentId(Symbol("XBTUSDT"), Venue("BITMEX"))

    engine = BacktestEngine(
        config=BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    )
    engine.add_venue(
        venue="BITMEX",
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=None,
        starting_balances=[Money(10_000, USDT)],
        fill_model=FillModel(random_seed=42),
    )
    engine.add_instrument(instrument)
    engine.add_data(_make_bars("XBTUSDT.BITMEX", bar_type_str, n=200))

    if strategy_name == "EMA_CROSS":
        strategy = EMACrossStrategy(
            config=EMACrossConfig(instrument_id=instr_id, bar_type=bar_type)
        )
    elif strategy_name == "BOLLINGER_MR":
        strategy = BollingerMeanReversionStrategy(
            config=BollingerMeanReversionConfig(instrument_id=instr_id, bar_type=bar_type)
        )
    elif strategy_name == "RSI_MOMENTUM":
        strategy = RSIMomentumStrategy(
            config=RSIMomentumConfig(instrument_id=instr_id, bar_type=bar_type)
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    engine.add_strategy(strategy)
    engine.run()
    engine.dispose()


def test_ema_cross_strategy() -> None:
    _run_strategy_backtest("EMA_CROSS")


def test_bollinger_mean_reversion_strategy() -> None:
    _run_strategy_backtest("BOLLINGER_MR")


def test_rsi_momentum_strategy() -> None:
    _run_strategy_backtest("RSI_MOMENTUM")
