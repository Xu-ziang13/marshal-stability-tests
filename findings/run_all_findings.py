"""Human-readable evidence dump for every finding (F1-F9).

Run:  python3 findings/run_all_findings.py

Prints a labelled section per finding with the concrete bytes/digests that
back the claims in the report. This is documentation, not a test; the pytest
suite is the authoritative pass/fail check.
"""

import hashlib
import marshal
import platform
import struct
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/findings")
from f1_set_hashseed import digest_with_seed  # noqa: E402


def h(b):
    return hashlib.sha256(b).hexdigest()[:16]


def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    print(f"interpreter : {platform.python_implementation()} "
          f"{platform.python_version()} on {platform.system()}")
    print(f"marshal.version (default) : {marshal.version}")

    section("F1/F2  set ordering vs PYTHONHASHSEED")
    str_set = "{'apple','banana','cherry','date','egg','fig','grape'}"
    sds = {digest_with_seed(str_set, s) for s in range(6)}
    ids = {digest_with_seed("set(range(50))", s) for s in range(6)}
    print(f"  string-set distinct digests over 6 seeds: {len(sds)} "
          f"({'NON-DETERMINISTIC' if len(sds) > 1 else 'stable'})")
    print(f"  int-set    distinct digests over 6 seeds: {len(ids)} "
          f"({'stable' if len(ids) == 1 else 'non-deterministic'})")

    section("F3  dict insertion-order sensitivity")
    d1, d2 = {1: 0, 2: 0}, {2: 0, 1: 0}
    print(f"  {{1,2}} == {{2,1}} (logical): {d1 == d2}")
    print(f"  bytes equal: {marshal.dumps(d1) == marshal.dumps(d2)}")

    section("F4  signed zero")
    print(f"  dumps(+0.0): {marshal.dumps(0.0, 4).hex()}")
    print(f"  dumps(-0.0): {marshal.dumps(-0.0, 4).hex()}")

    section("F5  NaN / Inf bit patterns preserved")
    for label, val in [("nan", float("nan")), ("+inf", float("inf")),
                       ("-inf", float("-inf"))]:
        out = marshal.loads(marshal.dumps(val, 4))
        same = struct.pack("<d", out) == struct.pack("<d", val)
        print(f"  {label:5}: roundtrip bit-exact = {same}")
    snan = struct.unpack("<d", struct.pack("<Q", 0x7FF0000000000001))[0]
    out = marshal.loads(marshal.dumps(snan, 4))
    print(f"  signalling-nan payload preserved = "
          f"{struct.pack('<d', out).hex() == struct.pack('<d', snan).hex()}")

    section("F6  recursive list across versions")
    for v in (0, 2, 3, 4):
        lst = []
        lst.append(lst)
        try:
            n = len(marshal.dumps(lst, v))
            print(f"  version {v}: OK ({n} bytes)")
        except ValueError as exc:
            print(f"  version {v}: ValueError: {exc}")

    section("F7  shared reference compaction (v0 vs v4)")
    s = "a moderately long shared string value here" * 4
    print(f"  (s, s) v0 bytes: {len(marshal.dumps((s, s), 0))}")
    print(f"  (s, s) v4 bytes: {len(marshal.dumps((s, s), 4))}")

    section("F8  cross-version encodings of 0.1")
    streams = {v: h(marshal.dumps(0.1, v)) for v in range(5)}
    for v, d in streams.items():
        print(f"  version {v}: {d}")
    print(f"  distinct encodings: {len(set(streams.values()))}")

    section("F9  intra-process repeatability")
    obj = {"a": [1, 2, 3], "b": (4.0, "five"), "c": frozenset({1, 2})}
    digs = {h(marshal.dumps(obj, 4)) for _ in range(100)}
    print(f"  100 dumps of same object -> {len(digs)} distinct digest(s)")


if __name__ == "__main__":
    main()
