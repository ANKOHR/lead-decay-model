"""Render measured input arithmetic with explicit provenance and limitations."""
import json

HONESTY = "Rule-based inactivity classification only. No conversion prediction, measured savings, or measured real-world accuracy. Amounts are supplied opportunity values, not expected revenue."


def provenance(result):
    real = [r["id"] for r in result["records"] if not r["synthetic"]]
    synthetic = [r["id"] for r in result["records"] if r["synthetic"]]
    return {"banner": "DATA PROVENANCE: real inputs declared entered by Henry; synthetic fixtures are illustrative, not real outcomes.",
            "real_input_ids": real, "synthetic_input_ids": synthetic,
            "configuration": "synthetic" if result["config"]["synthetic"] else "user supplied",
            "verification": "Input declarations only; identity and truth are not independently verified."}


def render(result, format="md"):
    payload = {**result, "provenance": provenance(result), "honesty": HONESTY}
    if format == "json":
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if format != "md":
        raise ValueError("format must be md or json")
    p, s, c = payload["provenance"], result["summary"], result["config"]
    lines = ["# Lead Decay Model", "", p["banner"],
             f"Real records: {len(p['real_input_ids'])}; synthetic records: {len(p['synthetic_input_ids'])}; configuration: {p['configuration']}.",
             p["verification"], "", HONESTY, "",
             f"Snapshot: {c['as_of']}. Cooling at {c['cooling_days']} days; cold at {c['cold_days']} days (inclusive).",
             f"Records: {s['total']}. Total input amount: {s['total_amount_minor']} {c['currency']} minor units.", "",
             "| Status | Count | Input amount (minor units) |", "| --- | ---: | ---: |"]
    for state in ("active", "cooling", "cold"):
        lines.append(f"| {state} | {s['counts'][state]} | {s['amounts_minor'][state]} |")
    lines += ["", "## Traceable record calculations", ""]
    for r in result["records"]:
        # JSON quoting prevents user text from injecting Markdown structure.
        identity = json.dumps({"id": r["id"], "name": r["name"]}, ensure_ascii=False)
        lines.append(f"    {identity}: last_contact={r['last_contact']}; days={r['days_since_contact']}; status={r['status']}; days_until_cold={r['days_until_cold']}; amount_minor={r['amount_minor']}; synthetic={str(r['synthetic']).lower()}; entered_by={json.dumps(r['entered_by'], ensure_ascii=False)}")
    return "\n".join(lines) + "\n"
