from veildata.utils.traversal import traverse_and_redact


def mock_redactor(text: str) -> str:
    return text[::-1]  # Reverse string for easy verification


def test_traverse_simple_string():
    assert traverse_and_redact("hello", mock_redactor) == "olleh"


def test_traverse_list():
    data = ["abc", "def", 123]
    expected = ["cba", "fed", 123]
    assert traverse_and_redact(data, mock_redactor) == expected


def test_traverse_dict():
    data = {"key1": "value1", "key2": 456}
    expected = {"key1": "1eulav", "key2": 456}
    assert traverse_and_redact(data, mock_redactor) == expected


def test_traverse_nested():
    data = {
        "user": {"name": "Alice", "age": 30, "roles": ["admin", "editor"]},
        "metadata": [{"id": 1, "note": "secret"}, {"id": 2, "note": "public"}],
    }
    expected = {
        "user": {"name": "ecilA", "age": 30, "roles": ["nimda", "rotide"]},
        "metadata": [{"id": 1, "note": "terces"}, {"id": 2, "note": "cilbup"}],
    }
    assert traverse_and_redact(data, mock_redactor) == expected


def test_traverse_mixed_types():
    data = [True, None, 3.14, "text"]
    expected = [True, None, 3.14, "txet"]
    assert traverse_and_redact(data, mock_redactor) == expected


def test_traverse_empty():
    assert traverse_and_redact({}, mock_redactor) == {}
    assert traverse_and_redact([], mock_redactor) == []
    assert traverse_and_redact("", mock_redactor) == ""
