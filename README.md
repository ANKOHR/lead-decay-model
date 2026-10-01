# Lead Decay Model

`ldm` computes when opportunities cross explicit inactivity thresholds. It uses supplied dates and integer amounts, with no network calls, models, GPU, database, or random numbers. It does not predict deal loss or conversion.

Hypothesis: a deterministic, tested local CLI can make inactivity rules reliable and auditable for Henry's outreach operation. Synthetic evidence validates the arithmetic and handling of inputs. Real operational usefulness remains unmeasured.

## Quickstart

Python 3.10 or newer, plus setuptools for installation. From the repository, install without accessing the network:

```powershell
python -m pip install --no-index --no-deps --no-build-isolation -e .
ldm fixtures --out demo
ldm run --input demo
ldm report --format md
python -m pytest -q
```

If a Windows user installation reports that `ldm` is not on PATH, add its Scripts directory for the current PowerShell session, then run the demo:

```powershell
$ldmScripts = python -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))"
$env:PATH = "$ldmScripts;$env:PATH"
```

The three demo commands also work joined with `&&` in PowerShell 7. Use a fresh fixture directory: the generator refuses to overwrite existing fixture files. Reports and state writes use UTF-8, LF newlines and atomic replacement. Output state defaults to `.ldm/results.json`, relative to the working directory. Tests require an already installed pytest; runtime has no third-party dependencies. Without installing, use `python -m lead_decay_model.cli` in place of `ldm`.

A tiny, hand-written five-record synthetic example is included:

```powershell
ldm run --input examples/tiny
ldm report --format md
```

Do not commit Henry's real records, generated state or real trial reports. Trial results belong in a separate private local directory.

## Input format reference

An input directory contains `config.json` and `leads.jsonl`. JSON supports full-line `#` header comments through this CLI's explicit preprocessing; these commented files are not strict standalone JSON for other tools. The parser retains original line numbers. `leads.jsonl` holds one JSON object per nonblank, noncomment line. UTF-8 with an optional BOM is accepted. Empty directories produce a zero report with explicitly synthetic default configuration: snapshot 2026-09-30, cooling 7 days, cold 14 days, GBP. Nonempty directories require both files. Unsupported files, including CSV and YAML, produce a named schema error; convert them to the documented format. `expectations.json` is optional fixture evidence only, never calculation input.

Configuration example for Henry's own manually entered data:

```json
{
  "synthetic": false,
  "as_of": "2026-09-30",
  "cooling_days": 7,
  "cold_days": 14,
  "currency": "GBP"
}
```

Illustrative input record, not a measured real opportunity:

```json
{"id":"example-1","name":"Illustrative prospect","last_contact":"2026-09-16","amount_minor":10000,"synthetic":true,"entered_by":"illustrative example"}
```

For Henry's own real records, he must explicitly set `synthetic` to `false` and `entered_by` to `Henry`. These declarations are not independently verified. Mixed real and synthetic records are allowed; reports identify each by ID, plus the provenance of the configuration.

All displayed fields are required and unknown fields are rejected. IDs are unique across the directory. `id`, `name`, and `entered_by` must be nonblank Unicode text up to 10000 characters, without control characters, unpaired surrogates, or em dash characters. Windows paths may appear in text using normal JSON backslash escaping. No strings are silently truncated. Dates must be exact valid YYYY-MM-DD calendar dates. Contact dates after `as_of` are rejected. Dates carry no time of day or timezone. `amount_minor` must be an integer from 0 to 10^15, excluding booleans, decimals, negatives, NaN and infinity. All records use one configured three-letter uppercase currency code; the CLI does not convert currencies or verify ISO membership. Amounts are in that currency's minor units. Both provenance flags must be JSON booleans. Thresholds must be integers: cooling 1..36500, cold 2..36500, and cold must exceed cooling. Duplicate JSON keys are rejected.

### Calculation rules

Elapsed days = `as_of - last_contact`. Active means elapsed days below `cooling_days`. Cooling means elapsed days at least `cooling_days` and below `cold_days`. Cold means elapsed days at least `cold_days`. Equality is included. `days_until_cold` = maximum of zero and `cold_days - elapsed days`, a conditional rule interval assuming no new contact. It is not a forecast of human behavior. There are no inferred contacts, scores, probabilities, fitted half-lives, or business-day adjustments. Supply an updated contact date and snapshot to recompute.

Counts reconcile across the three statuses. Input amounts reconcile using integer arithmetic. No floats or probabilistic revenue estimates are used. Records sort by ID; JSON keys sort deterministically. No current clock is used in calculation or reporting. Identical inputs and configuration produce byte-identical reports and saved results. Fixture construction is a fixed arithmetic sequence, with no randomness and therefore no seed.

