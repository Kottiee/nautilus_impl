"""
本番ライブ取引設定

BitMEX 本番環境のライブ取引設定を定義します。
API キーは環境変数から読み込みます。
"""

import os
from decimal import Decimal


# 本番用トレーダーID
TRADER_ID = "TRADER-LIVE-001"

# 取引シンボル
SYMBOL = "XBTUSDT"
VENUE = "BITMEX"
TIMEFRAME = "15m"
TRADE_SIZE = Decimal("0.001")

# ストラテジー設定
STRATEGY_NAME = "EMA_CROSS"
FAST_EMA = 10
SLOW_EMA = 20


def get_bitmex_live_config() -> dict:
    """BitMEX 本番接続設定を返します。"""
    api_key = os.environ.get("BITMEX_API_KEY", "")
    api_secret = os.environ.get("BITMEX_API_SECRET", "")

    if not api_key or not api_secret:
        raise ValueError(
            "BITMEX_API_KEY と BITMEX_API_SECRET 環境変数を設定してください。"
        )

    return {
        "api_key": api_key,
        "api_secret": api_secret,
    }
