"""Pure deterministic calculations. Values are input amounts, never savings estimates."""
from datetime import date
import re


class SchemaError(ValueError):
    """An input field violates the documented schema."""


def fail(field, message):
    raise SchemaError(f"{field}: {message}")


def exact_fields(value, required, field):
    if not isinstance(value, dict):
        fail(field, "must be an object")
    missing = set(required) - set(value)
    extra = set(value) - set(required)
    if missing or extra:
        fail(field, f"missing fields {sorted(missing)}; unknown fields {sorted(extra)}")


def integer(value, field, minimum=0, maximum=10**15):
    if type(value) is not int or not minimum <= value <= maximum:
        fail(field, f"must be an integer from {minimum} to {maximum}")
    return value


def string(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 10000:
        fail(field, "must be nonblank text of at most 10000 characters")
    if chr(0x2014) in value or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        fail(field, "control characters, unpaired surrogates and em dash characters are forbidden")
    return value


def day(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        fail(field, "must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        fail(field, "invalid calendar date")


def validate_config(config):
    exact_fields(config, ["synthetic", "as_of", "cooling_days", "cold_days", "currency"], "config")
    if type(config["synthetic"]) is not bool:
        fail("config.synthetic", "must be boolean")
    day(config["as_of"], "config.as_of")
    integer(config["cooling_days"], "config.cooling_days", 1, 36500)
    integer(config["cold_days"], "config.cold_days", 2, 36500)
    if config["cold_days"] <= config["cooling_days"]:
        fail("config.cold_days", "must exceed cooling_days")
    if not isinstance(config["currency"], str) or not re.fullmatch(r"[A-Z]{3}", config["currency"]):
        fail("config.currency", "must be a three-letter uppercase input currency code")


def classify(record, config):
    """Inclusive thresholds applied to elapsed calendar days since last contact."""
    days = (day(config["as_of"], "config.as_of") - day(record["last_contact"], "last_contact")).days
    status = "cold" if days >= config["cold_days"] else "cooling" if days >= config["cooling_days"] else "active"
    return {**record, "days_since_contact": days, "status": status,
            "days_until_cold": max(0, config["cold_days"] - days)}


def analyze(records, config):
    validate_config(config)
    seen = set()
    results = []
    fields = ["id", "name", "last_contact", "amount_minor", "synthetic", "entered_by"]
    for index, record in enumerate(records, 1):
        prefix = f"records[{index}]"
        exact_fields(record, fields, prefix)
        for field in ("id", "name", "entered_by"):
            string(record[field], f"{prefix}.{field}")
        if record["id"] in seen:
            fail(f"{prefix}.id", "duplicate id")
        seen.add(record["id"])
        integer(record["amount_minor"], f"{prefix}.amount_minor")
        if type(record["synthetic"]) is not bool:
            fail(f"{prefix}.synthetic", "must be boolean")
        if not record["synthetic"] and record["entered_by"] != "Henry":
            fail(f"{prefix}.entered_by", "real inputs must explicitly declare Henry")
        if day(record["last_contact"], f"{prefix}.last_contact") > day(config["as_of"], "config.as_of"):
            fail(f"{prefix}.last_contact", "future date relative to as_of")
        results.append(classify(record, config))
    results.sort(key=lambda r: r["id"])
    counts = {state: sum(r["status"] == state for r in results) for state in ("active", "cooling", "cold")}
    amounts = {state: sum(r["amount_minor"] for r in results if r["status"] == state) for state in counts}
    return {"config": config, "records": results, "summary": {
        "total": len(results), "counts": counts, "amounts_minor": amounts,
        "total_amount_minor": sum(amounts.values())}}
