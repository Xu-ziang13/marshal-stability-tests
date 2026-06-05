"""White-box: exercise each ``TYPE_*`` branch in CPython's ``marshal.c``.

The C writer (``w_object`` / ``w_complex_object``) dispatches on the object's
type to a one-byte type code. This module is a *structural* (white-box) suite:
it pins one representative per reachable type-code branch so that all major
write paths are covered (approximating all-defs / all-uses over the dispatch).

Type codes are taken from ``Python/marshal.c``. The high bit (0x80) is
``FLAG_REF`` and is masked off before comparison.
"""

import marshal

import pytest


FLAG_REF = 0x80


def code_of(obj, version=4):
    """Return the masked type-code character of the first marshalled byte."""
    raw = marshal.dumps(obj, version)
    return chr(raw[0] & ~FLAG_REF)


# (label, object, expected type-code char, version)
CASES = [
    ("NULL/None", None, "N", 4),
    ("True", True, "T", 4),
    ("False", False, "F", 4),
    ("StopIteration", StopIteration, "S", 4),
    ("Ellipsis", Ellipsis, ".", 4),
    ("int (TYPE_INT)", 5, "i", 4),
    ("big int (TYPE_LONG)", 2 ** 70, "l", 4),
    ("binary float (TYPE_BINARY_FLOAT)", 3.14, "g", 4),
    ("decimal float (TYPE_FLOAT, v0)", 3.14, "f", 0),
    ("binary complex (TYPE_BINARY_COMPLEX)", complex(1, 2), "y", 4),
    ("decimal complex (TYPE_COMPLEX, v0)", complex(1, 2), "x", 0),
    ("bytes (TYPE_STRING)", b"x", "s", 4),
    ("short ascii (TYPE_SHORT_ASCII)", "a b!@#", "z", 4),
    ("short ascii interned", "abc", "Z", 4),
    ("unicode (TYPE_UNICODE)", "é" * 300, "u", 4),
    ("long ascii (TYPE_ASCII)", "a" * 300, "A", 4),
    ("small tuple (TYPE_SMALL_TUPLE)", (1, 2), ")", 4),
    ("big tuple (TYPE_TUPLE)", tuple(range(300)), "(", 4),
    ("list (TYPE_LIST)", [1], "[", 4),
    ("dict (TYPE_DICT)", {1: 2}, "{", 4),
    ("set (TYPE_SET)", {1, 2}, "<", 4),
    ("frozenset (TYPE_FROZENSET)", frozenset({1, 2}), ">", 4),
]


@pytest.mark.parametrize(
    "label,obj,expected,version",
    CASES,
    ids=[c[0] for c in CASES],
)
def test_type_code_branch(label, obj, expected, version):
    assert code_of(obj, version) == expected


def test_flag_ref_set_only_when_object_is_shared():
    """FLAG_REF is lazy: a singly-used object does NOT carry it, but an
    object referenced twice does on its first occurrence (v3+).

    marshal only adds an object to the reference table when it is actually
    shared, so a freshly built standalone list head has no FLAG_REF.
    """
    standalone = marshal.dumps([1, 2, 3], 4)
    assert not (standalone[0] & FLAG_REF)

    shared = [1, 2, 3]
    raw = marshal.dumps([shared, shared], 4)
    # The inner list's first occurrence must be flagged so the second can ref.
    assert any(b & FLAG_REF for b in raw)
    assert 0x72 in raw                       # TYPE_REF for the 2nd occurrence


def test_flag_ref_absent_for_singletons():
    """Singletons (None/True/...) are not ref-tracked, so no FLAG_REF."""
    assert not (marshal.dumps(None, 4)[0] & FLAG_REF)


def test_back_reference_type_code_emitted():
    """A repeated object emits TYPE_REF ('r', 0x72) for later occurrences."""
    s = "a fairly long shared string to force a back reference xxxxxxxx"
    raw = marshal.dumps((s, s), 4)
    assert 0x72 in raw, "expected a TYPE_REF byte for the second occurrence"
