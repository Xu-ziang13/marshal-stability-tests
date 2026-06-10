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
>
> **Report:** [FINAL_REPORT.md](FINAL_REPORT.md)
> **Repository:** https://github.com/Xu-ziang13/marshal-stability-tests

---

## What is this?

Python's [`marshal`](https://docs.python.org/3/library/marshal.html) module
serializes Python objects to binary byte streams. It is primarily used to
write `.pyc` bytecode cache files. This project tests whether marshal is
**stable and correct**:

> *Does the same input always create the same (serialized) output?*

"Same output" means **byte/hash identity** — two outputs must have identical
SHA-256 digests. Logical equality (`==`) is not sufficient.

We apply six testing techniques: equivalence partitioning, boundary value
analysis, special-value testing, differential cross-process testing,
property-based fuzzing (hypothesis), and white-box type-code branch coverage.

---

## Key Findings

| # | Property | Result |
|---|----------|--------|
| F1 | `set`/`frozenset` of **strings** cross-process | ❌ Non-deterministic on **Python ≤ 3.10** (PYTHONHASHSEED); ✅ **Fixed in Python 3.11+** |
| F2 | `set`/`frozenset` of **ints/None/bools** cross-process | ✅ Always stable (integer hash = identity) |
| F3 | `dict` byte-output vs insertion order | ⚠️ Logically-equal dicts produce different bytes |
| F4 | Signed zero: `-0.0` vs `+0.0` | ✅ Distinct bytes, sign bit preserved correctly |
| F5 | NaN / ±Inf / signalling-NaN bit patterns | ✅ Full 64-bit pattern preserved bit-exactly |
| F6 | Cyclic / self-referential objects | ⚠️ `ValueError` on format v0–v2; handled correctly on v3/v4 |
| F7 | Shared object referenced twice | ✅ v3/v4 emit a `TYPE_REF` back-reference; output compacted |
| F8 | Output across marshal format versions | ⚠️ Three distinct encodings across v0–v4 (by design) |
| F9 | Repeated `dumps` within one process | ✅ Always hash-identical |

**Answer to the central question:** `marshal` is deterministic within a
single process. Across processes, stability depends on Python version:
string sets are non-deterministic on Python ≤ 3.10 (F1) but the issue was
**fixed in Python 3.11**, where marshal sorts set elements before writing.

---

## Test Suite at a Glance

| Metric | Value |
|--------|-------|
| Total test cases | **656** |
| Pass rate | **100%** |
| Line coverage | **99%** |
| Python versions tested | **3.8, 3.9, 3.10, 3.11, 3.12, 3.13** |
| `TYPE_*` branches covered (white-box) | **22 / 22** |
| Marshal format versions tested | **v0, v1, v2, v3, v4** |
| Fuzz iterations | **~1000** (400 built-in + 600 hypothesis) |

---

## Repository Layout

```
.
├── src/
│   └── marshal_testkit.py        # shared helpers: digest(), stable(),
│                                 # roundtrips(), dumps_in_subprocess(),
│                                 # value corpora (INT_BOUNDARIES, etc.)
│
├── tests/
│   ├── test_determinism.py       # intra- & inter-process stability (F1–F3, F9)
│   ├── test_roundtrip.py         # correctness: loads(dumps(x)) == x
│   ├── test_floats.py            # BVA + IEEE-754 special values (F4, F5)
│   ├── test_collections.py       # empty/large containers, ordering effects
│   ├── test_recursive.py         # cyclic structures, FLAG_REF depth (F6, F7)
│   ├── test_versions.py          # cross-version format stability (F8)
│   ├── test_typecodes.py         # white-box: one test per TYPE_* branch
│   └── test_fuzz.py              # property-based fuzzing (hypothesis + built-in)
│
├── tools/
│   └── run_multiversion.py       # run pytest across Python 3.8–3.13 via conda
│
├── findings/
│   ├── f1_set_hashseed.py        # standalone script: reproduce F1 evidence
│   └── run_all_findings.py       # print evidence for all 9 findings (F1–F9)
│
├── results/
│   └── multiversion-macos/       # pre-collected results: macOS arm64, 6 versions
│       ├── summary.json          # cross-version pass/fail overview
│       ├── py38/                 # Python 3.8.20
│       │   ├── pytest_output.txt # full pytest -v output
│       │   └── summary.json      # version, status, passed/failed counts
│       ├── py39/                 # Python 3.9.25
│       ├── py310/                # Python 3.10.20
│       ├── py311/                # Python 3.11.15
│       ├── py312/                # Python 3.12.13
│       └── py313/                # Python 3.13.13
│
├── FINAL_REPORT.md               # full report with traceability matrix
├── conftest.py                   # adds src/ to sys.path for pytest
├── pytest.ini                    # pytest configuration
└── requirements.txt              # pytest + hypothesis (hypothesis optional)
```

