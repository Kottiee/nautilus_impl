# CLAUDE.md - NautilusTrader Crypto Perpetual Auto-Trading System

## Project Overview

NautilusTraderを使用した仮想通貨Perpetual自動売買システム。
バックテスト、ドライラン（デモ取引）、本番ライブ取引の3環境をサポートする。

### Architecture Decision Records

| 決定事項 | 選定 | 理由 |
|---------|------|------|
| 取引所 | **BitMEX** | NautilusTraderで公式対応 |
| フレームワーク | NautilusTrader >= 1.222.0 | Plotly tearsheet可視化が組み込み済み、Python 3.12+ 対応 |
| バックテスト可視化 | NautilusTrader組み込みtearsheet + `create_bars_with_fills` | エントリー/エグジット位置の目視確認可能 |
| 分析統計 | NautilusTrader組み込みPortfolio Analyzer | Sharpe Ratio, Max Drawdown, Win Rate等のindustry standard指標 |
| データ形式 | Parquet (ParquetDataCatalog) | NautilusTrader標準、高速読み込み |

---

## Technology Stack

- **Python**: 3.12+
- **NautilusTrader**: >= 1.222.0 (`pip install nautilus_trader`)
- **Plotly**: >= 6.3.1 （tearsheet可視化用）
- **pandas**, **numpy**: データ処理
- **Grafana + TimescaleDB**: バックテスト結果のダッシュボード可視化（採用）
- **Docker**: 本番デプロイ用

---

## Project Structure

```
nautilus-trading/
├── CLAUDE.md
├── pyproject.toml
├── README.md
├── docker-compose.yml
├── Dockerfile
├── .env.example                    # API keys template
├── .github/
│   └── workflows/
│       └── backtest.yml            # CI: バックテスト自動実行
│
├── config/
│   ├── backtest.py                 # バックテスト設定
│   ├── dry_run.py                  # ドライラン設定（BitMEX Testnet）
│   └── live.py                     # 本番設定
│
├── data/
│   ├── catalog/                    # ParquetDataCatalog格納先
│   ├── raw/                        # 生データ（CSV等）
│   └── scripts/
│       └── fetch_historical.py     # BitMEXから過去データ取得
│
├── instruments/
│   └── definitions.py              # CryptoPerpetual instrument定義
│
├── strategies/
│   ├── __init__.py
│   ├── ema_cross.py                # EMA CrossoverストラテジーAdapter
│   ├── bollinger_mean_reversion.py # Bollinger Band Mean Reversionストラテジー
│   └── rsi_momentum.py             # RSI Momentumストラテジー
│
├── backtest/
│   ├── __init__.py
│   ├── runner.py                   # バックテスト実行エントリーポイント
│   └── analysis.py                 # 結果分析・tearsheet生成
│
├── live/
│   ├── __init__.py
│   ├── dry_run_node.py             # ドライラン（BitMEX Testnet）
│   └── live_node.py                # 本番ライブ取引
│
├── results/                        # バックテスト結果格納
│   ├── tearsheets/                 # HTML tearsheet
│   └── reports/                    # CSV/JSONレポート
│
└── tests/
    ├── test_strategies.py
    └── test_instruments.py
```

---

## Trading Instruments

BitMEX Perpetualの主要通貨ペア:

| Symbol | Instrument ID | 説明 |
|--------|--------------|------|
| XBTUSDT | `XBTUSDT.BITMEX` | Bitcoin Perpetual |
| ETHUSDT | `ETHUSDT.BITMEX` | Ethereum Perpetual |
| SOLUSDT | `SOLUSDT.BITMEX` | Solana Perpetual |
| XRPUSDT | `XRPUSDT.BITMEX` | XRP Perpetual |
| DOGEUSDT | `DOGEUSDT.BITMEX` | Dogecoin Perpetual |

**BitMEXシンボル命名規則**: Nautilus は `{SYMBOL}.BITMEX` の形式でvenueを識別する。

---

## Strategies

コミュニティで広く使用されている標準的なストラテジーを実装する。
**独自の複雑なロジックは実装しない。NautilusTrader公式examplesおよびコミュニティ実装をベースにする。**

### 1. EMA Cross Strategy (`strategies/ema_cross.py`)

NautilusTrader公式example (`nautilus_trader.examples.strategies.ema_cross`) をベースにCryptoPerpetual向けにadapt。

```python
# 基本パラメータ
fast_ema_period: int = 10
slow_ema_period: int = 20
bar_type: str = "XBTUSDT.BITMEX-15-MINUTE-LAST-EXTERNAL"
trade_size: Decimal = Decimal("0.001")  # BTC単位
```

- Fast EMA > Slow EMA でロング、逆でショート
- NautilusTrader組み込みの `ExponentialMovingAverage` インジケーターを使用
- `register_indicator_for_bars()` でバーデータに自動連動

