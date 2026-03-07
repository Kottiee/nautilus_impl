"""
バックテスト結果分析・tearsheet生成

NautilusTrader 組み込み機能を使用してバックテスト結果を可視化します。
"""

from pathlib import Path


def generate_tearsheet(
    engine: object,
    output_path: Path | str,
    title: str = "Backtest Tearsheet",
    venue: object | None = None,
) -> None:
    """HTML tearsheet を生成します。

    Args:
        engine: BacktestEngine インスタンス (run() 完了後)
        output_path: tearsheet の出力パス (.html)
        title: tearsheet のタイトル
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from nautilus_trader.analysis.reporter import ReportProvider

        account_report = engine.trader.generate_account_report(venue=venue)
        positions_report = engine.trader.generate_positions_report()
        orders_report = engine.trader.generate_orders_report()

        # 簡易HTMLレポートを生成
        _generate_simple_html(
            output_path=output_path,
            title=title,
            account_report=account_report,
            positions_report=positions_report,
            orders_report=orders_report,
        )
        print(f"Tearsheet 生成: {output_path}")

    except Exception as e:
        print(f"Tearsheet 生成エラー: {e}")


def _generate_simple_html(
    output_path: Path,
    title: str,
    account_report: object,
    positions_report: object,
    orders_report: object,
) -> None:
    """シンプルな HTML レポートを生成します。"""
    import pandas as pd

    sections = [
        f"<h1>{title}</h1>",
        "<h2>Account Report</h2>",
    ]

    if account_report is not None:
        df = account_report if isinstance(account_report, pd.DataFrame) else None
        if df is not None and not df.empty:
            sections.append(df.to_html(classes="table table-striped"))

    if positions_report is not None and isinstance(positions_report, pd.DataFrame) and not positions_report.empty:
        sections.append("<h2>Positions</h2>")
        sections.append(positions_report.to_html(classes="table table-striped"))

    if orders_report is not None and isinstance(orders_report, pd.DataFrame) and not orders_report.empty:
        sections.append("<h2>Orders</h2>")
        sections.append(orders_report.to_html(classes="table table-striped"))

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="container mt-4">
{"".join(sections)}
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")


def generate_bars_with_fills_chart(
    engine: object,
    bar_type_str: str,
    output_path: Path | str,
    title: str = "Entry/Exit Analysis",
) -> None:
    """エントリー/エグジット位置をローソク足上に描画した Plotly チャートを生成します。

    Args:
        engine: BacktestEngine インスタンス (run() 完了後)
        bar_type_str: バータイプ文字列 (例: "XBTUSDT.BITMEX-15-MINUTE-LAST-EXTERNAL")
        output_path: 出力パス (.html)
        title: チャートタイトル
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from nautilus_trader.analysis.plotting import create_bars_with_fills
        from nautilus_trader.model.data import BarType

        bar_type = BarType.from_str(bar_type_str)
        fig = create_bars_with_fills(engine=engine, bar_type=bar_type, title=title)
        fig.write_html(str(output_path))
        print(f"Bars with fills チャート生成: {output_path}")
    except Exception as e:
        print(f"Bars with fills チャート生成エラー: {e}")
