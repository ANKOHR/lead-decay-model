import json
from lead_decay_model.core import analyze
from lead_decay_model.fixtures import CONFIG, fixture_records, expectations, fixture_files


def test_fixtures_labelled_synthetic():
    for name, text in fixture_files().items():
        assert text.startswith('# synthetic: true')
        data = text.splitlines()[1:]
        if name.endswith('.jsonl'):
            assert all(json.loads(line)['synthetic'] is True for line in data)
        else:
            assert json.loads('\n'.join(data))['synthetic'] is True


def test_fixture_ground_truth_matches_hand_computed():
    expected = expectations()
    assert expected['counts'] == {'active': 70, 'cooling': 70, 'cold': 60}
    result = analyze(fixture_records(), CONFIG)
    assert result['summary'] == {k: expected[k] for k in result['summary']}
    assert len(result['records']) == 200


def test_corrupted_fixture_changes_computed_figures():
    records = fixture_records()
    records[14]['last_contact'] = '2026-09-30'
    records[14]['amount_minor'] = 17
    result = analyze(records, CONFIG)
    assert result['summary']['counts'] == {'active': 71, 'cooling': 70, 'cold': 59}
    assert result['summary']['total_amount_minor'] == 1990017
    # Expectations cannot affect computation, even if its ground truth is corrupted.
    wrong = expectations()
    wrong['counts']['cold'] = 0
    assert result['summary']['counts'] != wrong['counts']