## Subcommand catalogue

Every subcommand offers `--help` and an example.

| Command | Purpose | Example |
| --- | --- | --- |
| `fixtures` | Write 200 synthetic labelled cases and independent expectations | `ldm fixtures --out demo` |
| `run` | Compute and atomically save full results | `ldm run --input demo --state .ldm/results.json` |
| `report` | Render saved results or recompute from input | `ldm report --format json --input demo --out report.json` |
| `cold` | Report only records at or beyond the cold threshold | `ldm cold --input demo` |
| `assess` | Report one record and its conditional days until cold | `ldm assess --input demo --id lead-014` |

`report --format md` is the default. `report --state <path>` reads saved records and configuration, recomputes all figures, and adds provenance rather than trusting saved summary values. `cold` and `assess` output JSON reports whose totals reconcile only for the selected subset. A missing ID is a named error. No command sends messages or makes external requests.

## Architecture

```text
labelled fixtures.py or Henry's manually entered files
                         |
                   cli.py parsing and validation
                         |
                   core.py pure arithmetic
                         |
                   report.py provenance and rendering
                         |
                   stdout or atomic local output
```

## Honesty boundary

Synthetic figures are illustrative rule examples, not real business outcomes or measured accuracy on real prospects. All fixture files start with a synthetic header and contain `synthetic: true` on each JSON object where applicable. Every report has a DATA PROVENANCE banner, real and synthetic record identities, a configuration label, and an explicit limitation statement. Source identity and truth are declarations, not verified discoveries.

The CLI has no time-saved, money-saved, conversion-probability, or real-world-accuracy fields or options. It therefore cannot report unmeasured savings as measured. Supplied opportunity amounts are input values, not expected revenue. `days_until_cold` is conditional threshold arithmetic, not a predicted loss date. The threshold choices themselves are user assumptions; the default synthetic thresholds have no claimed empirical calibration.

## Acceptance evidence and failure modes

The 200-record fixture has ten cycles of inactivity days 0..19. Each cycle has seven active, seven cooling, and six cold records. Each record has an illustrative input value of 10000 minor units. Independent hand arithmetic gives counts 70/70/60, amounts 700000/700000/600000, and total 2000000. Cold IDs have a cycle position 14..19. The expectations file and tests pin this ground truth. Runtime never reads expectations. Changing contact dates or values changes the report even if expectations are unchanged or corrupted.

`EVIDENCE.md` records measured local tests and demo timing. Those measurements concern software execution, not outreach outcomes. Named errors have exit code 2 and no traceback: ParseError gives file and original line; SchemaError gives file, line and offending field; MissingInput includes a usage hint; MissingLead identifies an absent ID; ReadError handles filesystem or encoding failures; WriteError identifies an output failure. Configuration schema errors identify the file and line 1 (the document level), while record errors identify the exact JSONL line. Invalid data is rejected as a whole, never silently dropped. Report writes use a temporary sibling file and atomic replacement; on failure the temporary file is removed and any previous destination remains intact. The generator writes files individually, so a multi-file fixture write failure can leave already completed fixture files; use a fresh directory to retry.

Tests include empty directories, malformed JSON, schema drift, duplicate keys and IDs, negative and noninteger values, future dates, Unicode, long strings, Windows paths, provenance, deterministic bytes, corrupted fixture data, ignored corrupted expectations, CLI help, and report write failure. Tests against planted labels prove rule correctness, not that the labels reflect actual sales behavior.

## Evidence-based improvement hook and verdict

The primary real-use metric is the fraction of sampled classifications that Henry disagrees with after hand-checking the supplied contact history and status. Start a two-week private trial only when real use begins. Record its start and end dates, number of runs, sample selection, sample size, rule version, disagreements and causes. Error rate is disagreements / reviewed records; a zero sample is unmeasured, not zero error. Record baseline timing separately if claiming time saved, using the same task and sample. Do not ship real trial results.

After two weeks: if error exceeds 10 percent, fix the single largest evidenced failure cause and retest, or kill with a written reason. If the tool is never used, kill. Expand if it earns daily use or revenue; integrate if overlap with a sibling project is demonstrated; commercialise if a buyer would pay for it as-is; otherwise maintain as portfolio evidence, provided acceptance criteria are met. Record the actual decision and measured reason privately, with an appropriately anonymised repo update only if permitted.

`VERDICT.md` explicitly defers the operational verdict until that evidence window. A finished synthetic build does not invent two weeks of usage or justify commercialisation.
