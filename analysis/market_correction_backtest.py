"""Backtest combinations of credit, rate and market-stress signals.

This analysis is intentionally separate from the Streamlit application.  It
uses monthly observations and asks whether information available at month-end
is followed by a material S&P 500 decline over the next three or six months.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from core.macro_data import _fred, _yahoo


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
TRAIN_END = pd.Period("2016-12", freq="M")


def monthly(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").dropna().copy()
    values.index = pd.to_datetime(values.index).to_period("M")
    return values.groupby(level=0).last().sort_index()


def forward_min_return(series: pd.Series, horizon: int) -> pd.Series:
    """Worst close-to-signal-date return during the next ``horizon`` months."""
    result = pd.Series(np.nan, index=series.index, dtype=float)
    values = series.to_numpy(dtype=float)
    for i in range(len(series) - horizon):
        result.iloc[i] = np.min(values[i + 1 : i + horizon + 1] / values[i] - 1.0)
    return result


def causal_percentile(series: pd.Series, window: int = 120, minimum: int = 60) -> pd.Series:
    """Percentile of the current value using only the trailing history."""
    values = pd.to_numeric(series, errors="coerce")
    output = pd.Series(np.nan, index=values.index, dtype=float)
    for i, value in enumerate(values):
        if pd.isna(value):
            continue
        history = values.iloc[max(0, i - window + 1) : i + 1].dropna()
        if len(history) >= minimum:
            output.iloc[i] = float((history <= value).mean())
    return output


def load_frame() -> tuple[pd.DataFrame, dict[str, tuple[str, str, tuple[str, ...]]]]:
    raw = {
        "sp500": _yahoo("^GSPC"),
        "vix": _fred("VIXCLS"),
        "y10": _fred("DGS10"),
        "y3m": _fred("DGS3MO"),
        "stlfsi": _fred("STLFSI4"),
        "hy_oas": _fred("BAMLH0A0HYM2"),
        "baa10y": _fred("BAA10Y"),
        "real_yield": _fred("DFII10"),
        "nfci": _fred("NFCI"),
    }
    frame = pd.concat({key: monthly(value) for key, value in raw.items()}, axis=1).sort_index()

    frame["equity_mom_3m"] = frame["sp500"].pct_change(3) * 100
    frame["equity_gap_6m"] = (frame["sp500"] / frame["sp500"].rolling(6).max() - 1) * 100
    frame["y10_change_3m"] = frame["y10"].diff(3) * 100
    frame["curve_10y3m"] = (frame["y10"] - frame["y3m"]) * 100
    frame["hy_oas_bp"] = frame["hy_oas"] * 100
    frame["hy_oas_change_3m"] = frame["hy_oas"].diff(3) * 100
    frame["baa10y_bp"] = frame["baa10y"] * 100
    frame["baa10y_change_3m"] = frame["baa10y"].diff(3) * 100
    frame["real_yield_change_3m"] = frame["real_yield"].diff(3) * 100
    frame["nfci_change_3m"] = frame["nfci"].diff(3)
    frame["forward_min_3m"] = forward_min_return(frame["sp500"], 3) * 100
    frame["forward_min_6m"] = forward_min_return(frame["sp500"], 6) * 100
    frame["correction_10"] = frame["forward_min_6m"] <= -10
    frame["correction_15"] = frame["forward_min_6m"] <= -15

    definitions = {
        "credit_level": ("BAA−10Y信用利差 ≥300bp", "baa10y_bp >= 300", ("baa10y_bp",)),
        "credit_widening": ("BAA−10Y三个月扩大 ≥100bp", "baa10y_change_3m >= 100", ("baa10y_change_3m",)),
        "real_level": ("10Y实际利率 ≥2%", "real_yield >= 2", ("real_yield",)),
        "real_rising": ("10Y实际利率三个月上升 ≥50bp", "real_yield_change_3m >= 50", ("real_yield_change_3m",)),
        "nfci_tight": ("NFCI ≥0", "nfci >= 0", ("nfci",)),
        "nfci_tightening": ("NFCI三个月上升 ≥0.15", "nfci_change_3m >= 0.15", ("nfci_change_3m",)),
        "curve_inverted": ("10Y−3M ≤0bp", "curve_10y3m <= 0", ("curve_10y3m",)),
        "rate_shock": ("10Y三个月上升 ≥80bp", "y10_change_3m >= 80", ("y10_change_3m",)),
        "momentum_weak": ("标普三个月收益 ≤−5%", "equity_mom_3m <= -5", ("equity_mom_3m",)),
        "below_high": ("标普距六个月高点 ≤−8%", "equity_gap_6m <= -8", ("equity_gap_6m",)),
        "vix_high": ("VIX ≥25", "vix >= 25", ("vix",)),
        "stlfsi_high": ("STLFSI ≥0.32", "stlfsi >= 0.32", ("stlfsi",)),
    }
    for key, (_label, expression, sources) in definitions.items():
        values = frame.eval(expression).astype("boolean")
        missing = frame.loc[:, list(sources)].isna().any(axis=1)
        frame[key] = values.mask(missing, pd.NA)

    percentile_inputs = {
        "p_credit_level": ("baa10y_bp", "high"),
        "p_credit_widening": ("baa10y_change_3m", "high"),
        "p_real_level": ("real_yield", "high"),
        "p_real_rising": ("real_yield_change_3m", "high"),
        "p_nfci_tight": ("nfci", "high"),
        "p_nfci_tightening": ("nfci_change_3m", "high"),
        "p_curve_inverted": ("curve_10y3m", "low"),
        "p_rate_shock": ("y10_change_3m", "high"),
        "p_momentum_weak": ("equity_mom_3m", "low"),
        "p_below_high": ("equity_gap_6m", "low"),
        "p_vix_high": ("vix", "high"),
        "p_stlfsi_high": ("stlfsi", "high"),
    }
    for key, (source, direction) in percentile_inputs.items():
        percentile = causal_percentile(frame[source])
        frame[key] = (percentile >= 0.80 if direction == "high" else percentile <= 0.20).astype("boolean").mask(percentile.isna(), pd.NA)
    return frame, definitions


def confusion(signal: pd.Series, target: pd.Series) -> dict[str, float]:
    valid = signal.notna() & target.notna()
    signal = signal[valid].astype(bool)
    target = target[valid].astype(bool)
    tp = int((signal & target).sum())
    fp = int((signal & ~target).sum())
    fn = int((~signal & target).sum())
    tn = int((~signal & ~target).sum())
    precision = tp / (tp + fp) if tp + fp else np.nan
    recall = tp / (tp + fn) if tp + fn else np.nan
    false_positive_rate = fp / (fp + tn) if fp + tn else np.nan
    base_rate = float(target.mean())
    return {
        "n": len(target),
        "signals": int(signal.sum()),
        "tp": tp,
        "fp": fp,
        "precision": precision,
        "recall": recall,
        "false_positive_rate": false_positive_rate,
        "base_rate": base_rate,
        "lift": precision / base_rate if base_rate and not np.isnan(precision) else np.nan,
    }


def at_least(frame: pd.DataFrame, names: tuple[str, ...], count: int) -> pd.Series:
    inputs = frame.loc[:, names]
    result = (inputs.fillna(False).sum(axis=1) >= count).astype("boolean")
    return result.mask(inputs.isna().any(axis=1), pd.NA)


def all_of(frame: pd.DataFrame, names: tuple[str, ...]) -> pd.Series:
    inputs = frame.loc[:, names]
    result = inputs.fillna(False).all(axis=1).astype("boolean")
    return result.mask(inputs.isna().any(axis=1), pd.NA)


def conjunction(*signals: pd.Series) -> pd.Series:
    inputs = pd.concat(signals, axis=1)
    result = inputs.fillna(False).all(axis=1).astype("boolean")
    return result.mask(inputs.isna().any(axis=1), pd.NA)


def evaluate_rule(frame: pd.DataFrame, signal: pd.Series, name: str) -> list[dict[str, object]]:
    required = frame["forward_min_6m"].notna()
    results = []
    for sample, mask in {
        "训练期（至2016-12）": frame.index <= TRAIN_END,
        "验证期（2017起）": frame.index > TRAIN_END,
        "全样本": pd.Series(True, index=frame.index),
    }.items():
        metrics = confusion(signal[mask & required], frame.loc[mask & required, "correction_10"])
        results.append({"rule": name, "sample": sample, **metrics})
    return results


def auc_score(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Mann-Whitney AUC with average ranks for ties."""
    y_true = np.asarray(y_true, dtype=bool)
    scores = np.asarray(scores, dtype=float)
    positives = int(y_true.sum())
    negatives = int((~y_true).sum())
    if positives == 0 or negatives == 0:
        return np.nan
    ranks = pd.Series(scores).rank(method="average").to_numpy()
    rank_sum = ranks[y_true].sum()
    return float((rank_sum - positives * (positives + 1) / 2) / (positives * negatives))


