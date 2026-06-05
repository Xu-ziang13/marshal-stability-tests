# Stability & Correctness Testing of Python's `marshal` Module

**Course:** Software Testing — Final Project
**Repository:** `https://github.com/<your-username>/marshal-stability-tests`
**Environment under test:** CPython 3.9.6 (`marshal.version == 4`), macOS/Darwin 24.4.0, x86-64.

---

## 1. Introduction & Test Objective

The `marshal` module serialises Python's internal object types to a binary byte
stream, primarily to write the pseudo-compiled bytecode in `.pyc` files. The
central question of this project is:

> **Does the same input always produce the same serialized output?**

Following the assignment definition, *"same output"* means **hash-identical**
(byte-for-byte), not merely logically equivalent. A secondary objective is
**correctness**: the bytes must decode back to the original value
(`loads(dumps(x)) == x`).

We treat `marshal` as the *unit under test* and frame two top-level
requirements:

- **R-STAB** — *Stability*: for a fixed input and fixed format version, output
  is hash-identical across repetitions, processes, and (where the format is
  shared) interpreter versions.
- **R-CORR** — *Correctness*: serialization is loss-free and round-trips.

The remainder of the report describes the strategy (§2), the test suite (§3),
technique justification (§4), the traceability matrix (§5), findings (§6), and
limitations (§7).

## 2. Testing Strategy

We combined **black-box** and **white-box** techniques, chosen per
sub-problem rather than applying one technique uniformly:

- **Equivalence Partitioning (EP)** — partition the supported type space
  (None/bool/int/float/complex/str/bytes/tuple/list/dict/set/frozenset) and
  pick one representative per class for round-trip and stability.
- **Boundary Value Analysis (BVA)** — integer word boundaries
  (2⁷, 2¹⁵, 2³¹, 2³², 2⁶³, 2⁶⁴, big-int digits), collection sizes
  (0, 1, 255, 256, 65535, 65536, 10⁵), float subnormals/extremes, and nesting
  depth.
- **Special-value testing** — `NaN`, `±Inf`, signalling-NaN payloads, `-0.0`.
- **Fuzzing / property-based testing** — randomly generated nested objects
  checked against two invariants (round-trip, idempotent encoding), driven by
  `hypothesis` when available and a deterministic built-in generator otherwise.
- **White-box structural testing** — one test per `TYPE_*` dispatch branch in
  CPython's `Python/marshal.c` `w_object`/`w_complex_object`, approximating
  *all-uses* coverage of the type-code definition table, plus the `FLAG_REF`
  and `TYPE_REF` reference-table paths.
- **Differential / cross-configuration testing** — the same input is
  marshalled in **fresh subprocesses** under different `PYTHONHASHSEED` values,
  and across all five format versions, comparing digests.

Stability is verified with SHA-256 digests so equality is exact, not
structural. We deliberately distinguish **intra-process** stability (one
interpreter) from **inter-process** stability (new interpreters), because the
most important non-determinism is invisible to a single long-lived process.

## 3. Test Suite Overview

Code is in `tests/` (pytest), shared fixtures/corpora in
`src/marshal_testkit.py`, and standalone evidence scripts in `findings/`. The
suite runs with **654 tests, all passing, in ~0.5 s** using only the standard
library + pytest. (`hypothesis` adds richer fuzzing when installed.)

| Module | Technique(s) | Focus |
|---|---|---|
| `test_determinism.py` | Differential, EP | Intra- vs inter-process stability; set/dict ordering |
| `test_roundtrip.py` | EP | `loads(dumps(x)) == x`; type preservation; error paths |
| `test_floats.py` | BVA, special-value | IEEE-754 bit-exactness, `-0.0`, NaN/Inf, subnormals |
| `test_collections.py` | EP, BVA | Empty/large containers, ordering, type distinction |
| `test_recursive.py` | BVA, white-box | Cycles, `FLAG_REF`, depth limit |
| `test_versions.py` | Differential | Cross-version format (in)stability |
| `test_typecodes.py` | White-box | One representative per `TYPE_*` branch |
| `test_fuzz.py` | Fuzzing | Property invariants over random objects |

The helper `dumps_in_subprocess(expr, env=...)` spawns a clean interpreter and
returns the digest, which is what makes the hash-seed findings reproducible.

## 4. Why These Techniques (and Why Not Others)

**Equivalence Partitioning** is the backbone: `marshal`'s behaviour is
type-driven, so partitioning by Python type and by encoding sub-path (e.g.
short-ascii vs long-ascii vs unicode strings) gives high coverage for low
redundancy.

