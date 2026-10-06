"""Transparent research scores shared by local and deployed APIs."""
import math
from datetime import date
from statistics import mean, median

WEIGHTS = {"quality": 0.32, "value": 0.28, "momentum": 0.25, "liquidity": 0.15}


def number(value, minimum=None):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        return None
    return result


def clamp(value):
    return round(max(0.0, min(100.0, value)), 2)


def verified_history(rows, today=None):
    today = today or date.today()
    history = {}
    for row in rows:
        if row.get("source_verified") is not True or not row.get("source_url"):
            continue
        try:
            day = date.fromisoformat(str(row["date"]))
        except (KeyError, ValueError, TypeError):
            continue
        price = number(row.get("close_price"), minimum=0)
        volume = number(row.get("volume"), minimum=0)
        if day > today or price is None or price == 0 or volume is None:
            continue
        if day in history:
            raise ValueError("Duplicate trading dates must be resolved before scoring.")
        history[day] = dict(row, date=day.isoformat(), close_price=price, volume=volume)
    return [history[day] for day in sorted(history)]


def score_stock(stock, rows, sector_pe=None, today=None):
    today = today or date.today()
    history = verified_history(rows, today)
    result = {
        "id": stock["id"], "symbol": stock["symbol"],
        "name": stock.get("name") or stock["symbol"],
        "sector": stock.get("sector") or "Unknown",
        **{key: None for key in WEIGHTS}, "composite": None,
        "coverage": 0, "weights": {}, "as_of": None,
        "source_url": None, "stale": True, "explanation_bn": "",
        "warnings": [],
    }
    if not history:
        result["warnings"].append("No verified, dated market data is available.")
        return result
    latest = history[-1]
    result.update(as_of=latest["date"], source_url=latest["source_url"],latest_close=latest["close_price"],latest_volume=latest["volume"])
    result["stale"] = (today - date.fromisoformat(latest["date"])).days > 7
    if result["stale"]:
        result["warnings"].append("Historical snapshot: market data is more than 7 days old.")
    try:
        age = (today - date.fromisoformat(str(latest.get("fundamentals_date")))).days
        fresh_fundamentals = 0 <= age <= 180
    except (ValueError, TypeError):
        fresh_fundamentals = False
    roe = number(latest.get("roe")) if fresh_fundamentals else None
    debt = number(latest.get("debt_to_equity"), 0) if fresh_fundamentals else None
    pe = number(latest.get("pe_ratio"), 0) if fresh_fundamentals else None
    if roe is not None and debt is not None:
        result["quality"] = clamp(0.6 * clamp(roe / 30 * 100) + 0.4 * clamp((1 - debt / 2) * 100))
    if pe and sector_pe and stock.get("sector") not in (None, "", "General", "Unknown"):
        result["value"] = clamp(50 + (sector_pe / pe - 1) * 50)
    if len(history) >= 61:
        change = latest["close_price"] / history[-61]["close_price"] - 1
        result["momentum"] = clamp((change + 0.1) / 0.3 * 100)
    if len(history) >= 20:
        result["liquidity"] = clamp(mean(row["volume"] for row in history[-20:]) / 200000 * 100)
    available = {key: weight for key, weight in WEIGHTS.items() if result[key] is not None}
    total = sum(available.values())
    result["coverage"] = round(total * 100)
    result["weights"] = {key: round(weight / total, 6) for key, weight in available.items()} if total else {}
    if total:
        result["composite"] = round(sum(result[key] * weight for key, weight in available.items()) / total, 2)
    missing = [key for key in WEIGHTS if result[key] is None]
    if missing:
        result["warnings"].append("Unavailable factors: " + ", ".join(missing) + ". Available weights are renormalized.")
    return result


def score_universe(stocks, rows, today=None):
    today = today or date.today()
    grouped = {}
    for row in rows:
        grouped.setdefault(row["stock_id"], []).append(row)
    histories = {stock["id"]: verified_history(grouped.get(stock["id"], []), today) for stock in stocks}
    sectors = {}
    for stock in stocks:
        history = histories[stock["id"]]
        if not history or stock.get("sector") in (None, "", "General", "Unknown"):
            continue
        latest = history[-1]
        try:
            market_age = (today - date.fromisoformat(latest["date"])).days
            age = (today - date.fromisoformat(str(latest.get("fundamentals_date")))).days
        except (ValueError, TypeError):
            continue
        pe = number(latest.get("pe_ratio"), 0)
        if pe and 0 <= age <= 180 and market_age <= 7:
            sectors.setdefault(stock["sector"], []).append(pe)
    result = []
    for stock in stocks:
        peers = sectors.get(stock.get("sector"), [])
        baseline = median(peers) if len(peers) >= 3 else None
        result.append(score_stock(stock, grouped.get(stock["id"], []), baseline, today))
    return sorted(result, key=lambda row: (row["stale"], -(row["composite"] if row["composite"] is not None else -1)))