def fit_logistic(train_x: np.ndarray, train_y: np.ndarray, l2: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Small deterministic L2 logistic model; returns weights, mean and scale."""
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale == 0] = 1.0
    x = (train_x - mean) / scale
    x = np.column_stack([np.ones(len(x)), x])
    weights = np.zeros(x.shape[1], dtype=float)
    for step in range(6000):
        logits = np.clip(x @ weights, -30, 30)
        probabilities = 1.0 / (1.0 + np.exp(-logits))
        penalty = np.r_[0.0, weights[1:]] * l2
        gradient = (x.T @ (probabilities - train_y) + penalty) / len(x)
        learning_rate = 0.15 / (1.0 + step / 2500)
        weights -= learning_rate * gradient
    return weights, mean, scale


def logistic_predict(values: np.ndarray, weights: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> np.ndarray:
    x = (values - mean) / scale
    x = np.column_stack([np.ones(len(x)), x])
    logits = np.clip(x @ weights, -30, 30)
    return 1.0 / (1.0 + np.exp(-logits))


def choose_f1_threshold(target: np.ndarray, probability: np.ndarray) -> float:
    best = (-1.0, 0.5)
    for threshold in np.unique(np.round(probability, 6)):
        signal = probability >= threshold
        tp = int((signal & target).sum())
        fp = int((signal & ~target).sum())
        fn = int((~signal & target).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        if f1 > best[0]:
            best = (f1, float(threshold))
    return best[1]


def evaluate_models(frame: pd.DataFrame) -> pd.DataFrame:
    feature_sets = {
        "仅名义10Y": ["y10", "y10_change_3m"],
        "利率与曲线": ["y10_change_3m", "real_yield", "real_yield_change_3m", "curve_10y3m"],
        "信用与金融条件": ["baa10y_bp", "baa10y_change_3m", "nfci", "nfci_change_3m"],
        "市场确认": ["equity_mom_3m", "equity_gap_6m", "vix", "stlfsi"],
        "信用+利率领先组合": ["baa10y_bp", "baa10y_change_3m", "nfci", "nfci_change_3m", "real_yield", "real_yield_change_3m", "curve_10y3m", "y10_change_3m"],
        "领先组合+市场确认": ["baa10y_bp", "baa10y_change_3m", "nfci", "nfci_change_3m", "real_yield", "real_yield_change_3m", "curve_10y3m", "y10_change_3m", "equity_mom_3m", "equity_gap_6m", "vix", "stlfsi"],
    }
    rows = []
    for model, features in feature_sets.items():
        sample = frame.dropna(subset=features + ["forward_min_6m"]).copy()
        train = sample.index <= TRAIN_END
        test = sample.index > TRAIN_END
        train_x = sample.loc[train, features].to_numpy(dtype=float)
        test_x = sample.loc[test, features].to_numpy(dtype=float)
        train_y = sample.loc[train, "correction_10"].to_numpy(dtype=bool)
        test_y = sample.loc[test, "correction_10"].to_numpy(dtype=bool)
        weights, mean, scale = fit_logistic(train_x, train_y)
        train_probability = logistic_predict(train_x, weights, mean, scale)
        test_probability = logistic_predict(test_x, weights, mean, scale)
        threshold = choose_f1_threshold(train_y, train_probability)
        for period, target, probability in (
            ("训练期（至2016-12）", train_y, train_probability),
            ("验证期（2017起）", test_y, test_probability),
        ):
            metrics = confusion(pd.Series(probability >= threshold), pd.Series(target))
            rows.append({
                "model": model,
                "sample": period,
                "start": str(sample.loc[train if period.startswith("训练") else test].index.min()),
                "end": str(sample.loc[train if period.startswith("训练") else test].index.max()),
                "auc": auc_score(target, probability),
                "train_selected_threshold": threshold,
                **metrics,
            })
    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame, definitions = load_frame()
    complete = frame[frame["forward_min_6m"].notna()].copy()

    leading = ("credit_level", "credit_widening", "real_level", "real_rising", "nfci_tight", "nfci_tightening", "curve_inverted", "rate_shock")
    confirmation = ("momentum_weak", "below_high", "vix_high", "stlfsi_high")

    rules: dict[str, pd.Series] = {
        "仅10Y快速上升": complete["rate_shock"],
        "领先压力：8项至少2项": at_least(complete, leading, 2),
        "领先压力：8项至少3项": at_least(complete, leading, 3),
        "市场确认：4项至少2项": at_least(complete, confirmation, 2),
        "市场确认：4项至少3项": at_least(complete, confirmation, 3),
        "信用恶化且市场至少2项确认": conjunction(at_least(complete, ("credit_level", "credit_widening", "nfci_tight", "nfci_tightening"), 1), at_least(complete, confirmation, 2)),
        "融资压力至少2项且市场至少1项确认": conjunction(at_least(complete, ("credit_level", "credit_widening", "real_level", "real_rising", "nfci_tight", "nfci_tightening"), 2), at_least(complete, confirmation, 1)),
    }

    percentile_leading = ("p_credit_level", "p_credit_widening", "p_real_level", "p_real_rising", "p_nfci_tight", "p_nfci_tightening", "p_curve_inverted", "p_rate_shock")
    percentile_confirmation = ("p_momentum_weak", "p_below_high", "p_vix_high", "p_stlfsi_high")
    rules.update({
        "滚动分位领先压力：8项至少3项": at_least(complete, percentile_leading, 3),
        "滚动分位市场确认：4项至少2项": at_least(complete, percentile_confirmation, 2),
        "滚动分位领先至少2项且市场至少1项": conjunction(at_least(complete, percentile_leading, 2), at_least(complete, percentile_confirmation, 1)),
        "滚动分位领先至少3项且市场至少2项": conjunction(at_least(complete, percentile_leading, 3), at_least(complete, percentile_confirmation, 2)),
    })
    signal_audit = complete[["forward_min_3m", "forward_min_6m", "correction_10", "correction_15"]].copy()
    for name, signal in rules.items():
        signal_audit[name] = signal
    signal_audit.to_csv(OUTPUT_DIR / "monthly_signal_audit.csv")

    # Select pairwise AND rules using training data only, then report them on the untouched test period.
    train = complete.index <= TRAIN_END
    pair_candidates = []
    for left, right in combinations(definitions, 2):
        signal = all_of(complete, (left, right))
        metrics = confusion(signal[train], complete.loc[train, "correction_10"])
        if metrics["signals"] >= 8 and metrics["recall"] >= 0.10:
            pair_candidates.append((metrics["precision"], metrics["lift"], left, right))
    for _precision, _lift, left, right in sorted(pair_candidates, reverse=True)[:5]:
        label = f"训练期优选AND：{definitions[left][0]} + {definitions[right][0]}"
        rules[label] = all_of(complete, (left, right))

    rows = []
    for name, signal in rules.items():
        rows.extend(evaluate_rule(complete, signal, name))
    results = pd.DataFrame(rows)
    results.to_csv(OUTPUT_DIR / "rule_performance.csv", index=False)

    model_results = evaluate_models(frame)
    model_results.to_csv(OUTPUT_DIR / "model_performance.csv", index=False)

    event_months = {
        "1998-08": "俄罗斯违约与LTCM",
        "2000-03": "科网泡沫见顶",
        "2001-09": "9·11",
        "2007-08": "次贷风险显性化",
        "2008-09": "雷曼破产",
        "2011-08": "美国评级下调",
        "2015-08": "中国市场冲击",
        "2018-10": "紧缩抛售",
        "2020-02": "新冠冲击",
        "2022-01": "快速加息周期",
        "2023-03": "硅谷银行事件",
    }
    event_rows = []
    for month, event in event_months.items():
        period = pd.Period(month, freq="M")
        for lead in (0, 1, 3):
            signal_period = period - lead
            if signal_period not in complete.index:
                continue
            row = complete.loc[signal_period]
            event_rows.append({
                "event": event,
                "event_month": month,
                "signal_month": str(signal_period),
                "lead_months": lead,
                "future_6m_min_return_pct": row["forward_min_6m"],
                "leading_count": int(row[list(leading)].fillna(False).sum()),
                "confirmation_count": int(row[list(confirmation)].fillna(False).sum()),
                "percentile_leading_count": int(row[list(percentile_leading)].fillna(False).sum()),
                "percentile_confirmation_count": int(row[list(percentile_confirmation)].fillna(False).sum()),
                "percentile_joint_trigger": bool(
                    row[list(percentile_leading)].fillna(False).sum() >= 3
                    and row[list(percentile_confirmation)].fillna(False).sum() >= 2
                ),
                **{key: None if pd.isna(row[key]) else bool(row[key]) for key in definitions},
            })
    pd.DataFrame(event_rows).to_csv(OUTPUT_DIR / "event_signal_audit.csv", index=False)

    coverage = []
    for column in ["sp500", "vix", "y10", "y3m", "stlfsi", "hy_oas", "baa10y", "real_yield", "nfci"]:
        available = frame[column].dropna()
        coverage.append({
            "series": column,
            "start": str(available.index.min()),
            "end": str(available.index.max()),
            "months": len(available),
        })
    pd.DataFrame(coverage).to_csv(OUTPUT_DIR / "source_coverage.csv", index=False)

    display = results[results["sample"] == "验证期（2017起）"].copy()
    display = display.sort_values(["precision", "recall"], ascending=False)
    print("COMPLETE_SAMPLE", complete.index.min(), complete.index.max(), len(complete))
    print("TEST_BASE_RATE", round(float(display["base_rate"].iloc[0]), 4))
    print(display[["rule", "signals", "tp", "fp", "precision", "recall", "false_positive_rate", "lift"]].to_string(index=False))
    print("\nCONTINUOUS_MODELS_TEST")
    print(model_results[model_results["sample"] == "验证期（2017起）"][["model", "n", "signals", "tp", "fp", "auc", "precision", "recall", "false_positive_rate", "lift"]].to_string(index=False))


if __name__ == "__main__":
    main()
