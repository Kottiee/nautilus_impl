"""
バックテスト設定

BacktestEngine を使用したバックテストの設定を定義します。
"""

from decimal import Decimal
from pathlib import Path

from nautilus_trader.backtest.engine import BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.objects import Money
from nautilus_trader.test_kit.providers import TestInstrumentProvider

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# データカタログパス
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog"

# 結果出力パス
RESULTS_PATH = PROJECT_ROOT / "results"
TEARSHEETS_PATH = RESULTS_PATH / "tearsheets"
REPORTS_PATH = RESULTS_PATH / "reports"


def get_engine_config() -> BacktestEngineConfig:
    """BacktestEngine の設定を返します。"""
    return BacktestEngineConfig(
        logging=LoggingConfig(log_level="ERROR"),
    )


# Venue設定
VENUE_NAME = "BITMEX"
OMS_TYPE = OmsType.NETTING
ACCOUNT_TYPE = AccountType.MARGIN
STARTING_BALANCE = Money(10_000, "USDT")

# デフォルト取引サイズ
DEFAULT_TRADE_SIZES = {
    "XBTUSDT": Decimal("0.001"),
    "ETHUSDT": Decimal("0.01"),
    "SOLUSDT": Decimal("1.0"),
    "XRPUSDT": Decimal("10.0"),
    "DOGEUSDT": Decimal("100.0"),
}
