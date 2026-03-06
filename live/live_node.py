"""
本番ライブ取引ノード

BitMEX 本番環境でのライブ取引ノードを起動します。
バックテスト・ドライランと同一のストラテジーコードを使用します。

Usage:
    python live/live_node.py

環境変数:
    BITMEX_API_KEY: BitMEX 本番 API キー
    BITMEX_API_SECRET: BitMEX 本番 API シークレット

警告: 本番環境では実際の資金を使用します。十分なテストを行ってから使用してください。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from nautilus_trader.adapters.bitmex import BITMEX
from nautilus_trader.adapters.bitmex.factories import (
    BitmexLiveDataClientFactory,
    BitmexLiveExecClientFactory,
)
from nautilus_trader.live.node import TradingNode, TradingNodeConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue

from config.live import (
    FAST_EMA,
    SLOW_EMA,
    STRATEGY_NAME,
    SYMBOL,
    TIMEFRAME,
    TRADE_SIZE,
    TRADER_ID,
    VENUE,
    get_bitmex_live_config,
)
from strategies.bollinger_mean_reversion import (
    BollingerMeanReversionConfig,
    BollingerMeanReversionStrategy,
)
from strategies.ema_cross import EMACrossConfig, EMACrossStrategy
from strategies.rsi_momentum import RSIMomentumConfig, RSIMomentumStrategy


def build_bar_type(symbol: str, timeframe: str, venue: str) -> BarType:
    """バータイプ文字列を構築します。"""
    tf_map = {
        "1m": "1-MINUTE",
        "3m": "3-MINUTE",
        "5m": "5-MINUTE",
        "15m": "15-MINUTE",
        "30m": "30-MINUTE",
        "1h": "1-HOUR",
        "4h": "4-HOUR",
        "1d": "1-DAY",
    }
    tf_str = tf_map.get(timeframe, "15-MINUTE")
    return BarType.from_str(f"{symbol}.{venue}-{tf_str}-LAST-EXTERNAL")


def main() -> None:
    live_config = get_bitmex_live_config()

    config = TradingNodeConfig(
        trader_id=TRADER_ID,
        data_clients={
            BITMEX: live_config,
        },
        exec_clients={
            BITMEX: live_config,
        },
    )

    node = TradingNode(config=config)
    node.add_data_client_factory(BITMEX, BitmexLiveDataClientFactory)
    node.add_exec_client_factory(BITMEX, BitmexLiveExecClientFactory)

    instrument_id = InstrumentId(Symbol(SYMBOL), Venue(VENUE))
    bar_type = build_bar_type(SYMBOL, TIMEFRAME, VENUE)

    if STRATEGY_NAME == "EMA_CROSS":
        strategy = EMACrossStrategy(
            config=EMACrossConfig(
                instrument_id=instrument_id,
                bar_type=bar_type,
                fast_ema_period=FAST_EMA,
                slow_ema_period=SLOW_EMA,
                trade_size=TRADE_SIZE,
            )
        )
    elif STRATEGY_NAME == "BOLLINGER_MR":
        strategy = BollingerMeanReversionStrategy(
            config=BollingerMeanReversionConfig(
                instrument_id=instrument_id,
                bar_type=bar_type,
                trade_size=TRADE_SIZE,
            )
        )
    elif STRATEGY_NAME == "RSI_MOMENTUM":
        strategy = RSIMomentumStrategy(
            config=RSIMomentumConfig(
                instrument_id=instrument_id,
                bar_type=bar_type,
                trade_size=TRADE_SIZE,
            )
        )
    else:
        print(f"未対応のストラテジー: {STRATEGY_NAME}")
        sys.exit(1)

    node.trader.add_strategy(strategy)

    try:
        node.build()
        node.run()
    except KeyboardInterrupt:
        print("\nライブ取引停止中...")
    finally:
        node.stop()
        node.dispose()


if __name__ == "__main__":
    main()
