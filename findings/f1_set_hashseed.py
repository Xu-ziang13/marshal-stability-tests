"""Reproduce F1/F2: hash-seed-dependent marshalling of sets.

Run directly:  python3 findings/f1_set_hashseed.py

It marshals a set of strings and a set of ints in several fresh interpreters
with different PYTHONHASHSEED values and prints the resulting digests. The
string-set digests differ (non-deterministic); the int-set digests match.
"""

import os
import subprocess
import sys

_CHILD = (
    "import marshal, hashlib, sys\n"
    "obj = eval(sys.argv[1])\n"
    "sys.stdout.write(hashlib.sha256(marshal.dumps(obj, 4)).hexdigest())\n"
)


def digest_with_seed(expr, seed):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    out = subprocess.check_output(
        [sys.executable, "-c", _CHILD, expr], env=env)
    return out.decode().strip()[:16]


def main():
    str_set = "{'apple','banana','cherry','date','egg','fig','grape'}"
    int_set = "set(range(50))"
    seeds = [0, 1, 2, 3, 4, 5]

    print("PYTHONHASHSEED  string-set digest   int-set digest")
    print("-" * 52)
    str_digests, int_digests = set(), set()
    for s in seeds:
        sd = digest_with_seed(str_set, s)
        idg = digest_with_seed(int_set, s)
        str_digests.add(sd)
        int_digests.add(idg)
        print(f"{s:<14}  {sd}   {idg}")

    print("-" * 52)
    print(f"distinct string-set digests: {len(str_digests)} "
          f"-> {'NON-DETERMINISTIC' if len(str_digests) > 1 else 'stable'}")
    print(f"distinct int-set digests:    {len(int_digests)} "
          f"-> {'non-deterministic' if len(int_digests) > 1 else 'STABLE'}")


if __name__ == "__main__":
    main()
