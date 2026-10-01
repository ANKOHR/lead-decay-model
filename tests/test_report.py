import json
from lead_decay_model.core import analyze
from lead_decay_model.fixtures import CONFIG, fixture_records, expectations
from lead_decay_model.report import render


def test_report_matches_ground_truth_exact():
    result = json.loads(render(analyze(fixture_records(), CONFIG), 'json'))
    expected = expectations()
    assert result['summary'] == {key: expected[key] for key in result['summary']}


def test_report_zero_false_positives():
    result = json.loads(render(analyze(fixture_records(), CONFIG), 'json'))
    actual = [r['id'] for r in result['records'] if r['status'] == 'cold']
    assert actual == expectations()['cold_ids']


def test_report_carries_provenance_banner():
    records = fixture_records(2)
    records[0].update(synthetic=False, entered_by='Henry')
    for format in ('md', 'json'):
        text = render(analyze(records, CONFIG), format)
        assert 'DATA PROVENANCE' in text and 'Henry' in text and 'synthetic' in text
    p = json.loads(render(analyze(records, CONFIG), 'json'))['provenance']
    assert p['real_input_ids'] == ['lead-000']
    assert p['synthetic_input_ids'] == ['lead-001']


def test_hypothetical_figures_labelled():
    text = render(analyze(fixture_records(), CONFIG))
    assert 'illustrative' in text
    assert 'No conversion prediction, measured savings, or measured real-world accuracy' in text
    assert 'not expected revenue' in text


def test_no_em_dashes_in_outputs():
    for format in ('md', 'json'):
        assert chr(0x2014) not in render(analyze(fixture_records(), CONFIG), format)


def test_markdown_figures_match_ground_truth():
    text = render(analyze(fixture_records(), CONFIG))
    assert '| active | 70 | 700000 |' in text
    assert '| cooling | 70 | 700000 |' in text
    assert '| cold | 60 | 600000 |' in text
    assert 'Records: 200. Total input amount: 2000000 GBP minor units.' in text