### 2. Bollinger Band Mean Reversion (`strategies/bollinger_mean_reversion.py`)

```python
# 基本パラメータ
bb_period: int = 20
bb_std: float = 2.0
bar_type: str = "ETHUSDT.BITMEX-15-MINUTE-LAST-EXTERNAL"
trade_size: Decimal = Decimal("0.01")
```

- 価格がLower Bandを下回ったらロング、Upper Bandを上回ったらショート
- NautilusTrader組み込みの `BollingerBands` インジケーターを使用
- ミドルバンド回帰で利確

### 3. RSI Momentum Strategy (`strategies/rsi_momentum.py`)

```python
# 基本パラメータ
rsi_period: int = 14
overbought: float = 70.0
oversold: float = 30.0
bar_type: str = "SOLUSDT.BITMEX-15-MINUTE-LAST-EXTERNAL"
trade_size: Decimal = Decimal("1.0")
```

- RSI < 30 でロング（売られ過ぎ）、RSI > 70 でショート（買われ過ぎ）
- NautilusTrader組み込みの `RelativeStrengthIndex` インジケーターを使用

---

## Implementation Guidelines

### Strategy実装の原則

1. **`Strategy` クラスを継承** し、`StrategyConfig` を定義する
2. `on_start()` で:
   - `self.cache.instrument()` でinstrument取得
   - `self.register_indicator_for_bars()` でインジケーター登録
   - `self.request_bars()` で過去データリクエスト（インジケーター初期化用）
   - `self.subscribe_bars()` でリアルタイムバー購読
3. `on_bar()` で:
   - インジケーターの `initialized` チェック
   - シグナル判定
   - `self.order_factory.market()` でオーダー生成
   - `self.submit_order()` で発注
4. `on_stop()` でクリーンアップ
5. **同一コードでバックテスト・ドライラン・本番で動作** させる（NautilusTraderの設計思想）

### Instrument定義 (`instruments/definitions.py`)

バックテストではカスタム `CryptoPerpetual` instrument定義が必要:

```python
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.model.currencies import BTC, USDT
from nautilus_trader.model.enums import AssetClass

def create_xbtusdt_perpetual() -> CryptoPerpetual:
    return CryptoPerpetual(
        instrument_id=InstrumentId(Symbol("XBTUSDT"), Venue("BITMEX")),
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
        margin_init=Decimal("0.01"),      # 1% = 100x max leverage
        margin_maint=Decimal("0.005"),
        maker_fee=Decimal("0.0002"),       # BitMEX maker fee（例）
        taker_fee=Decimal("0.00075"),      # BitMEX taker fee（例）
        ts_event=0,
        ts_init=0,
        multiplier=Quantity.from_str("1"),
    )
```

**ライブ/ドライランでは `BitmexInstrumentProvider` が自動でinstrumentを取得するため、手動定義不要。**

---

## Backtest Configuration

### BacktestEngine (Low-level API) を使用

```python
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig

engine = BacktestEngine(
    config=BacktestEngineConfig(
        logging=LoggingConfig(log_level="ERROR"),
    )
)

# Venue設定
engine.add_venue(
    venue_name="BITMEX",
    oms_type=OmsType.NETTING,       # Perpetualはnetting
    account_type=AccountType.MARGIN, # マージン取引
    base_currency=None,              # マルチカレンシー
    starting_balances=[Money(10_000, USDT)],
    fill_model=FillModel(
        prob_fill_on_limit=0.2,
        prob_fill_on_stop=0.95,
        prob_slippage=0.5,
        random_seed=42,
    ),
)

# Instrument & Data追加
engine.add_instrument(instrument)
engine.add_data(bars)  # or ticks

# Strategy追加 & 実行
engine.add_strategy(strategy)
engine.run()
```

### データ取得

BitMEXから過去データを取得し、ParquetDataCatalogに格納:

```python
# data/scripts/fetch_historical.py
# ccxtを使ってBitMEXからOHLCVデータを取得し、NautilusTraderのBar形式に変換
import ccxt
import pandas as pd

exchange = ccxt.bitmex()
ohlcv = exchange.fetch_ohlcv("XBT/USDT", timeframe="15m", limit=1000)
df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
```

**注意**: ccxtでデータ取得後、NautilusTraderの `BarDataWrangler` で変換してからcatalogに書き込む。

---

## Backtest Analysis & Visualization

### Industry Standard 分析指標

NautilusTrader組み込みの `PortfolioAnalyzer` が自動計算:

- **Sharpe Ratio** - リスク調整後リターン
- **Sortino Ratio** - 下方リスク調整後リターン
- **Max Drawdown** - 最大ドローダウン
- **Win Rate** - 勝率
- **Profit Factor** - 総利益 / 総損失
- **Average Win / Average Loss** - 平均勝ち / 平均負け
- **Total Return** - 総リターン
- **Annualized Return** - 年率リターン
- **Total Trades** - 総取引数
- **Avg Trade Duration** - 平均保有期間

