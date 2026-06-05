"""Recursive / cyclic structures and depth boundaries (F6, F7).

marshal handles self-reference only from format version 3 onward (FLAG_REF).
Older versions detect the cycle and raise ``ValueError`` after exceeding an
internal nesting limit. Deeply (but finitely) nested structures probe the
recursion-depth guard in marshal.c (``MAX_MARSHAL_STACK_DEPTH``).
"""

import marshal

import pytest

import marshal_testkit as kit


# --- Self-referential containers (F6) --------------------------------------

@pytest.mark.parametrize("version", (0, 1, 2))
def test_self_referential_list_rejected_pre_v3(version):
    lst = []
    lst.append(lst)
    with pytest.raises(ValueError):
        marshal.dumps(lst, version)


@pytest.mark.parametrize("version", (3, 4))
def test_self_referential_list_ok_v3plus(version):
    lst = []
    lst.append(lst)
    data = marshal.dumps(lst, version)
    out = marshal.loads(data)
    assert out[0] is out          # cycle reconstructed via back-reference
    # And the encoding is deterministic within the process.
    assert marshal.dumps(lst, version) == data


def test_mutually_recursive_dicts_v4():
    a = {}
    b = {}
    a["b"] = b
    b["a"] = a
    out = marshal.loads(marshal.dumps(a, 4))
    assert out["b"]["a"] is out


def test_cycle_through_tuple_requires_ref():
    """A tuple cannot be built mid-cycle, so we wrap the cycle in a list."""
    inner = []
    t = (inner,)
    inner.append(t)
    out = marshal.loads(marshal.dumps(t, 4))
    assert out[0][0] is out


# --- Shared (non-cyclic) references and FLAG_REF size win (F7) --------------

def test_shared_reference_is_compact_in_v4():
    s = "a moderately long shared string value here" * 4
    pair = (s, s)
    big = marshal.dumps(pair, 0)
    small = marshal.dumps(pair, 4)
    assert len(small) < len(big)
    assert marshal.loads(small) == pair


def test_shared_reference_stable():
    s = "shared"
    obj = [s, s, s]
    assert kit.stable(obj, version=4)


# --- Depth boundary -------------------------------------------------------

def _nested_list(depth):
    obj = inner = []
    for _ in range(depth):
        new = []
        inner.append(new)
        inner = new
    return obj


def test_moderate_depth_roundtrips():
    obj = _nested_list(100)
    assert marshal.loads(marshal.dumps(obj)) == obj


def test_excessive_depth_raises_not_crashes():
    """Very deep nesting must raise cleanly (no segfault / silent truncation).

    The exact limit is implementation-defined; we only require a controlled
    exception. We search upward until it triggers to avoid hard-coding it.
    """
    raised = False
    for depth in (1_000, 5_000, 20_000, 100_000):
        try:
            marshal.dumps(_nested_list(depth))
        except ValueError:
            raised = True
            break
    assert raised, "expected a ValueError for pathologically deep nesting"
