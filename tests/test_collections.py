"""Collections: empty / large / ordering (equivalence + boundary analysis).

Covers the container type codes and the stability nuances introduced by hash
randomisation (sets) and insertion order (dicts). Large-collection cases probe
the int32 length field used by marshal for sized objects.
"""

import marshal

import pytest

import marshal_testkit as kit


# --- Empty containers (boundary: size 0) -----------------------------------

@pytest.mark.parametrize("empty", [
    (), [], {}, set(), frozenset(), b"", "", bytearray(b""),
])
def test_empty_containers_roundtrip_and_stable(empty):
    assert kit.stable(empty)
    out = marshal.loads(marshal.dumps(empty))
    # set/frozenset/bytearray normalise type or value; compare by equality.
    assert out == empty or list(out) == list(empty)


# --- Singletons inside containers ------------------------------------------

def test_single_element_containers():
    for obj in ([1], (1,), {1}, frozenset({1}), {1: 2}):
        assert kit.roundtrips(obj)
        assert kit.stable(obj)


# --- Large containers (boundary: many elements) ----------------------------

@pytest.mark.parametrize("n", [0, 1, 255, 256, 65535, 65536, 100_000])
def test_large_list_roundtrip(n):
    data = list(range(n))
    assert marshal.loads(marshal.dumps(data)) == data


def test_large_list_is_stable():
    data = list(range(100_000))
    assert kit.stable(data, repeats=3)


def test_large_string_roundtrip():
    s = "x" * 1_000_000
    assert marshal.loads(marshal.dumps(s)) == s


def test_large_bytes_roundtrip():
    b = b"\x00\x01\x02\x03" * 250_000
    assert marshal.loads(marshal.dumps(b)) == b


# --- Set ordering: ints stable, strings not (links F1/F2) ------------------

def test_int_set_intra_process_stable():
    assert kit.stable(set(range(1000)))


def test_nested_frozenset_roundtrip():
    fs = frozenset({frozenset({1, 2}), frozenset({3, 4})})
    assert marshal.loads(marshal.dumps(fs)) == fs


# --- Tuple vs list distinction preserved -----------------------------------

def test_tuple_and_list_are_distinct_types_after_load():
    out_t = marshal.loads(marshal.dumps((1, 2, 3)))
    out_l = marshal.loads(marshal.dumps([1, 2, 3]))
    assert isinstance(out_t, tuple)
    assert isinstance(out_l, list)
    assert marshal.dumps((1, 2, 3)) != marshal.dumps([1, 2, 3])
