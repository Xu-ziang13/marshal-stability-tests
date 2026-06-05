"""Determinism: does the same input always yield the same output bytes?

The assignment defines "same output" as *hash-identical*. These tests split
the question into two regimes:

* **Intra-process** -- repeated ``dumps`` in one interpreter. Expected stable
  for every supported type (T-DET-*).
* **Inter-process** -- ``dumps`` run in fresh interpreters with differing
  ``PYTHONHASHSEED``. This is where hash-randomised containers (sets of
  strings) reveal non-determinism (F1/F2).
"""

import marshal

import pytest

import marshal_testkit as kit


# --- Intra-process stability (positive cases) ------------------------------

@pytest.mark.parametrize("obj", kit.small_object_corpus())
def test_intra_process_stable_for_corpus(obj):
    """Repeated dumps within one process is always byte-identical."""
    assert kit.stable(obj)


@pytest.mark.parametrize("value", kit.INT_BOUNDARIES)
def test_intra_process_stable_ints(value):
    assert kit.stable(value)


@pytest.mark.parametrize("value", kit.STRING_VALUES)
def test_intra_process_stable_strings(value):
    assert kit.stable(value)


# --- Inter-process: integer sets are stable (F2) ---------------------------

@pytest.mark.parametrize("seed", ["0", "1", "42", "12345"])
def test_int_set_stable_across_hashseeds(seed):
    """A frozenset of ints hashes identically regardless of hash seed.

    Integers hash to themselves, so set iteration order is seed-independent.
    """
    baseline = kit.dumps_in_subprocess(
        "frozenset(range(50))", env={"PYTHONHASHSEED": "0"})
    other = kit.dumps_in_subprocess(
        "frozenset(range(50))", env={"PYTHONHASHSEED": seed})
    assert baseline == other


# --- Inter-process: string sets are NON-deterministic (F1) -----------------

def test_string_set_nondeterministic_across_hashseeds():
    """A set of *strings* serialises differently under different hash seeds.

    This documents F1: marshal output for hash-randomised containers is NOT
    stable across processes. The test asserts the bug exists; if a future
    CPython fixed it (e.g. by sorting), this test would flag the change.
    """
    expr = "{'apple', 'banana', 'cherry', 'date', 'egg', 'fig', 'grape'}"
    digests = {
        kit.dumps_in_subprocess(expr, env={"PYTHONHASHSEED": s})
        for s in ("0", "1", "2", "3", "4", "5", "6", "7")
    }
    # If output were stable we would see exactly one digest.
    assert len(digests) > 1, (
        "expected hash-seed-dependent output for a string set; "
        "got a single digest -- behaviour may have changed"
    )


def test_string_set_stable_when_hashseed_fixed():
    """Pinning PYTHONHASHSEED makes even string sets reproducible.

    This is the practical mitigation for F1 and is asserted so the report can
    recommend it with test backing.
    """
    expr = "{'apple', 'banana', 'cherry', 'date', 'egg'}"
    a = kit.dumps_in_subprocess(expr, env={"PYTHONHASHSEED": "0"})
    b = kit.dumps_in_subprocess(expr, env={"PYTHONHASHSEED": "0"})
    assert a == b


# --- Dict insertion-order sensitivity (F3) ---------------------------------

def test_dict_byte_output_depends_on_insertion_order():
    """Logically-equal dicts can produce different bytes (F3).

    marshal walks a dict in insertion order, so {1:0,2:0} and {2:0,1:0} differ
    byte-wise although they compare equal. This is a correctness-vs-stability
    nuance worth documenting, not a crash.
    """
    d1 = {1: 0, 2: 0}
    d2 = {2: 0, 1: 0}
    assert d1 == d2
    assert marshal.dumps(d1) != marshal.dumps(d2)


def test_equal_int_sets_built_differently_are_byte_equal():
    """Counterpart to F3: int sets normalise, so build order is irrelevant."""
    s1 = set()
    for i in (5, 3, 1, 4, 2):
        s1.add(i)
    s2 = set(range(1, 6))
    assert s1 == s2
    assert marshal.dumps(s1) == marshal.dumps(s2)