def explain_bangla(stock):
    labels = {"quality": "ব্যবসার মান", "value": "মূল্যায়ন", "momentum": "অতীতের দামের পরিবর্তন", "liquidity": "লেনদেনের পরিমাণ"}
    available = {key: stock[key] for key in WEIGHTS if stock[key] is not None}
    if not available:
        return "এই প্রতিষ্ঠানের যাচাইকৃত তথ্য পর্যাপ্ত নয়, তাই নির্ভরযোগ্য স্কোর বা ব্যাখ্যা দেওয়া যাচ্ছে না। এটি বিনিয়োগের পরামর্শ নয়।"
    highest, lowest = max(available, key=available.get), min(available, key=available.get)
    text = f"{stock['name']}-এর {stock['as_of']} তারিখের তথ্য অনুযায়ী, উপলব্ধ সূচকগুলোর মধ্যে {labels[highest]} তুলনামূলক বেশি ({available[highest]:.1f}/১০০)। "
    text += f"তুলনামূলক কম স্কোর হলো {labels[lowest]} ({available[lowest]:.1f}/১০০); সিদ্ধান্ত নেওয়ার আগে এই দিকটি খতিয়ে দেখুন। "
    if stock["coverage"] < 100:
        text += "কিছু তথ্য অনুপস্থিত, তাই এটি আংশিক মূল্যায়ন। "
    if stock["stale"]:
        text += "তথ্য পুরোনো; বর্তমান বাজার পরিস্থিতি আলাদা হতে পারে। "
    return text + "এই স্কোর ভবিষ্যতের দাম বা লাভের নিশ্চয়তা দেয় না। তথ্য ও শিক্ষার জন্য, বিনিয়োগের পরামর্শ নয়।"


def stored_history(rows):
    """Preserve import order for undated legacy data; never invent trading dates."""
    ordered = sorted(rows, key=lambda row: row.get('id', 0))
    return [dict(row, close_price=number(row.get('close_price'), 0)) for row in ordered
            if number(row.get('close_price'), 0) not in (None, 0)]


def add_stored_research(results, rows, saved_scores):
    scores = {row['stock_id']: row for row in saved_scores}
    for result in results:
        records = stored_history([row for row in rows if row['stock_id'] == result['id']])
        result['stored_data'] = None
        result['saved_scores'] = None
        if records:
            latest = records[-1]
            previous = records[-2]['close_price'] if len(records) > 1 else None
            change = (latest['close_price'] / previous - 1) * 100 if previous else None
            result['stored_data'] = {'count':len(records), 'close':latest['close_price'],
                'previous_close':previous, 'change_percent':round(change, 2) if change is not None else None,
                'volume':number(latest.get('volume'), 0), 'pe_ratio':number(latest.get('pe_ratio')),
                'roe':number(latest.get('roe')), 'debt_to_equity':number(latest.get('debt_to_equity')),
                'dates_verified': all(row.get('source_verified') is True and row.get('source_url') for row in records),
                'stored_date':latest.get('date')}
        saved = scores.get(result['id'])
        if saved:
            values = {key: number(saved.get(key + '_score'), 0) for key in (*WEIGHTS, 'composite')}
            values = {key: value if value is not None and value <= 100 else None for key,value in values.items()}
            result['saved_scores'] = dict(values, explanation_bn=saved.get('ai_explanation_bn') or '')
    return results


def explain_stored_bangla(stock):
    data = stock.get('stored_data')
    if not data:
        return explain_bangla(stock)
    change = data['change_percent']
    text = f"{stock['name']}-এর সংরক্ষিত {data['count']}টি রেকর্ড আছে। শেষ সংরক্ষিত দাম {data['close']:.2f} টাকা। "
    if change is not None:
        direction = 'বেড়েছে' if change > 0 else 'কমেছে' if change < 0 else 'অপরিবর্তিত আছে'
        text += f"আগের সংরক্ষিত রেকর্ডের তুলনায় দাম {abs(change):.2f}% {direction}। "
    if data['volume'] is not None:
        text += f"শেষ রেকর্ডে লেনদেনের পরিমাণ {data['volume']:,.0f}। "
    text += "এই পুরোনো ইমপোর্টের তারিখ ও উৎস যাচাই বাকি; এটি আজকের দাম বা আগামী দিনের প্রেডিকশন নয়। "
    saved = stock.get('saved_scores')
    if saved and saved.get('composite') is not None:
        text += f"আগের সিস্টেমে সংরক্ষিত কম্পোজিট স্কোর {saved['composite']:.1f}/১০০। এর পদ্ধতি এখনও যাচাই করা হয়নি। "
    if all(data[key] is None for key in ('pe_ratio','roe','debt_to_equity')):
        text += "P/E, ROE ও ঋণের তথ্য নেই, তাই বর্তমান ব্যবসার স্বাস্থ্য নির্ধারণ করা যাচ্ছে না।"
    return text
