"""
Instrument定義のテスト
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from instruments.definitions import (
    ALL_INSTRUMENTS,
    create_dogeusdt_perpetual,
    create_ethusdt_perpetual,
    create_solusdt_perpetual,
    create_xbtusdt_perpetual,
    create_xrpusdt_perpetual,
)


def test_xbtusdt_perpetual() -> None:
    instrument = create_xbtusdt_perpetual()
    assert str(instrument.id) == "XBTUSDT.BITMEX"
    assert str(instrument.base_currency) == "BTC"
    assert str(instrument.quote_currency) == "USDT"
    assert not instrument.is_inverse


def test_ethusdt_perpetual() -> None:
    instrument = create_ethusdt_perpetual()
    assert str(instrument.id) == "ETHUSDT.BITMEX"
    assert str(instrument.base_currency) == "ETH"
    assert str(instrument.quote_currency) == "USDT"


def test_solusdt_perpetual() -> None:
    instrument = create_solusdt_perpetual()
    assert str(instrument.id) == "SOLUSDT.BITMEX"


def test_xrpusdt_perpetual() -> None:
    instrument = create_xrpusdt_perpetual()
    assert str(instrument.id) == "XRPUSDT.BITMEX"


def test_dogeusdt_perpetual() -> None:
    instrument = create_dogeusdt_perpetual()
    assert str(instrument.id) == "DOGEUSDT.BITMEX"


def test_all_instruments_count() -> None:
    assert len(ALL_INSTRUMENTS) == 5


def test_all_instruments_unique_ids() -> None:
    ids = [str(i.id) for i in ALL_INSTRUMENTS]
    assert len(ids) == len(set(ids)), "Instrument ID が重複しています"