**Boundary Value Analysis** is highly relevant because `marshal` switches
encodings at numeric boundaries (`TYPE_INT` ↔ `TYPE_LONG`, small-tuple ↔ tuple
at 256 elements, decimal ↔ binary floats) and uses fixed-width length fields.
Bugs in serializers cluster at exactly these size boundaries, so BVA is
applied to ints, collection lengths, float magnitudes, and nesting depth.

**Special-value testing** is essential for floats: the format stores raw
IEEE-754 bytes, so `NaN` payloads, signalling NaNs, signed zero, and infinities
are precisely where a format could silently normalise and lose information.

**Fuzzing** complements EP/BVA by exploring *combinations* (deeply nested,
mixed-type structures) that hand-written cases miss, and checks invariants
rather than fixed expected outputs.

**White-box `TYPE_*` coverage** is justified because the C source is available
and the writer is essentially a large `switch` on type. Covering each branch
gives a concrete, auditable completeness criterion (close to all-uses on the
type-code table). We approximate rather than instrument coverage because the
unit under test is a C extension, not pure Python (see §7).

**Techniques we deliberately limited:**

- *Decision/condition coverage with instrumentation* on `marshal.c` was **not**
  performed: instrumenting and rebuilding CPython's C core is out of scope and
  brittle; we substitute branch-representative black-box cases.
- *State-transition testing* is **not** applicable — `marshal` is stateless
  per call (no session/protocol state to model).
- *Exhaustive value enumeration* is infeasible (infinite int/float/str spaces);
  BVA + fuzzing are the principled substitutes.

## 5. Traceability Matrix

