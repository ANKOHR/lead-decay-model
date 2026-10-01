import json
import subprocess
import sys
import time
from pathlib import Path
import pytest
from lead_decay_model.cli import main, workflow
from lead_decay_model.fixtures import fixture_files


@pytest.fixture
def inputs(tmp_path):
    directory = tmp_path / 'inputs'
    directory.mkdir()
    for name, text in fixture_files().items():
        (directory / name).write_text(text, encoding='utf-8')
    return directory


def test_run_completes_on_fixture(inputs, tmp_path, capsys):
    state = tmp_path / 'state.json'
    start = time.perf_counter()
    assert main(['run', '--input', str(inputs), '--state', str(state)]) == 0
    assert main(['report', '--state', str(state), '--format', 'md']) == 0
    assert time.perf_counter() - start < 5
    assert 'DATA PROVENANCE' in capsys.readouterr().out


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    assert main(['report', '--input', str(tmp_path), '--format', 'json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['summary']['total'] == 0
    assert result['summary']['total_amount_minor'] == 0


def test_malformed_input_named_error(inputs, capsys):
    (inputs / 'leads.jsonl').write_text('# synthetic: true\n{broken\n', encoding='utf-8')
    assert main(['run', '--input', str(inputs)]) == 2
    error = capsys.readouterr().err
    assert 'ParseError' in error and 'leads.jsonl: line 2' in error
    assert 'Traceback' not in error


def test_determinism_byte_identical(inputs, tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    for path in (a, b):
        assert main(['run', '--input', str(inputs), '--state', str(path)]) == 0
    assert a.read_bytes() == b.read_bytes()
    assert main(['report', '--state', str(a), '--out', str(tmp_path / 'one.md')]) == 0
    assert main(['report', '--state', str(b), '--out', str(tmp_path / 'two.md')]) == 0
    assert (tmp_path / 'one.md').read_bytes() == (tmp_path / 'two.md').read_bytes()


def test_cli_smoke_all_subcommands(inputs, tmp_path, capsys):
    assert main(['fixtures', '--out', str(tmp_path / 'fresh')]) == 0
    assert main(['run', '--input', str(inputs), '--state', str(tmp_path / 'state')]) == 0
    assert main(['report', '--input', str(inputs), '--format', 'json']) == 0
    assert main(['cold', '--input', str(inputs)]) == 0
    assert main(['assess', '--input', str(inputs), '--id', 'lead-014']) == 0
    for command in ('fixtures', 'run', 'report', 'cold', 'assess'):
        with pytest.raises(SystemExit) as error:
            main([command, '--help'])
        assert error.value.code == 0
    assert chr(0x2014) not in capsys.readouterr().out


def test_missing_and_write_errors(tmp_path, inputs, capsys):
    assert main(['run', '--input', str(tmp_path / 'missing')]) == 2
    assert 'MissingInput' in capsys.readouterr().err
    assert main(['report', '--input', str(inputs), '--out', str(inputs)]) == 2
    assert 'WriteError' in capsys.readouterr().err
    assert sorted(p.name for p in inputs.iterdir()) == sorted(fixture_files())


@pytest.mark.parametrize('text', ['{"id":1,"id":2}', '{"amount_minor":NaN}', '[]', '{"amount_minor":-1}'])
def test_adversarial_files(inputs, text, capsys):
    (inputs / 'leads.jsonl').write_text(text, encoding='utf-8')
    assert main(['report', '--input', str(inputs)]) == 2
    assert 'line 1' in capsys.readouterr().err


def test_expectations_are_never_used(inputs):
    before = workflow(inputs)
    (inputs / 'expectations.json').write_text('corrupted deliberately', encoding='utf-8')
    assert workflow(inputs) == before


def test_realistic_five_record_workflow(inputs):
    path = inputs / 'leads.jsonl'
    path.write_text('\n'.join(path.read_text(encoding='utf-8').splitlines()[:6])+'\n', encoding='utf-8')
    assert workflow(inputs)['summary']['total'] == 5


def test_subprocess_entrypoint(inputs):
    result = subprocess.run([sys.executable, '-m', 'lead_decay_model.cli', 'cold', '--input', str(inputs)], capture_output=True, encoding='utf-8')
    assert result.returncode == 0
    assert json.loads(result.stdout)['summary']['total'] == 60


def test_handwritten_tiny_example():
    result = workflow(Path(__file__).resolve().parents[1] / 'examples' / 'tiny')
    assert result['summary'] == {'total': 5, 'counts': {'active': 2, 'cooling': 1, 'cold': 2}, 'amounts_minor': {'active': 300, 'cooling': 300, 'cold': 900}, 'total_amount_minor': 1500}


def test_config_parse_line_preserved(inputs, capsys):
    (inputs / 'config.json').write_text('# synthetic: true\n{\n broken\n}', encoding='utf-8')
    assert main(['run', '--input', str(inputs)]) == 2
    assert 'config.json: line 3' in capsys.readouterr().err


def test_schema_error_exact_record_line(inputs, capsys):
    lines = (inputs / 'leads.jsonl').read_text(encoding='utf-8').splitlines()
    bad = json.loads(lines[15])
    bad['amount_minor'] = -1
    lines[15] = json.dumps(bad)
    (inputs / 'leads.jsonl').write_text('\n'.join(lines), encoding='utf-8')
    assert main(['report', '--input', str(inputs)]) == 2
    assert 'leads.jsonl: line 16: records[15].amount_minor' in capsys.readouterr().err


def test_saved_totals_recomputed(inputs, tmp_path, capsys):
    state = tmp_path / 'state.json'
    assert main(['run', '--input', str(inputs), '--state', str(state)]) == 0
    capsys.readouterr()
    data = json.loads(state.read_text(encoding='utf-8'))
    data['summary']['total'] = 999
    state.write_text(json.dumps(data), encoding='utf-8')
    assert main(['report', '--state', str(state), '--format', 'json']) == 0
    assert json.loads(capsys.readouterr().out)['summary']['total'] == 200


def test_incomplete_nonempty_directory(tmp_path, capsys):
    (tmp_path / 'expectations.json').write_text('{}', encoding='utf-8')
    assert main(['report', '--input', str(tmp_path)]) == 2
    assert 'MissingInput' in capsys.readouterr().err


def test_unsupported_csv_named_error(tmp_path, capsys):
    (tmp_path / 'bad.csv').write_text('broken,csv', encoding='utf-8')
    assert main(['report', '--input', str(tmp_path)]) == 2
    assert 'bad.csv' in capsys.readouterr().err