---

## Quick Start

### Prerequisites

- Python 3.8 or later
- `pip install pytest` (required)
- `pip install hypothesis` (optional; `test_fuzz.py` falls back to a
  built-in deterministic fuzzer if not installed)

### Run the full test suite

```bash
git clone https://github.com/Xu-ziang13/marshal-stability-tests.git
cd marshal-stability-tests
pip install -r requirements.txt
python3 -m pytest -q
```

Expected output:

```
656 passed in ~5s
```

### Run a specific module

```bash
python3 -m pytest tests/test_determinism.py -v   # stability tests
python3 -m pytest tests/test_floats.py -v        # float BVA + special values
python3 -m pytest tests/test_typecodes.py -v     # white-box branch coverage
```

### Print human-readable evidence for all findings

```bash
python3 findings/run_all_findings.py
```

This prints concrete bytes and SHA-256 digests backing each of the 9
findings, including the F1 string-set non-determinism demonstration.

### Reproduce F1 specifically

```bash
python3 findings/f1_set_hashseed.py
```

Spawns 6 subprocesses with different `PYTHONHASHSEED` values and shows
that string-set digests diverge (Python ≤ 3.10) or converge (Python 3.11+).

---

## Multi-Version Testing (Python 3.8–3.13)

The `tools/run_multiversion.py` script runs the full pytest suite under
each Python version via conda, then prints a summary table.

### Setup conda environments

```bash
# Create one environment per version (only needed once)
for v in 3.8 3.9 3.10 3.11 3.12 3.13; do
    conda create -n $v python=$v -y
done
```

### Run

```bash
# All versions (auto-installs pytest + hypothesis in each env)
python3 tools/run_multiversion.py

# Selected versions only
python3 tools/run_multiversion.py --versions 3.10 3.11 3.12

# Custom output directory
python3 tools/run_multiversion.py --output-dir results/multiversion-linux

# Skip automatic dependency install (if already installed)
python3 tools/run_multiversion.py --no-install
```

### Example output

```
Platform : macOS-14.1.2-arm64-arm-64bit
Versions : 3.8, 3.9, 3.10, 3.11, 3.12, 3.13

[INFO] Python 3.8  (3.8.20 ...)
    [pytest] ✅ PASSED — passed=656  failed=0
[INFO] Python 3.9  (3.9.25 ...)
    [pytest] ✅ PASSED — passed=656  failed=0
...

======================================================
MULTI-VERSION SUMMARY
======================================================
Version   Status      Passed    Failed
------------------------------------------------------
3.8       ✅ passed    656       0
3.9       ✅ passed    656       0
3.10      ✅ passed    656       0
3.11      ✅ passed    656       0
3.12      ✅ passed    656       0
3.13      ✅ passed    656       0
======================================================
```

Pre-collected results for macOS arm64 are in
[`results/multiversion-macos/`](results/multiversion-macos/).

---

## Test Techniques Used

| Technique | Where applied | Purpose |
|-----------|--------------|---------|
| Equivalence Partitioning | `test_roundtrip.py`, `test_collections.py` | Cover all 8 Python type classes |
| Boundary Value Analysis | `test_floats.py`, `test_collections.py` | Int word boundaries (2³¹, 2⁶³…), collection sizes (0, 255, 256…) |
| Special-value testing | `test_floats.py` | NaN, ±Inf, -0.0, signalling NaN |
| Differential testing | `test_determinism.py` | Spawn fresh subprocesses with different PYTHONHASHSEED |
| Property-based fuzzing | `test_fuzz.py` | Randomly-generated nested objects; round-trip + idempotency invariants |
| White-box branch coverage | `test_typecodes.py` | One input per `TYPE_*` branch in `Python/marshal.c` |

---

## Environment

- **Primary:** macOS Darwin 23.1.0, arm64, CPython 3.9.6, `marshal.version == 4`
- **Multi-version:** CPython 3.8 – 3.13 (conda), all 656 tests pass on every version
- **No external runtime dependencies** beyond `pytest` and optionally `hypothesis`

## PEP 8 Compliance

```bash
python3 -m pycodestyle src tests findings   # 0 violations
```
