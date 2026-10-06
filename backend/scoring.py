"""Persist the same validated scores served by the research API."""
from frontend.api.index import current_stocks, database_request


def calculate_scores():
    stocks = current_stocks()
    written = 0
    for stock in stocks:
        if stock["coverage"] == 0:
            continue  # Preserve saved research when verified inputs are absent.
        written += 1
        database_request("POST", "factor_scores", params={"on_conflict": "stock_id"}, body={
            "stock_id": stock["id"],
            "quality_score": stock["quality"], "value_score": stock["value"],
            "momentum_score": stock["momentum"], "liquidity_score": stock["liquidity"],
            "composite_score": stock["composite"],
            # Old explanations must not survive a change in the underlying scores.
            "ai_explanation_bn": None, "ai_explanation_en": None,
        }, prefer="resolution=merge-duplicates,return=minimal")
    print(f"Updated {written} verified scores; preserved other saved scores. Missing factors remain null; no ML prediction boost is used.")


if __name__ == "__main__":
    calculate_scores()
