"""
Bollinger Band Mean Reversion Strategy

価格が Lower Band を下回ったらロング、Upper Band を上回ったらショート。
ミドルバンド回帰で利確。
"""

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.message import Event
from nautilus_trader.indicators.bollinger_bands import BollingerBands
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


class BollingerMeanReversionConfig(StrategyConfig, frozen=True):
    """Bollinger Band Mean Reversion ストラテジーの設定。"""

    instrument_id: InstrumentId
    bar_type: BarType
    bb_period: int = 20
    bb_std: float = 2.0
    trade_size: Decimal = Decimal("0.01")
    order_id_tag: str = "BB_MR"


class BollingerMeanReversionStrategy(Strategy):
    """Bollinger Band Mean Reversion ストラテジー。

    価格が Lower Band を下回ったらロング、Upper Band を上回ったらショート。
    ミドルバンド（移動平均）回帰で利確。
    """

    def __init__(self, config: BollingerMeanReversionConfig) -> None:
        super().__init__(config)
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.trade_size = config.trade_size

        self.bb = BollingerBands(config.bb_period, config.bb_std)

        self._instrument: Instrument | None = None

    def on_start(self) -> None:
        self._instrument = self.cache.instrument(self.instrument_id)
        if self._instrument is None:
            self.log.error(f"instrument が見つかりません: {self.instrument_id}")
            self.stop()
            return

        self.register_indicator_for_bars(self.bar_type, self.bb)

        self.request_bars(self.bar_type)
        self.subscribe_bars(self.bar_type)

        self.log.info(
            f"BollingerMeanReversionStrategy 開始: {self.instrument_id} "
            f"period={self.config.bb_period} std={self.config.bb_std}"
        )

    def on_bar(self, bar: Bar) -> None:
        if not self.bb.initialized:
            return

        close = bar.close.as_double()
        upper = self.bb.upper.as_double()
        lower = self.bb.lower.as_double()
        middle = self.bb.middle.as_double()

        if self.portfolio.is_flat(self.instrument_id):
            if close < lower:
                self._enter_long()
            elif close > upper:
                self._enter_short()
        elif self.portfolio.is_net_long(self.instrument_id):
            if close >= middle:
                self._close_position()
                self.log.info(f"ロング利確: close={close:.4f} >= middle={middle:.4f}")
        elif self.portfolio.is_net_short(self.instrument_id):
            if close <= middle:
                self._close_position()
                self.log.info(f"ショート利確: close={close:.4f} <= middle={middle:.4f}")

    def _enter_long(self) -> None:
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self._instrument.make_qty(self.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"ロングエントリー (Lower Band 下抜け): {self.trade_size} @ market")

    def _enter_short(self) -> None:
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=self._instrument.make_qty(self.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"ショートエントリー (Upper Band 上抜け): {self.trade_size} @ market")

    def _close_position(self) -> None:
        self.close_position(self.portfolio.positions_open(self.instrument_id)[0])

    def on_stop(self) -> None:
        self.cancel_all_orders(self.instrument_id)
        self.close_all_positions(self.instrument_id)
        self.log.info("BollingerMeanReversionStrategy 停止")

    def on_event(self, event: Event) -> None:
        pass
