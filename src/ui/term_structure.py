from __future__ import annotations
from textual.widget import Widget
from textual.app import ComposeResult
from textual_plotext import PlotextPlot

class TermStructurePanel(Widget):
    DEFAULT_CSS = """
    TermStructurePanel { height: 1fr; }
    TermStructurePanel PlotextPlot { height: 1fr; }
    """
    def compose(self) -> ComposeResult:
        yield PlotextPlot(id="term_chart")

    def update_data(self, term_data: dict[str, list[tuple[int, float]]]) -> None:
        widget = self.query_one("#term_chart", PlotextPlot)
        plt = widget.plt
        plt.clear_figure()
        plt.title("Term Structure (ATM IV)")
        plt.xlabel("Days to Expiry")
        plt.ylabel("ATM IV %")
        colors = {"deribit": "green", "okx": "cyan"}
        for exchange, points in term_data.items():
            if not points: continue
            days = [p[0] for p in points]
            ivs = [p[1] for p in points]
            plt.plot(days, ivs, color=colors.get(exchange, "white"), label=exchange)
        widget.refresh()
