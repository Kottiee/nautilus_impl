"""
ドライラン設定 (BitMEX Testnet)

BitMEX Testnet 環境でのドライラン設定を定義します。
API キーは環境変数から読み込みます。
"""

import os
from decimal import Decimal

from nautilus_trader.adapters.bitmex.common.enums import BitmexAccountType


# ドライラン用トレーダーID
TRADER_ID = "TRADER-DRYRUN-001"

# 取引シンボル（ドライランではまず1シンボルで検証）
SYMBOL = "XBTUSDT"
VENUE = "BITMEX"
TIMEFRAME = "15m"
TRADE_SIZE = Decimal("0.001")

# ストラテジー設定
STRATEGY_NAME = "EMA_CROSS"
FAST_EMA = 10
SLOW_EMA = 20


def get_bitmex_testnet_config() -> dict:
    """BitMEX Testnet 接続設定を返します。"""
    api_key = os.environ.get("BITMEX_TESTNET_API_KEY", "")
    api_secret = os.environ.get("BITMEX_TESTNET_API_SECRET", "")

    if not api_key or not api_secret:
        raise ValueError(
            "BITMEX_TESTNET_API_KEY と BITMEX_TESTNET_API_SECRET 環境変数を設定してください。"
        )

    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "testnet": True,
    }
