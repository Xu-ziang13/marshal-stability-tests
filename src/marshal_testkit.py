"""Shared helpers for the marshal test suite.

This module centralises:

* ``digest`` / ``stable`` -- hash-identity checks (the assignment defines
  "same output" as *hash-identical*, not merely logically equal).
* value corpora used across several test modules (equivalence-partition
  representatives and boundary values).
* a dependency-free deterministic fuzzer used by ``tests/test_fuzz.py`` when
  ``hypothesis`` is not installed.
* ``dumps_in_subprocess`` -- run ``marshal.dumps`` in a *fresh* interpreter so
  that hash-seed randomisation (PYTHONHASHSEED) is exercised, which a single
  long-lived process cannot reveal.
"""

import hashlib
import marshal
import os
import subprocess
import sys

# All marshal format versions that exist in CPython today.
ALL_VERSIONS = (0, 1, 2, 3, 4)

# Versions that support FLAG_REF / object references (and therefore cycles).
REF_VERSIONS = (3, 4)


def digest(payload):
    """Return a short stable hex digest of a bytes payload."""
    return hashlib.sha256(payload).hexdigest()


def dumps(obj, version=marshal.version):
    """Thin wrapper so tests read intentionally."""
    return marshal.dumps(obj, version)


def stable(obj, version=marshal.version, repeats=50):
    """True iff repeated dumps of *obj* are byte-identical in this process."""
    first = marshal.dumps(obj, version)
    return all(marshal.dumps(obj, version) == first for _ in range(repeats))


def roundtrips(obj, version=marshal.version):
    """True iff ``loads(dumps(obj)) == obj`` (logical equality)."""
    return marshal.loads(marshal.dumps(obj, version)) == obj


def dumps_in_subprocess(literal_expr, version=marshal.version, env=None):
    """Marshal ``eval(literal_expr)`` in a brand-new interpreter.

    Returns the hex digest of the produced bytes. A fresh process is the only
    way to observe PYTHONHASHSEED-driven non-determinism, because the seed is
    fixed once per process at start-up.
    """
    code = (
        "import marshal, hashlib, sys\n"
        "obj = eval(sys.argv[1])\n"
        "sys.stdout.write("
        "hashlib.sha256(marshal.dumps(obj, int(sys.argv[2]))).hexdigest())\n"
    )
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    out = subprocess.check_output(
        [sys.executable, "-c", code, literal_expr, str(version)],
        env=run_env,
    )
    return out.decode().strip()


# ---------------------------------------------------------------------------
# Equivalence-partition representatives and boundary values.
# ---------------------------------------------------------------------------

# Integers: small, word boundaries, and big-int (PyLong digit) boundaries.
INT_BOUNDARIES = [
    0, 1, -1,
    255, 256, -256,
    2 ** 15 - 1, 2 ** 15, -(2 ** 15),       # short
    2 ** 31 - 1, 2 ** 31, -(2 ** 31),       # int32
    2 ** 32 - 1, 2 ** 32,                    # uint32
    2 ** 63 - 1, 2 ** 63, -(2 ** 63),       # int64
    2 ** 64 - 1, 2 ** 64,                    # uint64
    2 ** 1000, -(2 ** 1000),                 # arbitrary precision big int
]

# Floats: ordinary, subnormal, boundaries, and special values.
FLOAT_VALUES = [
    0.0, -0.0, 1.0, -1.0, 0.1, 1.0 / 3.0,
    sys.float_info.max, sys.float_info.min,
    sys.float_info.epsilon,
    5e-324,                                  # smallest subnormal
    float("inf"), float("-inf"), float("nan"),
]

# Strings: empty, ascii, unicode, surrogates-via-codepoints, long, latin-1.
STRING_VALUES = [
    "", "a", "ascii", "ünïcödé", "你好", "🦄",
    "x" * 10_000, "\x00\x01\x02", "line\nbreak",
]


def small_object_corpus():
    """A flat list of single representatives across the type space."""
    return [
        None, True, False, StopIteration, Ellipsis,
        0, -1, 2 ** 70, 3.14, -0.0, complex(1, -2),
        b"bytes", bytearray(b"ba"), "text",
        (), (1, 2, 3), [], [1, [2, [3]]],
        {}, {"k": "v"}, frozenset({1, 2, 3}),
    ]