### Tearsheet生成

```python
from nautilus_trader.analysis.tearsheet import create_tearsheet, create_bars_with_fills
from nautilus_trader.model import BarType

# HTML tearsheet生成（Equity Curve, Drawdown, Monthly Returns等）
create_tearsheet(
    engine=engine,
    output_path="results/tearsheets/ema_cross_tearsheet.html",
    config=TearsheetConfig(
        charts=[
            "stats_table",
            "equity",
            "drawdown",
            "monthly_returns",
            "distribution",
            "rolling_sharpe",
            "yearly_returns",
            "bars_with_fills",  # エントリー位置可視化
        ],
        theme="nautilus",
    ),
)

# エントリー/エグジット位置の目視確認チャート
bar_type = BarType.from_str("XBTUSDT.BITMEX-15-MINUTE-LAST-EXTERNAL")
fig = create_bars_with_fills(
    engine=engine,
    bar_type=bar_type,
    title="BTC Perpetual - Entry/Exit Analysis",
)
fig.write_html("results/tearsheets/btc_fills.html")
```

**`create_bars_with_fills` は**: OHLCローソク足上に緑三角（買い）/赤三角（売り）でエントリー/エグジットポイントを描画する。

### ローソク足 + インジケータ可視化
**採用**: `Grafana + TimescaleDB`

- 運用で使えるダッシュボード機能（複数パネル、期間ズーム、テンプレート変数、共有）
- ローソク足チャートとEMA/Bollinger/RSI等を同一画面で管理しやすい
- 戦略・銘柄・時間足の切替を同一UIで扱える
- Backtestの統計（tearsheet）と分離して、時系列分析を継続的に拡張できる

**役割分担**:
- 統計サマリ: create_tearsheet
- ローソク足 + インジケータ: Grafanaダッシュボード

**備考**: 新規可視化基盤を自作せず、既存プロダクト（Grafana）を利用する。

### CSVレポート出力

```python
# ポジションレポート
positions_report = engine.trader.generate_positions_report()
positions_report.to_csv("results/reports/positions.csv")

# オーダーレポート
orders_report = engine.trader.generate_orders_report()
orders_report.to_csv("results/reports/orders.csv")

# フィルレポート
fills_report = engine.trader.generate_fills_report()
fills_report.to_csv("results/reports/fills.csv")
```

---

## Dry Run (Demo Trading)

BitMEX Testnet環境でのドライラン:

```python
# live/dry_run_node.py
from nautilus_trader.adapters.bitmex import BITMEX
from nautilus_trader.adapters.bitmex import BitmexLiveDataClientFactory, BitmexLiveExecClientFactory
from nautilus_trader.live.node import TradingNode, TradingNodeConfig

config = TradingNodeConfig(
    trader_id="TRADER-DRYRUN-001",
    data_clients={
        BITMEX: {
            "api_key": "${BITMEX_TESTNET_API_KEY}",
            "api_secret": "${BITMEX_TESTNET_API_SECRET}",
            "testnet": True,
        },
    },
    exec_clients={
        BITMEX: {
            "api_key": "${BITMEX_TESTNET_API_KEY}",
            "api_secret": "${BITMEX_TESTNET_API_SECRET}",
            "testnet": True,
        },
    },
)

node = TradingNode(config=config)
node.add_data_client_factory(BITMEX, BitmexLiveDataClientFactory)
node.add_exec_client_factory(BITMEX, BitmexLiveExecClientFactory)

# Strategy追加（バックテストと同一コード）
node.trader.add_strategy(strategy)
node.run()
```

**注意**: BitMEX Testnetでは本番と同様にAPI制限があるため、レート制限とエラーハンドリングを本番同等で扱うこと。

---

## Live Trading (本番)

```python
# live/live_node.py
config = TradingNodeConfig(
    trader_id="TRADER-LIVE-001",
    data_clients={
        BITMEX: {
            "api_key": "${BITMEX_API_KEY}",
            "api_secret": "${BITMEX_API_SECRET}",
            # testnet=False (default)
        },
    },
    exec_clients={
        BITMEX: {
            "api_key": "${BITMEX_API_KEY}",
            "api_secret": "${BITMEX_API_SECRET}",
        },
    },
)
```

---

## Environment Variables

```bash
# .env.example
# BitMEX Live
BITMEX_API_KEY=
BITMEX_API_SECRET=

# BitMEX Testnet (dry run)
BITMEX_TESTNET_API_KEY=
BITMEX_TESTNET_API_SECRET=
```

---

## CI/CD - GitHub Actions

### バックテスト自動実行 (`.github/workflows/backtest.yml`)

