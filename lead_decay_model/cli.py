"""Local-only CLI with named errors and atomic writes."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from .core import SchemaError, analyze
from .fixtures import CONFIG, fixture_files
from .report import render


class InputError(ValueError):
    """Named file and line error."""


def decode(text, path, line=1):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key}")
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f"nonfinite JSON constant {value}")
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except json.JSONDecodeError as error:
        raise InputError(f"ParseError: {path}: line {line + error.lineno - 1}: {error.msg}") from error
    except ValueError as error:
        raise InputError(f"ParseError: {path}: line {line}: {error}") from error


def read_json(path):
    text = path.read_text(encoding="utf-8-sig")
    # Replace comments with blank lines to preserve parser line numbers.
    return decode("\n".join("" if s.lstrip().startswith("#") else s for s in text.splitlines()), path)


def workflow(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise InputError(f"MissingInput: {directory}: use --input with a directory containing config.json and leads.jsonl")
    config_path = directory / "config.json"
    leads_path = directory / "leads.jsonl"
    unexpected = sorted(p.name for p in directory.iterdir() if p.is_file() and p.name not in {"config.json", "leads.jsonl", "expectations.json"})
    if unexpected:
        raise InputError(f"SchemaError: {directory}: line 1: unsupported input files {unexpected}; use config.json and leads.jsonl")
    if not any(directory.iterdir()):
        return analyze([], dict(CONFIG))
    if not config_path.is_file() or not leads_path.is_file():
        missing = config_path if not config_path.is_file() else leads_path
        raise InputError(f"MissingInput: {missing}: line 1: both config.json and leads.jsonl are required")
    config = read_json(config_path)
    records, locations = [], []
    for line, text in enumerate(leads_path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if text.strip() and not text.lstrip().startswith("#"):
            records.append(decode(text, leads_path, line))
            locations.append(line)
    try:
        return analyze(records, config)
    except SchemaError as error:
        match = re.search(r"records\[(\d+)\]", str(error))
        path = leads_path if match else config_path
        line = locations[int(match[1])-1] if match else 1
        raise InputError(f"SchemaError: {path}: line {line}: {error}") from error


def atomic_write(path, text):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    except OSError as error:
        raise InputError(f"WriteError: {path}: {error.strerror}") from error
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def parser():
    root = argparse.ArgumentParser(prog="ldm", description="Compute explicit opportunity inactivity rules. No predictions or savings estimates.")
    sub = root.add_subparsers(dest="command", required=True)
    fixtures = sub.add_parser("fixtures", help="Generate 200 labelled synthetic cases", epilog="Example: ldm fixtures --out demo")
    fixtures.add_argument("--out", required=True)
    run = sub.add_parser("run", help="Compute and save results", epilog="Example: ldm run --input demo")
    run.add_argument("--input", required=True)
    run.add_argument("--state", default=".ldm/results.json")
    report = sub.add_parser("report", help="Render saved or fresh calculations with provenance", epilog="Example: ldm report --format md")
    report.add_argument("--format", choices=["md", "json"], default="md")
    report.add_argument("--state", default=".ldm/results.json")
    report.add_argument("--input", help="Recompute directly from this input directory")
    report.add_argument("--out", help="Atomically write a report instead of stdout")
    cold = sub.add_parser("cold", help="List leads at or beyond the cold threshold", epilog="Example: ldm cold --input demo")
    cold.add_argument("--input", required=True)
    assess = sub.add_parser("assess", help="Show one lead's inactivity and days until cold", epilog="Example: ldm assess --input demo --id lead-014")
    assess.add_argument("--input", required=True)
    assess.add_argument("--id", required=True)
    return root


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            destination = Path(args.out)
            files = fixture_files()
            if any((destination / name).exists() for name in files):
                raise InputError(f"WriteError: {destination}: fixture files already exist; choose a fresh directory")
            for name, content in files.items():
                atomic_write(destination / name, content)
            print("Generated 200 synthetic illustrative records; no real outcomes measured.")
        elif args.command == "run":
            result = workflow(args.input)
            atomic_write(args.state, render(result, "json"))
            synthetic_count = sum(r['synthetic'] for r in result['records'])
            print(f"Computed {result['summary']['total']} records: {synthetic_count} synthetic illustrative, {result['summary']['total'] - synthetic_count} real declared entered by Henry. Results: {args.state}. Rule-based, no predicted outcomes or measured savings.")
        elif args.command == "report":
            if args.input:
                result = workflow(args.input)
            else:
                path = Path(args.state)
                if not path.is_file():
                    raise InputError(f"MissingInput: {path}: run ldm run --input <dir> first, or use report --input <dir>")
                stored = read_json(path)
                if not isinstance(stored, dict) or "config" not in stored or "records" not in stored:
                    raise InputError(f"SchemaError: {path}: line 1: missing config or records")
                # Recompute arithmetic instead of trusting stored totals.
                fields = ("id", "name", "last_contact", "amount_minor", "synthetic", "entered_by")
                try:
                    result = analyze([{key: r[key] for key in fields} for r in stored["records"]], stored["config"])
                except (KeyError, TypeError, SchemaError) as error:
                    raise InputError(f"SchemaError: {path}: line 1: {error}") from error
            output = render(result, args.format)
            if args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        else:
            result = workflow(args.input)
            if args.command == "cold":
                result["records"] = [r for r in result["records"] if r["status"] == "cold"]
            else:
                result["records"] = [r for r in result["records"] if r["id"] == args.id]
                if not result["records"]:
                    raise InputError(f"MissingLead: {args.id}: use an id present in leads.jsonl")
            # Subset reports reconcile their counts and values.
            raw = [{k: v for k, v in r.items() if k not in {"status", "days_since_contact", "days_until_cold"}} for r in result["records"]]
            print(render(analyze(raw, result["config"]), "json"), end="")
        return 0
    except (InputError, OSError, UnicodeError) as error:
        message = str(error).replace(chr(0x2014), "-")
        print(message if isinstance(error, InputError) else f"ReadError: {getattr(error, 'filename', None) or getattr(args, 'input', '')}: line 1: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
