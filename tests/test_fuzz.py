"""Property-based fuzzing.

Two invariants are fuzzed over randomly generated objects:

* **Round-trip**: ``loads(dumps(x)) == x``.
* **Idempotent encoding**: ``dumps(x) == dumps(x)`` within a process.

If ``hypothesis`` is installed it drives generation (with shrinking); otherwise
a dependency-free deterministic random generator is used so the suite still
runs everywhere. The seed is fixed so failures are reproducible.
"""

import marshal
import random

import pytest

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
    HAS_HYPOTHESIS = True
except ImportError:                          # pragma: no cover - env dependent
    HAS_HYPOTHESIS = False


# --------------------------------------------------------------------------
# Dependency-free recursive object generator.
# --------------------------------------------------------------------------

def _gen(rng, depth=0):
    """Generate a random marshallable object using *rng* (random.Random)."""
    leaf = depth >= 4
    choices = ["none", "bool", "int", "float", "str", "bytes"]
    if not leaf:
        choices += ["list", "tuple", "dict", "frozenset"]
    kind = rng.choice(choices)
    if kind == "none":
        return None
    if kind == "bool":
        return rng.choice([True, False])
    if kind == "int":
        return rng.randint(-(2 ** 80), 2 ** 80)
    if kind == "float":
        return rng.choice([
            rng.uniform(-1e9, 1e9), 0.0, -0.0,
            float("inf"), float("-inf"),
        ])
    if kind == "str":
        n = rng.randint(0, 12)
        return "".join(rng.choice("ab cé你🦄\x00") for _ in range(n))
    if kind == "bytes":
        return bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 12)))
    if kind == "list":
        return [_gen(rng, depth + 1) for _ in range(rng.randint(0, 5))]
    if kind == "tuple":
        return tuple(_gen(rng, depth + 1) for _ in range(rng.randint(0, 5)))
    if kind == "frozenset":
        # Only hashable leaves to keep it valid.
        return frozenset(
            rng.choice([rng.randint(0, 99), rng.random(), None])
            for _ in range(rng.randint(0, 5))
        )
    # dict
    return {
        rng.randint(0, 999): _gen(rng, depth + 1)
        for _ in range(rng.randint(0, 5))
    }


@pytest.mark.parametrize("seed", range(200))
def test_fuzz_roundtrip_builtin(seed):
    rng = random.Random(seed)
    obj = _gen(rng)
    assert marshal.loads(marshal.dumps(obj, 4)) == obj


@pytest.mark.parametrize("seed", range(200))
def test_fuzz_idempotent_builtin(seed):
    rng = random.Random(seed)
    obj = _gen(rng)
    assert marshal.dumps(obj, 4) == marshal.dumps(obj, 4)


# --------------------------------------------------------------------------
# Hypothesis-driven version (richer shrinking) when available.
# --------------------------------------------------------------------------

if HAS_HYPOTHESIS:
    _leaves = (
        st.none() | st.booleans() | st.integers()
        | st.floats(allow_nan=False) | st.text() | st.binary()
    )
    _objects = st.recursive(
        _leaves,
        lambda children: (
            st.lists(children)
            | st.dictionaries(st.integers(), children)
        ),
        max_leaves=30,
    )

    @settings(max_examples=300, deadline=None)
    @given(_objects)
    def test_fuzz_roundtrip_hypothesis(obj):
        assert marshal.loads(marshal.dumps(obj, 4)) == obj

    @settings(max_examples=300, deadline=None)
    @given(_objects)
    def test_fuzz_idempotent_hypothesis(obj):
        assert marshal.dumps(obj, 4) == marshal.dumps(obj, 4)
