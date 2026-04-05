"""Session analysis endpoint — per-signal and per-exit-reason performance."""

import logging
from collections import defaultdict

from flask import Blueprint, current_app, jsonify

logger = logging.getLogger(__name__)
analysis_bp = Blueprint("analysis", __name__)


def _s():
    return current_app.config["BOT_STATE"]


@analysis_bp.get("/api/analysis")
def get_analysis():
    """Return performance breakdown by signal type and exit reason from in-memory trades."""
    state = _s()
    with state._lock:
        trades = list(state.trades)

    by_signal: dict[str, dict] = defaultdict(lambda: {
        "trades": 0, "wins": 0, "losses": 0, "net_pnl": 0.0,
    })
    by_exit: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "total_pnl": 0.0,
    })
    total_wins = 0
    total_pnl = 0.0

    for t in trades:
        sig = t.signal_type or "UNKNOWN"
        by_signal[sig]["trades"] += 1
        by_signal[sig]["net_pnl"] += t.pnl
        if t.pnl > 0:
            by_signal[sig]["wins"] += 1
            total_wins += 1
        else:
            by_signal[sig]["losses"] += 1
        total_pnl += t.pnl

        reason = t.exit_reason or "unknown"
        by_exit[reason]["count"] += 1
        by_exit[reason]["total_pnl"] += t.pnl

    signal_rows = []
    for sig, d in sorted(by_signal.items()):
        n = d["trades"]
        win_pct = (d["wins"] / n * 100) if n > 0 else 0.0
        signal_rows.append({
            "signal": sig,
            "trades": n,
            "wins": d["wins"],
            "losses": d["losses"],
            "win_pct": round(win_pct, 1),
            "net_pnl": round(d["net_pnl"], 4),
        })

    exit_rows = []
    for reason, d in sorted(by_exit.items()):
        n = d["count"]
        avg = d["total_pnl"] / n if n > 0 else 0.0
        exit_rows.append({
            "reason": reason,
            "count": n,
            "total_pnl": round(d["total_pnl"], 4),
            "avg_pnl": round(avg, 4),
        })

    n_total = len(trades)

    # Profit Factor = Gross Profits / Gross Losses (net_pnl = pnl - fees)
    gross_profit = sum(t.net_pnl for t in trades if t.net_pnl > 0)
    gross_loss = abs(sum(t.net_pnl for t in trades if t.net_pnl <= 0))
    profit_factor = round(gross_profit / gross_loss, 3) if gross_loss > 0 else 0.0

    # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    winning = [t.net_pnl for t in trades if t.net_pnl > 0]
    losing = [t.net_pnl for t in trades if t.net_pnl <= 0]
    avg_win = sum(winning) / len(winning) if winning else 0.0
    avg_loss = abs(sum(losing) / len(losing)) if losing else 0.0
    win_rate_frac = total_wins / n_total if n_total > 0 else 0.0
    expectancy = round(win_rate_frac * avg_win - (1 - win_rate_frac) * avg_loss, 4)

    total_fees = round(sum(t.fees for t in trades), 4)
    fee_drag_pct = round(total_fees / abs(total_pnl) * 100, 1) if total_pnl != 0 else 0.0

    return jsonify({
        "total_trades": n_total,
        "total_wins": total_wins,
        "total_pnl": round(total_pnl, 4),
        "overall_win_pct": round(total_wins / n_total * 100, 1) if n_total > 0 else 0.0,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "total_fees": total_fees,
        "fee_drag_pct": fee_drag_pct,
        "by_signal": signal_rows,
        "by_exit": exit_rows,
    })
