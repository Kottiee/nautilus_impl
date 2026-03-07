"""
EMA Cross Strategy

NautilusTrader 公式 example (nautilus_trader.examples.strategies.ema_cross) を
ベースに CryptoPerpetual 向けにアダプトしたストラテジー。

Fast EMA > Slow EMA でロング、逆でショート。
"""

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.message import Event
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


class EMACrossConfig(StrategyConfig, frozen=True, kw_only=True):
    """EMA Cross ストラテジーの設定。"""

    instrument_id: InstrumentId
    bar_type: BarType
    fast_ema_period: int = 10
    slow_ema_period: int = 20
    trade_size: Decimal = Decimal("0.001")
    order_id_tag: str = "EMA_CROSS"


class EMACrossStrategy(Strategy):
    """EMA Crossover ストラテジー。

    Fast EMA が Slow EMA を上抜けたらロング、下抜けたらショートエントリー。
    反対シグナルが発生したらポジションを反転させる。
    """

    def __init__(self, config: EMACrossConfig) -> None:
        super().__init__(config)
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.trade_size = config.trade_size

        self.fast_ema = ExponentialMovingAverage(config.fast_ema_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema_period)

        self._instrument: Instrument | None = None

    def on_start(self) -> None:
        self._instrument = self.cache.instrument(self.instrument_id)
        if self._instrument is None:
            self.log.error(f"instrument が見つかりません: {self.instrument_id}")
            self.stop()
            return

        self.register_indicator_for_bars(self.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.bar_type, self.slow_ema)

        self.subscribe_bars(self.bar_type)

        self.log.info(f"EMACrossStrategy 開始: {self.instrument_id} fast={self.config.fast_ema_period} slow={self.config.slow_ema_period}")

    def on_bar(self, bar: Bar) -> None:
        if not self.fast_ema.initialized or not self.slow_ema.initialized:
            return

        fast_val = self.fast_ema.value
        slow_val = self.slow_ema.value

        if fast_val > slow_val:
            if self.portfolio.is_flat(self.instrument_id):
                self._enter_long()
            elif self.portfolio.is_net_short(self.instrument_id):
                self._close_position()
                self._enter_long()
        elif fast_val < slow_val:
            if self.portfolio.is_flat(self.instrument_id):
                self._enter_short()
            elif self.portfolio.is_net_long(self.instrument_id):
                self._close_position()
                self._enter_short()

    def _enter_long(self) -> None:
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self._instrument.make_qty(self.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"ロングエントリー: {self.trade_size} @ market")

    def _enter_short(self) -> None:
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=self._instrument.make_qty(self.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"ショートエントリー: {self.trade_size} @ market")

    def _close_position(self) -> None:
        self.close_all_positions(self.instrument_id)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.instrument_id)
        self.close_all_positions(self.instrument_id)
        self.log.info("EMACrossStrategy 停止")

    def on_event(self, event: Event) -> None:
        pass
