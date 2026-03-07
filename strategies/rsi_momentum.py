"""
RSI Momentum Strategy

RSI < 30 でロング（売られ過ぎ）、RSI > 70 でショート（買われ過ぎ）。
RSI が中央値（50）に戻ったら利確。
"""

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.message import Event
from nautilus_trader.indicators import MovingAverageType, RelativeStrengthIndex
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


class RSIMomentumConfig(StrategyConfig, frozen=True, kw_only=True):
    """RSI Momentum ストラテジーの設定。"""

    instrument_id: InstrumentId
    bar_type: BarType
    rsi_period: int = 14
    overbought: float = 70.0
    oversold: float = 30.0
    trade_size: Decimal = Decimal("1.0")
    order_id_tag: str = "RSI_MOM"


class RSIMomentumStrategy(Strategy):
    """RSI Momentum ストラテジー。

    RSI < oversold でロング（売られ過ぎからの反発）。
    RSI > overbought でショート（買われ過ぎからの反落）。
    RSI が 50 を回帰したら利確。
    """

    def __init__(self, config: RSIMomentumConfig) -> None:
        super().__init__(config)
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.trade_size = config.trade_size
        self.overbought = config.overbought
        self.oversold = config.oversold

        self.rsi = RelativeStrengthIndex(config.rsi_period, MovingAverageType.EXPONENTIAL)

        self._instrument: Instrument | None = None

    def on_start(self) -> None:
        self._instrument = self.cache.instrument(self.instrument_id)
        if self._instrument is None:
            self.log.error(f"instrument が見つかりません: {self.instrument_id}")
            self.stop()
            return

        self.register_indicator_for_bars(self.bar_type, self.rsi)

        self.subscribe_bars(self.bar_type)

        self.log.info(
            f"RSIMomentumStrategy 開始: {self.instrument_id} "
            f"period={self.config.rsi_period} oversold={self.oversold} overbought={self.overbought}"
        )

    def on_bar(self, bar: Bar) -> None:
        if not self.rsi.initialized:
            return

        rsi_val = self.rsi.value

        if self.portfolio.is_flat(self.instrument_id):
            if rsi_val < self.oversold:
                self._enter_long()
            elif rsi_val > self.overbought:
                self._enter_short()
        elif self.portfolio.is_net_long(self.instrument_id):
            if rsi_val >= 50.0:
                self._close_position()
                self.log.info(f"ロング利確: RSI={rsi_val:.2f} >= 50")
        elif self.portfolio.is_net_short(self.instrument_id):
            if rsi_val <= 50.0:
                self._close_position()
                self.log.info(f"ショート利確: RSI={rsi_val:.2f} <= 50")

    def _enter_long(self) -> None:
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self._instrument.make_qty(self.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"ロングエントリー (RSI={self.rsi.value:.2f} 売られ過ぎ): {self.trade_size} @ market")

    def _enter_short(self) -> None:
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=self._instrument.make_qty(self.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"ショートエントリー (RSI={self.rsi.value:.2f} 買われ過ぎ): {self.trade_size} @ market")

    def _close_position(self) -> None:
        self.close_all_positions(self.instrument_id)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.instrument_id)
        self.close_all_positions(self.instrument_id)
        self.log.info("RSIMomentumStrategy 停止")

    def on_event(self, event: Event) -> None:
        pass