Each requirement maps to findings (F#) and the tests that exercise it.

| Req | Sub-requirement | Finding | Tests |
|---|---|---|---|
| R-STAB.1 | Repeated dumps in one process are identical | F9 | `test_determinism::test_intra_process_stable_*`, `test_floats::test_nan_is_stable_within_process` |
| R-STAB.2 | Int/None/bool sets stable across processes | F2 | `test_determinism::test_int_set_stable_across_hashseeds` |
| R-STAB.3 | **String sets stable across processes** | **F1 ❌** | `test_determinism::test_string_set_nondeterministic_across_hashseeds`, `findings/f1_set_hashseed.py` |
| R-STAB.4 | Fixing `PYTHONHASHSEED` restores stability | F1 | `test_determinism::test_string_set_stable_when_hashseed_fixed` |
| R-STAB.5 | Dict byte-output vs insertion order | F3 | `test_determinism::test_dict_byte_output_depends_on_insertion_order` |
| R-STAB.6 | Output identical across format versions | F8 ⚠️ | `test_versions::*` |
| R-CORR.1 | Round-trip for all types | — | `test_roundtrip::*`, `test_collections::*`, `test_fuzz::*` |
| R-CORR.2 | Signed zero preserved | F4 | `test_floats::test_signed_zero_distinct_and_preserved` |
| R-CORR.3 | NaN/Inf/sNaN bit-exact | F5 | `test_floats::test_*nan*`, `test_*infinit*` |
| R-CORR.4 | Cycles handled or cleanly rejected | F6 | `test_recursive::test_self_referential_*` |
| R-CORR.5 | Shared refs compact & correct (v3+) | F7 | `test_recursive::test_shared_reference_*`, `test_typecodes::test_back_reference_*` |
| R-CORR.6 | Unsupported types raise, not corrupt | — | `test_roundtrip::test_unmarshallable_type_raises` |
| R-CORR.7 | Each `TYPE_*` branch encodes/decodes | — | `test_typecodes::test_type_code_branch` (22 branches) |
| R-CORR.8 | Pathological depth raises, no crash | F6 | `test_recursive::test_excessive_depth_raises_not_crashes` |

**White-box branch coverage (type codes):** the 22 cases in `test_typecodes`
cover `TYPE_NONE, TRUE, FALSE, STOPITER, ELLIPSIS, INT, LONG, FLOAT,
BINARY_FLOAT, COMPLEX, BINARY_COMPLEX, STRING, SHORT_ASCII,
SHORT_ASCII_INTERNED, ASCII, UNICODE, SMALL_TUPLE, TUPLE, LIST, DICT, SET,
FROZENSET`, plus `FLAG_REF` and `TYPE_REF`. Codes were verified empirically
against the running interpreter, not assumed.

## 6. Findings

The headline result: **`marshal` is *not* unconditionally deterministic.**
Whether output is hash-identical depends on the object graph and the process
environment.

**F1 — String/`bytes` sets are non-deterministic across processes (the key
bug-class).** A `set`/`frozenset` of strings serialises to *different* bytes in
different interpreter runs, because set iteration order derives from
string hashes, which CPython randomises per process (`PYTHONHASHSEED`). Our
script shows **6 distinct digests over 6 seeds**:

```
PYTHONHASHSEED  string-set digest   int-set digest
0               affb5aec9ee10e09    7b9d4189b59f309e
1               ea027e95c060ee7f    7b9d4189b59f309e
...             (all different)     (all identical)
```

This directly violates "same input → same output" for any program that
marshals string-keyed sets without pinning the seed. It is the reason build
systems set `PYTHONHASHSEED=0` for reproducible `.pyc` output. *Note:* `dict`
preserves insertion order, so string **dicts** are stable across seeds — only
**sets/frozensets** are affected.

**F2 — Integer/`None`/`bool` sets are stable.** These objects hash to fixed
values (ints hash to themselves), so iteration order is seed-independent: **1
distinct digest across all seeds**. Stability therefore depends on element
type, a subtle and easily-missed distinction.

**F3 — Dict byte-output depends on insertion order.** `{1:0,2:0}` and
`{2:0,1:0}` are logically equal but produce different bytes. Not a bug, but a
correctness-vs-stability nuance: logical equality does **not** imply byte
equality, reinforcing why the assignment demands hash-identity.

**F4 — Signed zero is preserved** (`+0.0` → `…00`, `-0.0` → `…80`), correctly
distinct and round-tripping.

**F5 — NaN/Inf/signalling-NaN are bit-exact.** The binary float path preserves
the full 64-bit pattern including the NaN payload (`0x7FF0000000000001`
survives). No normalisation/loss observed — a positive correctness result.

**F6 — Cycles: version-dependent behaviour.** Self-referential containers
**raise `ValueError("object too deeply nested")` for versions 0–2** but
serialise correctly via back-references at **v3/v4**. The depth guard also
cleanly rejects pathologically deep (non-cyclic) nesting with a `ValueError`
rather than crashing — verified no segfault/silent truncation.

**F7 — Reference table works and compacts output.** With a shared string,
`(s, s)` is **351 bytes at v0 vs 177 at v4**; the second occurrence emits
`TYPE_REF` and the cycle/identity is reconstructed (`out[0] is out`).

**F8 — Cross-version output is intentionally unstable.** For `0.1` we observe
**3 distinct encodings** across versions: v0/v1 decimal-text float, v2 binary
float, v3/v4 binary float **+ FLAG_REF**. The float binary encoding starts at
**v2** (not v1, a common misconception), and v3 differs from v2 only by the
`FLAG_REF` bit. These are pinned by tests so a default-version change is caught.

**F9 — Intra-process determinism holds universally.** 100 repeated dumps of a
mixed object yield **1 digest**; every corpus/boundary value is stable within a
process. So the non-determinism is strictly *cross-process*, never *within* a
run.

**Summary:** `marshal` is deterministic **within a process** and for
identity-hashed data, **loss-free** for all tested values (including IEEE-754
edge cases), but **not reproducible across processes for hash-randomised
containers** and **not stable across format versions** (by design). The
practical correctness recommendation — fix `PYTHONHASHSEED` and pin the format
version for any reproducible-build use of `marshal` — is backed by tests
(R-STAB.4).

## 7. Limitations & Shortcomings

- **Single platform/version measured.** Findings were produced on CPython 3.9.6
  / macOS. The format and version-specific tests are written to run on other
  CPython versions, but we did not execute on Windows/Linux or PyPy. The
  architecture-independence claim (endianness) is therefore argued from the
  format (binary floats stored little-endian via `_PyFloat_Pack8`) rather than
  measured cross-architecture.
- **No true C-level coverage instrumentation.** White-box coverage of
  `marshal.c` is *representative* (one input per `TYPE_*` branch), not measured
  via gcov; some error branches (I/O errors, allocation failure) are
  unreachable from pure-Python inputs and untested.
- **Code-object marshalling is out of scope.** `.pyc` files mostly contain code
  objects; we test data types, not `TYPE_CODE`, because code-object equality
  and reproducibility add confounding factors (line tables, filenames).
- **Fuzzer scope.** The built-in generator avoids constructing cyclic inputs
  and caps depth at 4; very large/deep adversarial graphs are only partially
  explored. `hypothesis` shrinking is available but not run in CI by default.
- **`-0.0`/NaN inside containers** and exotic str encodings (lone surrogates)
  are only lightly covered.
- **Stability across processes is sampled** (8 seeds), not exhaustive; absence
  of a difference for int-sets is strong evidence but not a proof.

Despite these limits, the suite gives a clear, reproducible answer to the
project question and pins the observed behaviour so regressions or
version/default changes would be caught.

---

### Appendix — Reproducing

```bash
python3 -m pytest -q                  # 654 tests
python3 findings/run_all_findings.py  # evidence dump (F1–F9)
python3 findings/f1_set_hashseed.py   # the headline non-determinism
python3 -m pycodestyle --max-line-length=79 src tests findings conftest.py
```
