"""Event study from leading-pressure onset to market-confirmation signals."""

from pathlib import Path

import numpy as np
import pandas as pd

from analysis.market_correction_backtest import at_least, load_frame


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def main() -> None:
    frame, _ = load_frame()
    leading = (
        "p_credit_level", "p_credit_widening", "p_real_level", "p_real_rising",
        "p_nfci_tight", "p_nfci_tightening", "p_curve_inverted", "p_rate_shock",
    )
    confirmation = ("p_momentum_weak", "p_below_high", "p_vix_high", "p_stlfsi_high")
    frame["leading_count"] = frame.loc[:, leading].fillna(False).sum(axis=1)
    frame["confirmation_count"] = frame.loc[:, confirmation].fillna(False).sum(axis=1)
    frame["leading_signal"] = at_least(frame, leading, 3)
    frame["market_confirmation"] = at_least(frame, confirmation, 2)

    valid = frame["leading_signal"].notna() & frame["market_confirmation"].notna() & frame["forward_min_6m"].notna()
    sample = frame.loc[valid].copy()
    prior = sample["leading_signal"].shift(1, fill_value=False).astype(bool)
    onset_mask = sample["leading_signal"].astype(bool) & ~prior
    onset_positions = np.flatnonzero(onset_mask.to_numpy())

    rows = []
    for position in onset_positions:
        current = sample.iloc[position]
        prior_row = sample.iloc[position - 1] if position > 0 else current
        future = sample.iloc[position : min(position + 4, len(sample))]
        sp500_path = sample["sp500"].iloc[position : min(position + 4, len(sample))]
        rows.append({
            "onset_month": str(sample.index[position]),
            "future_6m_min_return_pct": current["forward_min_6m"],
            "future_10pct_correction": bool(current["correction_10"]),
            "leading_count": int(current["leading_count"]),
            "confirmation_count_t0": int(current["confirmation_count"]),
            "confirmed_t0": bool(current["market_confirmation"]),
            "confirmed_within_1m": bool(future["market_confirmation"].iloc[:2].astype(bool).any()),
            "confirmed_within_3m": bool(future["market_confirmation"].astype(bool).any()),
            "vix_t0": current["vix"],
            "vix_change_vs_prior": current["vix"] - prior_row["vix"],
            "vix_max_next_3m": future["vix"].max(),
            "vix_max_change_next_3m": future["vix"].max() - prior_row["vix"],
            "equity_momentum_t0": current["equity_mom_3m"],
            "equity_gap_t0": current["equity_gap_6m"],
            "stlfsi_t0": current["stlfsi"],
            "stlfsi_max_next_3m": future["stlfsi"].max(),
            "sp500_min_return_next_3m": ((sp500_path / current["sp500"] - 1) * 100).min(),
        })

    episodes = pd.DataFrame(rows)
    episodes.to_csv(OUTPUT_DIR / "leading_market_transition_episodes.csv", index=False)

    summary_rows = []
    for group_name, group in {
        "全部信号起点": episodes,
        "信号起点后发生10%回调": episodes[episodes["future_10pct_correction"]],
        "信号起点后未发生10%回调": episodes[~episodes["future_10pct_correction"]],
    }.items():
        summary_rows.append({
            "group": group_name,
            "signal_onsets": len(group),
            "confirmed_t0_pct": group["confirmed_t0"].mean() * 100,
            "confirmed_within_1m_pct": group["confirmed_within_1m"].mean() * 100,
            "confirmed_within_3m_pct": group["confirmed_within_3m"].mean() * 100,
            "median_vix_t0": group["vix_t0"].median(),
            "median_vix_max_next_3m": group["vix_max_next_3m"].median(),
            "median_vix_max_change_next_3m": group["vix_max_change_next_3m"].median(),
            "median_equity_momentum_t0": group["equity_momentum_t0"].median(),
            "median_equity_gap_t0": group["equity_gap_t0"].median(),
            "median_stlfsi_t0": group["stlfsi_t0"].median(),
            "median_forward_6m_min_return": group["future_6m_min_return_pct"].median(),
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUTPUT_DIR / "leading_market_transition_summary.csv", index=False)
    print(summary.to_string(index=False))
    print("\nEPISODES")
    print(episodes.to_string(index=False))


if __name__ == "__main__":
    main()
