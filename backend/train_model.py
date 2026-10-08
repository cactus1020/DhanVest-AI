"""Research-only model evaluation using purged chronological folds."""
import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score

from backend.data_validation import load_market_data, validate_source

FEATURES = ["close", "volume", "return_daily", "momentum_ratio", "vol_ma5"]


def features(frame, include_labels=True):
    groups = []
    for _, stock in frame.groupby("symbol"):
        stock = stock.sort_values("date").copy()
        stock["return_daily"] = stock["close"].pct_change(fill_method=None)
        stock["momentum_ratio"] = stock["close"].rolling(5).mean() / stock["close"].rolling(20).mean()
        stock["vol_ma5"] = stock["volume"].rolling(5).mean()
        future = stock["close"].shift(-5)
        stock["label_date"] = stock["date"].shift(-5)
        stock["target"] = (future > stock["close"]).astype(int)
        groups.append(stock)
    return pd.concat(groups).replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES + (["label_date"] if include_labels else []))


def chronological_folds(frame):
    days = np.array(sorted(frame["date"].unique()))
    if len(days) < 100:
        raise ValueError("At least 100 dated feature sessions are required for walk-forward evaluation.")
    for block in np.array_split(days[len(days) // 2:], 3):
        start, end = pd.Timestamp(block[0]), pd.Timestamp(block[-1])
        # Labels crossing into the test window are purged from training.
        train = frame[(frame["date"] < start) & (frame["label_date"] < start)]
        test = frame[(frame["date"] >= start) & (frame["date"] <= end)]
        if train.empty or test.empty or train["target"].nunique() < 2:
            raise ValueError("Insufficient samples or target classes in a chronological fold.")
        yield train, test


def train_model(path, source_url, confirm_verified=False, output=None):
    frame = load_market_data(path)
    validate_source(source_url)
    if not confirm_verified:
        raise ValueError("Training requires verified source data; pass --confirm-verified after checking it.")
    frame = features(frame)
    report = {"status": "research_only", "source": source_url, "rows": len(frame), "features": FEATURES, "horizon_sessions": 5, "folds": [], "limitations": ["Not a trading recommendation.", "No transaction-cost, survivorship-bias, or portfolio-performance evaluation.", "The model is not used by production scoring."]}
    for train, test in chronological_folds(frame):
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=1)
        model.fit(train[FEATURES], train["target"])
        prediction = model.predict(test[FEATURES])
        baseline = int(train["target"].mode().iloc[0])
        report["folds"].append({
            "train_end": train["date"].max().date().isoformat(),
            "latest_training_label": train["label_date"].max().date().isoformat(),
            "test_start": test["date"].min().date().isoformat(), "test_end": test["date"].max().date().isoformat(),
            "train_rows": len(train), "test_rows": len(test),
            "accuracy": accuracy_score(test["target"], prediction),
            "balanced_accuracy": balanced_accuracy_score(test["target"], prediction),
            "majority_baseline_accuracy": accuracy_score(test["target"], np.full(len(test), baseline)),
        })
    output = Path(output or Path(__file__).with_name("model-evaluation.json"))
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=1)
    model.fit(frame[FEATURES], frame["target"])
    with output.with_suffix(".pkl").open("wb") as handle:
        pickle.dump(model, handle)
    print(f"Saved three purged chronological evaluations to {output}. No investment performance claim is established.")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--confirm-verified", action="store_true")
    args = parser.parse_args()
    try:
        train_model(args.csv, args.source_url, args.confirm_verified)
    except ValueError as error:
        parser.exit(2, str(error) + "\n")
