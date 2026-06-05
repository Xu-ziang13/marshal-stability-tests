"""Correctness: ``loads(dumps(x))`` must reproduce ``x``.

Determinism is meaningless if the bytes do not decode back to the original
value. These tests cover the supported type space via equivalence partitions
and check both logical equality and, where it matters, byte/identity nuances.
"""

import marshal

import pytest

import marshal_testkit as kit


@pytest.mark.parametrize("obj", kit.small_object_corpus())
def test_roundtrip_corpus(obj):
    assert kit.roundtrips(obj)


@pytest.mark.parametrize("value", kit.INT_BOUNDARIES)
def test_roundtrip_int_boundaries(value):
    assert marshal.loads(marshal.dumps(value)) == value


@pytest.mark.parametrize("value", kit.STRING_VALUES)
def test_roundtrip_strings(value):
    out = marshal.loads(marshal.dumps(value))
    assert out == value
    assert isinstance(out, str)


def test_roundtrip_bytes_and_bytearray_types():
    """bytes stays bytes; bytearray decodes back to bytes (documented quirk).

    marshal has no distinct bytearray type code, so a bytearray round-trips to
    an equal *bytes* object. We assert the value matches but the type changes.
    """
    assert marshal.loads(marshal.dumps(b"abc")) == b"abc"
    out = marshal.loads(marshal.dumps(bytearray(b"abc")))
    assert out == b"abc"
    assert isinstance(out, bytes)


def test_singletons_preserved_by_identity():
    for singleton in (None, True, False, Ellipsis, StopIteration):
        assert marshal.loads(marshal.dumps(singleton)) is singleton


def test_nested_structure_roundtrip():
    obj = {
        "ints": list(range(20)),
        "nested": [[1, 2], (3, 4), {"deep": {"deeper": [None, True]}}],
        "bytes": b"\x00\xff",
        "frozen": frozenset({1, 2, 3}),
    }
    assert marshal.loads(marshal.dumps(obj)) == obj


def test_unmarshallable_type_raises():
    """Unsupported objects raise ValueError, not silent corruption."""
    with pytest.raises(ValueError):
        marshal.dumps(lambda x: x)
    with pytest.raises(ValueError):
        marshal.dumps(object())