```yaml
name: Backtest
on:
  push:
    paths:
      - 'strategies/**'
      - 'backtest/**'
      - 'config/backtest.py'
  pull_request:
    paths:
      - 'strategies/**'

jobs:
  backtest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install nautilus_trader plotly pandas numpy ccxt
      - name: Run backtest
        run: python backtest/runner.py
      - name: Upload tearsheet
        uses: actions/upload-artifact@v4
        with:
          name: backtest-results
          path: results/
```

---

## Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install nautilus_trader plotly pandas numpy

COPY . .

# バックテスト
CMD ["python", "backtest/runner.py"]

# ドライラン: docker run --env-file .env app python live/dry_run_node.py
# 本番:      docker run --env-file .env app python live/live_node.py
```

---

## Development Commands

```bash
# 環境セットアップ
python -m venv .venv
source .venv/bin/activate
pip install nautilus_trader plotly pandas numpy ccxt

# 過去データ取得
python data/scripts/fetch_historical.py

# バックテスト実行
python backtest/runner.py

# ドライラン（BitMEX Testnet）
python live/dry_run_node.py

# 本番ライブ取引
python live/live_node.py
```

---

## Implementation Order (推奨実装順序)

1. **Phase 1: 基盤整備**
   - `pyproject.toml` 作成、依存関係定義
   - `instruments/definitions.py` - CryptoPerpetual instrument定義
    - `data/scripts/fetch_historical.py` - ccxtでBitMEXから過去データ取得
   - ParquetDataCatalogへのデータ格納

2. **Phase 2: ストラテジー実装**
   - `strategies/ema_cross.py` - 公式exampleベース
   - `strategies/bollinger_mean_reversion.py`
   - `strategies/rsi_momentum.py`

3. **Phase 3: バックテスト環境**
   - `config/backtest.py` - バックテスト設定
   - `backtest/runner.py` - 全ストラテジー・全ペアでバックテスト実行
   - `backtest/analysis.py` - tearsheet生成、`create_bars_with_fills` でエントリー可視化
    - Grafanaダッシュボード（TimescaleDB連携）でローソク足+インジケータ表示
   - **初回バックテスト実行し、結果を `results/` に保存**

4. **Phase 4: ドライラン**
   - `config/dry_run.py`
    - `live/dry_run_node.py` - BitMEX Testnet環境テスト

5. **Phase 5: 本番 & CI/CD**
   - `config/live.py`
   - `live/live_node.py`
   - `.github/workflows/backtest.yml`
   - `Dockerfile` & `docker-compose.yml`

---

## Coding Standards

- **型ヒント必須**: すべてのpublicメソッドに型アノテーション
- **Decimal使用**: 金額・数量は `Decimal` 型（浮動小数点は使わない）
- **NautilusTrader規約に従う**: `StrategyConfig` でパラメータ定義、`order_id_tag` でストラテジー識別
- **ログ**: `self.log.info()` / `self.log.warning()` / `self.log.error()` を使用（NautilusTrader組み込みlogger）
- **テスト**: 各ストラテジーの基本動作テストを `tests/` に配置
- **独自実装の排除**: NautilusTrader組み込み機能（インジケーター、オーダー管理、リスクエンジン等）を最大限活用し、車輪の再発明をしない

---

## Key References

- NautilusTrader Docs: https://nautilustrader.io/docs/latest/
- BitMEX Integration: https://nautilustrader.io/docs/nightly/integrations/bitmex/
- Visualization/Tearsheet: https://nautilustrader.io/docs/nightly/concepts/visualization/
- Grafana Docs: https://grafana.com/docs/grafana/latest/
- TimescaleDB Docs: https://docs.timescale.com/
- Strategy Guide: https://nautilustrader.io/docs/latest/concepts/strategies/
- Backtesting Guide: https://nautilustrader.io/docs/latest/concepts/backtesting/
- Reports: https://nautilustrader.io/docs/latest/concepts/reports/
- Instruments (CryptoPerpetual): https://nautilustrader.io/docs/latest/concepts/instruments/
- GitHub Examples: https://github.com/nautechsystems/nautilus_trader/tree/master/examples
- NautilusTrader Discord: https://discord.gg/nautilustrader

---

## Important Notes

- **Bitget非対応について**: NautilusTrader 1.222.0時点でBitgetアダプターは存在しない。公式対応済みのBitMEXを採用し、同一戦略コードでBacktest/DryRun/Liveを運用する。
- **BacktestEngineはシングルプロセス**: 同一プロセスで複数BacktestNode/TradingNodeの並行実行は非対応。順次実行すること
- **ログレベル**: Jupyter使用時は `log_level="ERROR"` 推奨（stdout rate limit超過で停止するため）
- **NautilusTraderはアクティブ開発中**: APIブレイキングチェンジの可能性あり。リリースノートを確認すること
