import copy
import pytest
from lead_decay_model.core import analyze, SchemaError
from lead_decay_model.fixtures import CONFIG, fixture_records


def test_boundaries():
    result = analyze(fixture_records(20), CONFIG)
    by_id = {r['id']: r for r in result['records']}
    assert by_id['lead-006']['status'] == 'active'
    assert by_id['lead-007']['status'] == 'cooling'
    assert by_id['lead-013']['days_until_cold'] == 1
    assert by_id['lead-014']['status'] == 'cold'


@pytest.mark.parametrize('field,value', [('amount_minor', -1), ('amount_minor', True), ('amount_minor', 1.5), ('amount_minor', 10**16), ('last_contact', '2026-10-01'), ('last_contact', '2026-02-30'), ('name', 'x'*10001), ('synthetic', 'yes'), ('entered_by', ''), ('id', 'x'+chr(0x2014))])
def test_rejects_adversarial_values(field, value):
    records = fixture_records(1)
    records[0][field] = value
    with pytest.raises(SchemaError):
        analyze(records, CONFIG)


def test_duplicate_and_schema_drift():
    record = fixture_records(1)[0]
    with pytest.raises(SchemaError, match='duplicate id'):
        analyze([record, record], CONFIG)
    with pytest.raises(SchemaError, match='unknown fields'):
        analyze([{**record, 'mystery': 3}], CONFIG)


def test_handles_unicode_and_long_inputs():
    record = fixture_records(1)[0]
    record['name'] = '雪 café C:\\Users\\Henry ' + 'x'*9000
    assert analyze([record], CONFIG)['records'][0]['name'] == record['name']


def test_real_data_provenance_validation():
    record = {**fixture_records(1)[0], 'synthetic': False, 'entered_by': 'Henry'}
    assert analyze([record], CONFIG)['summary']['total'] == 1
    record['entered_by'] = 'unknown'
    with pytest.raises(SchemaError, match='Henry'):
        analyze([record], CONFIG)


@pytest.mark.parametrize('change', [{'cold_days': 7}, {'cooling_days': 0}, {'currency': 'gbp'}, {'as_of': 'today'}, {'synthetic': 1}])
def test_invalid_config(change):
    with pytest.raises(SchemaError):
        analyze([], {**CONFIG, **change})
