FROM python:3.12-slim

WORKDIR /app

# 依存関係インストール
COPY pyproject.toml .
RUN pip install --no-cache-dir nautilus_trader plotly pandas numpy ccxt

# アプリケーションコードをコピー
COPY . .

# デフォルトコマンド（バックテスト）
CMD ["python", "backtest/runner.py"]

# ドライラン: docker run --env-file .env app python live/dry_run_node.py
# 本番:      docker run --env-file .env app python live/live_node.py
