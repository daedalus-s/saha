from app.llm_json import parse_json_payload
import pytest


def test_parse_plain_object():
    assert parse_json_payload('{"found": true}') == {"found": True}


def test_parse_fenced_object():
    raw = 'Sure.\n```json\n{"verses": ["a"]}\n```\n'
    assert parse_json_payload(raw)["verses"] == ["a"]


def test_parse_rejects_array():
    with pytest.raises(ValueError):
        parse_json_payload("[1, 2]")
