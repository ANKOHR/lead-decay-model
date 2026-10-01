"""Synthetic illustrative cases. No randomness: fixed arithmetic sequence, no seed needed."""
from datetime import date, timedelta
import json

CONFIG = {"synthetic": True, "as_of": "2026-09-30", "cooling_days": 7, "cold_days": 14, "currency": "GBP"}


def fixture_records(count=200):
    return [{"id": f"lead-{i:03d}", "name": f"Synthetic opportunity {i}",
             "last_contact": (date(2026, 9, 30) - timedelta(days=i % 20)).isoformat(),
             "amount_minor": 10000, "synthetic": True, "entered_by": "fixture generator"}
            for i in range(count)]


def expectations():
    # Ten cycles of 0..19: 7 active, 7 cooling, 6 cold per cycle.
    return {"synthetic": True, "total": 200,
            "counts": {"active": 70, "cooling": 70, "cold": 60},
            "amounts_minor": {"active": 700000, "cooling": 700000, "cold": 600000},
            "total_amount_minor": 2000000,
            "cold_ids": [f"lead-{i:03d}" for i in range(200) if i % 20 in (14, 15, 16, 17, 18, 19)]}


def fixture_files():
    def labelled(value):
        return "# synthetic: true; illustrative fixture, not real outcomes\n" + json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return {"config.json": labelled(CONFIG), "leads.jsonl":
            "# synthetic: true; illustrative fixture, not real outcomes\n" + "".join(json.dumps(r, sort_keys=True) + "\n" for r in fixture_records()),
            "expectations.json": labelled(expectations())}
