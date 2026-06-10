# Stability & Correctness Test Suite for Python's `marshal`

> **Group 15** · Software Testing Final Project
>
> | Role | Name | Student ID |
> |------|------|------------|
> | Leader | Wang Chengyi | 302023334044 |
> | Member | Zhu Guangjun | 302023334026 |
> | Member | Huang Huanxin | 302023334023 |
> | Member | Tang Junxi | 302023334032 |
> | Member | Xu Ziang | 302023334070 |

A black-box and white-box test suite investigating whether Python's
[`marshal`](https://docs.python.org/3/library/marshal.html) module produces
**hash-identical** output for the same input under all circumstances, and
whether serialization round-trips correctly.

> **Central question.** *Does the same input always create the same (serialized)
> output?* We require **byte/hash identity**, not mere logical equivalence.

## TL;DR findings

| # | Property tested | Result |
|---|-----------------|--------|
| F1 | `set`/`frozenset` of **strings** | ❌ **Non-deterministic across processes on Python ≤ 3.10** (PYTHONHASHSEED); ✅ Fixed in Python 3.11+ (marshal now sorts set elements) |
| F2 | `set`/`frozenset` of **ints/None/bools** | ✅ Stable (hash is identity-based) |
| F3 | `dict` byte-output depends on **insertion order** | ⚠️ Logically-equal dicts ≠ byte-equal |
| F4 | `-0.0` vs `+0.0` | ✅ Distinct bytes, sign preserved (correct) |
| F5 | `NaN` / `±Inf` / signalling NaN bit patterns | ✅ Preserved bit-exactly through round-trip |
| F6 | Recursive/cyclic objects | ⚠️ Raise `ValueError` for versions < 3; OK for v3/v4 (FLAG_REF) |
| F7 | Same object referenced twice (interning / `FLAG_REF`) | ✅ v3/v4 emit a back-reference; output shorter & still stable |
| F8 | Cross-`marshal`-version output | ⚠️ Not stable across format versions (by design) — documented & locked by tests |
| F9 | Within one process, repeated `dumps` of same object | ✅ Always hash-identical |

See [`report/report.md`](report/report.md) for the full discussion and the
traceability matrix.

## Layout

```
.
├── src/
│   └── marshal_testkit.py     # shared helpers (hashing, value corpora, fuzzers)
├── tests/
│   ├── test_determinism.py    # same-input/same-output, intra- & inter-process
│   ├── test_roundtrip.py      # correctness: loads(dumps(x)) == x
│   ├── test_floats.py         # BVA + special FP values
│   ├── test_collections.py    # sets/dicts/empty/large, ordering effects
│   ├── test_recursive.py      # cyclic & deeply-nested structures
│   ├── test_versions.py       # cross-version format stability
│   ├── test_typecodes.py      # white-box: one test per marshal.c TYPE_* branch
│   └── test_fuzz.py           # randomized property-based fuzzing (no deps)
├── tools/
│   └── run_multiversion.py    # run pytest across Python 3.8–3.13 via conda
│   ├── f1_set_hashseed.py     # reproduces the string-set non-determinism
│   └── run_all_findings.py    # prints an evidence report
├── requirements.txt
├── pytest.ini
└── report/report.md
```

## Running

```bash
python3 -m pytest -q                 # full suite
python3 -m pytest -q tests/test_determinism.py
python3 findings/run_all_findings.py # human-readable evidence dump
```

### Multi-version testing (Python 3.8–3.13)

Requires [conda](https://docs.conda.io/) with environments named after the
version numbers (`3.8`, `3.9`, …, `3.13`). Create them with:

```bash
for v in 3.8 3.9 3.10 3.11 3.12 3.13; do
    conda create -n $v python=$v -y
done
```

Then run:

```bash
python3 tools/run_multiversion.py                   # all versions
python3 tools/run_multiversion.py --versions 3.10 3.11 3.12
python3 tools/run_multiversion.py --no-install      # skip dep install
```

Results are written to `results/multiversion-<os>/` with per-version
`pytest_output.txt` and `summary.json`. The summary table printed at the
end shows pass/fail for each version at a glance.

Only **pytest** is required. `hypothesis` is optional; `test_fuzz.py` uses it
when present and otherwise falls back to a built-in deterministic random fuzzer.

## Environment used

- macOS (Darwin 23.1.0), arm64, CPython 3.9.6, `marshal.version == 4`
- Multi-version suite verified on CPython 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
  (all 656 tests pass on every version)
- The cross-version *format* tests are written to also run on other CPython
  versions; the suite records the running interpreter in its output.

## PEP 8

```bash
python3 -m flake8 src tests findings      # if flake8 installed
python3 -m pycodestyle src tests findings  # alternative
```
