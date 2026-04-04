from __future__ import annotations
from textual.widget import Widget
from textual.app import ComposeResult
from textual_plotext import PlotextPlot

class VolSmilePanel(Widget):
    DEFAULT_CSS = """
    VolSmilePanel { height: 1fr; }
    VolSmilePanel PlotextPlot { height: 1fr; }
    """
    def compose(self) -> ComposeResult:
        yield PlotextPlot(id="smile_chart")

    def update_data(self, smile_data: dict[str, list[tuple[float, float]]], spot_price: float = 0) -> None:
        widget = self.query_one("#smile_chart", PlotextPlot)
        plt = widget.plt
        plt.clear_figure()
        plt.title("Volatility Smile")
        plt.xlabel("Strike Price (USD)")
        plt.ylabel("IV %")
        colors = ["green", "cyan", "yellow", "red", "magenta"]
        for i, (expiry_label, points) in enumerate(smile_data.items()):
            if not points: continue
            strikes = [p[0] for p in points]
            ivs = [p[1] for p in points]
            plt.plot(strikes, ivs, color=colors[i % len(colors)], label=expiry_label)
        if spot_price > 0:
            plt.vline(spot_price, color="white")
        widget.refresh()
