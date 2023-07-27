from eth_validator_watcher.utils import LimitedDict
from pytest import raises


def test_negative() -> None:
    with raises(AssertionError):
        LimitedDict(-1)


def test_nominal_increasing() -> None:
    limited_dict = LimitedDict(2)
    assert len(limited_dict) == 0

    limited_dict[1] = "a"
    assert len(limited_dict) == 1
    assert 1 in limited_dict
    assert limited_dict[1] == "a"

    limited_dict[2] = "b"
    assert len(limited_dict) == 2
    assert 2 in limited_dict
    assert limited_dict[2] == "b"

    limited_dict[3] = "c"
    assert len(limited_dict) == 2
    assert 3 in limited_dict
    assert limited_dict[3] == "c"
    assert 1 not in limited_dict

    with raises(KeyError):
        limited_dict[1]


def test_nominal_not_increasing() -> None:
    limited_dict = LimitedDict(2)
    assert len(limited_dict) == 0

    limited_dict[3] = "c"
    assert len(limited_dict) == 1
    assert 3 in limited_dict
    assert limited_dict[3] == "c"

    limited_dict[2] = "b"
    assert len(limited_dict) == 2
    assert 2 in limited_dict
    assert limited_dict[2] == "b"

    limited_dict[1] = "a"
    assert len(limited_dict) == 2
    assert 1 not in limited_dict

    with raises(KeyError):
        limited_dict[1]
