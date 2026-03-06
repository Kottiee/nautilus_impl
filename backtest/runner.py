"""
バックテスト実行エントリーポイント

全ストラテジー・全ペアでバックテストを実行し、結果を results/ に保存します。

Usage:
    python backtest/runner.py
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.fill_model import FillModel
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from config.backtest import (
    CATALOG_PATH,
    DEFAULT_TRADE_SIZES,
    REPORTS_PATH,
    TEARSHEETS_PATH,
    VENUE_NAME,
    get_engine_config,
)
from instruments.definitions import (
    create_dogeusdt_perpetual,
    create_ethusdt_perpetual,
    create_solusdt_perpetual,
    create_xbtusdt_perpetual,
    create_xrpusdt_perpetual,
)
from strategies.bollinger_mean_reversion import (
    BollingerMeanReversionConfig,
    BollingerMeanReversionStrategy,
)
from strategies.ema_cross import EMACrossConfig, EMACrossStrategy
from strategies.rsi_momentum import RSIMomentumConfig, RSIMomentumStrategy


def load_bars_from_catalog(
    catalog: ParquetDataCatalog,
    instrument_id_str: str,
    timeframe: str = "15-MINUTE",
) -> list:
    """ParquetDataCatalogからバーデータを読み込みます。"""
    from nautilus_trader.model.data import BarType

    bar_type = BarType.from_str(f"{instrument_id_str}-{timeframe}-LAST-EXTERNAL")
    bars = catalog.bars([str(bar_type)])
    return bars


def run_backtest(
    symbol: str,
    strategy_name: str,
    timeframe: str = "15-MINUTE",
) -> dict | None:
    """指定したシンボルとストラテジーでバックテストを実行します。

    Returns:
        バックテスト結果の統計辞書、またはデータが存在しない場合 None。
    """
    instrument_factories = {
        "XBTUSDT": create_xbtusdt_perpetual,
        "ETHUSDT": create_ethusdt_perpetual,
        "SOLUSDT": create_solusdt_perpetual,
        "XRPUSDT": create_xrpusdt_perpetual,
        "DOGEUSDT": create_dogeusdt_perpetual,
    }

    if symbol not in instrument_factories:
        print(f"未対応のシンボル: {symbol}")
        return None

    instrument = instrument_factories[symbol]()
    instrument_id = instrument.id
    instrument_id_str = f"{symbol}.{VENUE_NAME}"
    trade_size = DEFAULT_TRADE_SIZES.get(symbol, Decimal("0.001"))

    # カタログからバーデータを読み込み
    if not CATALOG_PATH.exists():
        print(f"データカタログが見つかりません: {CATALOG_PATH}")
        print("先に python data/scripts/fetch_historical.py を実行してください。")
        return None

    catalog = ParquetDataCatalog(str(CATALOG_PATH))
    bars = load_bars_from_catalog(catalog, instrument_id_str, timeframe)

    if not bars:
        print(f"バーデータが見つかりません: {instrument_id_str} {timeframe}")
        print("先に python data/scripts/fetch_historical.py を実行してください。")
        return None

    print(f"バックテスト開始: {symbol} × {strategy_name} ({len(bars)} bars)")

    # BacktestEngine 設定
    engine = BacktestEngine(config=get_engine_config())

    engine.add_venue(
        venue=VENUE_NAME,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=None,
        starting_balances=[Money(10_000, USDT)],
        fill_model=FillModel(
            prob_fill_on_limit=0.2,
            prob_fill_on_stop=0.95,
            prob_slippage=0.5,
            random_seed=42,
        ),
    )

    engine.add_instrument(instrument)
    engine.add_data(bars)

    bar_type_str = f"{instrument_id_str}-{timeframe}-LAST-EXTERNAL"

    from nautilus_trader.model.data import BarType
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue

    bar_type = BarType.from_str(bar_type_str)
    instr_id = InstrumentId(Symbol(symbol), Venue(VENUE_NAME))

    if strategy_name == "EMA_CROSS":
        config = EMACrossConfig(
            instrument_id=instr_id,
            bar_type=bar_type,
            trade_size=trade_size,
        )
        strategy = EMACrossStrategy(config=config)
    elif strategy_name == "BOLLINGER_MR":
        config = BollingerMeanReversionConfig(
            instrument_id=instr_id,
            bar_type=bar_type,
            trade_size=trade_size,
        )
        strategy = BollingerMeanReversionStrategy(config=config)
    elif strategy_name == "RSI_MOMENTUM":
        config = RSIMomentumConfig(
            instrument_id=instr_id,
            bar_type=bar_type,
            trade_size=trade_size,
        )
        strategy = RSIMomentumStrategy(config=config)
    else:
        print(f"未対応のストラテジー: {strategy_name}")
        return None

    engine.add_strategy(strategy)
    engine.run()

    # 結果保存
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    report_prefix = f"{symbol}_{strategy_name}"

    positions_report = engine.trader.generate_positions_report()
    if positions_report is not None and not positions_report.empty:
        positions_report.to_csv(REPORTS_PATH / f"{report_prefix}_positions.csv")

    orders_report = engine.trader.generate_orders_report()
    if orders_report is not None and not orders_report.empty:
        orders_report.to_csv(REPORTS_PATH / f"{report_prefix}_orders.csv")

    fills_report = engine.trader.generate_fills_report()
    if fills_report is not None and not fills_report.empty:
        fills_report.to_csv(REPORTS_PATH / f"{report_prefix}_fills.csv")

    from backtest.analysis import generate_tearsheet

    tearsheet_path = TEARSHEETS_PATH / f"{report_prefix}_tearsheet.html"
    generate_tearsheet(engine=engine, output_path=tearsheet_path, title=f"{symbol} {strategy_name}")

    stats = engine.get_stats_pnls_formatted()
    engine.reset()
    engine.dispose()

    print(f"バックテスト完了: {symbol} × {strategy_name}")
    return stats


def main() -> None:
    symbols = ["XBTUSDT", "ETHUSDT", "SOLUSDT"]
    strategies = ["EMA_CROSS", "BOLLINGER_MR", "RSI_MOMENTUM"]

    for symbol in symbols:
        for strategy_name in strategies:
            result = run_backtest(symbol=symbol, strategy_name=strategy_name)
            if result:
                print(f"\n=== {symbol} × {strategy_name} ===")
                for key, val in result.items():
                    print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
