"""
CryptoPerpetual instrument定義

バックテスト用のBitMEX Perpetualインストゥルメントを定義します。
ライブ/ドライランでは BitmexInstrumentProvider が自動で取得するため不要です。
"""

from decimal import Decimal

from nautilus_trader.model.currencies import BTC, ETH, USDT
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity

BITMEX = Venue("BITMEX")


def create_xbtusdt_perpetual() -> CryptoPerpetual:
    """Bitcoin/USDT Perpetual (XBTUSDT.BITMEX) を作成します。"""
    return CryptoPerpetual(
        instrument_id=InstrumentId(Symbol("XBTUSDT"), BITMEX),
        raw_symbol=Symbol("XBTUSDT"),
        base_currency=BTC,
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=1,
        size_precision=3,
        price_increment=Price.from_str("0.1"),
        size_increment=Quantity.from_str("0.001"),
        max_quantity=Quantity.from_str("100.0"),
        min_quantity=Quantity.from_str("0.001"),
        max_notional=None,
        min_notional=Money(5, USDT),
        max_price=Price.from_str("1000000.0"),
        min_price=Price.from_str("0.1"),
        margin_init=Decimal("0.01"),
        margin_maint=Decimal("0.005"),
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.00075"),
        ts_event=0,
        ts_init=0,
        multiplier=Quantity.from_str("1"),
    )


def create_ethusdt_perpetual() -> CryptoPerpetual:
    """Ethereum/USDT Perpetual (ETHUSDT.BITMEX) を作成します。"""
    return CryptoPerpetual(
        instrument_id=InstrumentId(Symbol("ETHUSDT"), BITMEX),
        raw_symbol=Symbol("ETHUSDT"),
        base_currency=ETH,
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=2,
        size_precision=2,
        price_increment=Price.from_str("0.01"),
        size_increment=Quantity.from_str("0.01"),
        max_quantity=Quantity.from_str("10000.0"),
        min_quantity=Quantity.from_str("0.01"),
        max_notional=None,
        min_notional=Money(5, USDT),
        max_price=Price.from_str("100000.0"),
        min_price=Price.from_str("0.01"),
        margin_init=Decimal("0.01"),
        margin_maint=Decimal("0.005"),
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.00075"),
        ts_event=0,
        ts_init=0,
        multiplier=Quantity.from_str("1"),
    )


def _create_usdt_perpetual(
    symbol: str,
    price_precision: int,
    size_precision: int,
    price_increment: str,
    size_increment: str,
    min_quantity: str,
    max_quantity: str,
    max_price: str,
) -> CryptoPerpetual:
    """USDT建てPerpetualインストゥルメントの汎用ファクトリ。"""
    from nautilus_trader.model.currencies import Currency

    base_ccy = Currency.from_str(symbol.replace("USDT", ""))

    return CryptoPerpetual(
        instrument_id=InstrumentId(Symbol(symbol), BITMEX),
        raw_symbol=Symbol(symbol),
        base_currency=base_ccy,
        quote_currency=USDT,
        settlement_currency=USDT,
        is_inverse=False,
        price_precision=price_precision,
        size_precision=size_precision,
        price_increment=Price.from_str(price_increment),
        size_increment=Quantity.from_str(size_increment),
        max_quantity=Quantity.from_str(max_quantity),
        min_quantity=Quantity.from_str(min_quantity),
        max_notional=None,
        min_notional=Money(5, USDT),
        max_price=Price.from_str(max_price),
        min_price=Price.from_str(price_increment),
        margin_init=Decimal("0.01"),
        margin_maint=Decimal("0.005"),
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.00075"),
        ts_event=0,
        ts_init=0,
        multiplier=Quantity.from_str("1"),
    )


def create_solusdt_perpetual() -> CryptoPerpetual:
    """Solana/USDT Perpetual (SOLUSDT.BITMEX) を作成します。"""
    return _create_usdt_perpetual(
        symbol="SOLUSDT",
        price_precision=3,
        size_precision=1,
        price_increment="0.001",
        size_increment="0.1",
        min_quantity="0.1",
        max_quantity="100000.0",
        max_price="10000.0",
    )


def create_xrpusdt_perpetual() -> CryptoPerpetual:
    """XRP/USDT Perpetual (XRPUSDT.BITMEX) を作成します。"""
    return _create_usdt_perpetual(
        symbol="XRPUSDT",
        price_precision=4,
        size_precision=0,
        price_increment="0.0001",
        size_increment="1",
        min_quantity="1",
        max_quantity="10000000.0",
        max_price="1000.0",
    )


def create_dogeusdt_perpetual() -> CryptoPerpetual:
    """Dogecoin/USDT Perpetual (DOGEUSDT.BITMEX) を作成します。"""
    return _create_usdt_perpetual(
        symbol="DOGEUSDT",
        price_precision=5,
        size_precision=0,
        price_increment="0.00001",
        size_increment="1",
        min_quantity="1",
        max_quantity="100000000.0",
        max_price="100.0",
    )


ALL_INSTRUMENTS: list[CryptoPerpetual] = [
    create_xbtusdt_perpetual(),
    create_ethusdt_perpetual(),
    create_solusdt_perpetual(),
    create_xrpusdt_perpetual(),
    create_dogeusdt_perpetual(),
]
