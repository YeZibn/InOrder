import pytest

from inorder_llm.reference_time import ReferenceTimeError, resolve_reference_time


def test_reference_time_defaults_to_shanghai_clock_format():
    value = resolve_reference_time(None)
    assert len(value) == 16
    assert value[4] == "-" and value[7] == "-" and value[10] == " " and value[13] == ":"


def test_reference_time_preserves_valid_caller_value():
    assert resolve_reference_time("2020-01-02 03:04") == "2020-01-02 03:04"
    assert resolve_reference_time(" 2020-01-02 03:04 ") == "2020-01-02 03:04"


@pytest.mark.parametrize("value", ["", "tomorrow", "2020/01/02 03:04", "2020-01-02"])
def test_reference_time_rejects_invalid_values(value):
    if value == "":
        assert len(resolve_reference_time(value)) == 16
    else:
        with pytest.raises(ReferenceTimeError):
            resolve_reference_time(value)
