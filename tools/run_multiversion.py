"""Run the pytest suite across multiple Python versions via conda.

For each version the script:
  1. Locates the conda environment named after the version (e.g. "3.10").
  2. Installs pytest and hypothesis into that environment if missing.
  3. Runs the full pytest suite and captures the result.
  4. Writes a per-version evidence file to the output directory.
  5. Prints a comparison table when all versions have been run.

Usage::

    python3 tools/run_multiversion.py
    python3 tools/run_multiversion.py --versions 3.9 3.10 3.11
    python3 tools/run_multiversion.py --output-dir results/multiversion
    python3 tools/run_multiversion.py --no-install  # skip dep install
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSIONS = ("3.8", "3.9", "3.10", "3.11", "3.12", "3.13")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def platform_slug() -> str:
    return {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(
        platform.system(), "unknown"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--versions",
        nargs="+",
        default=list(DEFAULT_VERSIONS),
        metavar="VER",
        help="Python versions to test (default: 3.8–3.13)",
    )
    parser.add_argument(
        "--output-dir",
        default=f"results/multiversion-{platform_slug()}",
        help="Parent directory for per-version evidence files",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Skip automatic pip install of pytest / hypothesis",
    )
    return parser.parse_args()


def conda_python(version: str) -> Path | None:
    """Return the Python executable for a conda env named *version*, or None."""
    conda_roots = [Path.home() / "miniconda3", Path.home() / "anaconda3"]
    bin_name = "python.exe" if os.name == "nt" else "bin/python"
    for root in conda_roots:
        exe = root / "envs" / version / bin_name
        if exe.exists():
            return exe
    return None


def run_cmd(command: list[str], cwd: Path = ROOT) -> tuple[int, str]:
    """Run *command* and return (returncode, combined stdout+stderr)."""
    result = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def ensure_deps(python: Path) -> bool:
    """Install pytest and hypothesis into *python*'s environment if absent."""
    # pytest is required
    code, _ = run_cmd([str(python), "-m", "pytest", "--version"])
    if code != 0:
        print("    [pip] installing pytest …")
        code, out = run_cmd(
            [str(python), "-m", "pip", "install", "pytest", "-q"]
        )
        if code != 0:
            print(f"    [pip] ERROR: {out.strip()}")
            return False

    # hypothesis is optional; test_fuzz.py falls back if absent
    code, _ = run_cmd(
        [str(python), "-c", "import hypothesis"]
    )
    if code != 0:
        print("    [pip] installing hypothesis …")
        run_cmd([str(python), "-m", "pip", "install", "hypothesis", "-q"])

    return True


def parse_pytest_counts(output: str) -> tuple[int, int]:
    """Extract (passed, failed) from pytest's summary line."""
    passed_match = re.search(r"(\d+) passed", output)
    failed_match = re.search(r"(\d+) failed", output)
    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0
    return passed, failed


# ---------------------------------------------------------------------------
# Per-version runner
# ---------------------------------------------------------------------------

def run_for_version(
    version: str,
    output_root: Path,
    install: bool,
) -> dict:
    python = conda_python(version)
    if python is None:
        print(f"[SKIP] Python {version} — conda env not found")
        return {"version": version, "status": "missing"}

    # Confirm the interpreter works and get its full version string
    code, ver_out = run_cmd(
        [str(python), "-c", "import sys; print(sys.version)"]
    )
    if code != 0:
        print(f"[SKIP] Python {version} — interpreter not executable")
        return {"version": version, "status": "missing"}

    full_version = ver_out.strip().splitlines()[0]
    print(f"[INFO] Python {version}  ({full_version})")
    print(f"       {python}")

    if install and not ensure_deps(python):
        return {"version": version, "status": "failed",
                "reason": "dependency install failed"}

    label = f"py{version.replace('.', '')}"
    out_dir = output_root / label
    out_dir.mkdir(parents=True, exist_ok=True)

    print("    [pytest] running …")
    code, pytest_out = run_cmd(
        [str(python), "-m", "pytest", "tests/", "-v", "--tb=short"],
    )

    (out_dir / "pytest_output.txt").write_text(pytest_out, encoding="utf-8")

    passed, failed = parse_pytest_counts(pytest_out)
    status = "passed" if code == 0 else "failed"
    marker = "✅" if status == "passed" else "❌"
    print(f"    [pytest] {marker} {status.upper()} — "
          f"passed={passed}  failed={failed}")

    summary = {
        "version": version,
        "full_version": full_version,
        "executable": str(python),
        "platform": platform.platform(),
        "status": status,
        "returncode": code,
        "passed": passed,
        "failed": failed,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    output_root = Path(args.output_dir)
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Platform : {platform.platform()}")
    print(f"Output   : {output_root}")
    print(f"Versions : {', '.join(args.versions)}")
    print()

    runs = []
    for version in args.versions:
        record = run_for_version(
            version, output_root, install=not args.no_install
        )
        runs.append(record)
        print()

    # Summary table
    print("=" * 54)
    print("MULTI-VERSION SUMMARY")
    print("=" * 54)
    print(f"{'Version':<10}{'Status':<12}{'Passed':<10}{'Failed':<8}")
    print("-" * 54)
    for r in runs:
        v = r["version"]
        s = r.get("status", "?")
        p = r.get("passed", "—")
        f = r.get("failed", "—")
        marker = "✅" if s == "passed" else ("⏭️ " if s == "missing" else "❌")
        print(f"{v:<10}{marker} {s:<10}{str(p):<10}{str(f):<8}")
    print("=" * 54)

    overall = {
        "platform": platform.platform(),
        "runs": runs,
    }
    (output_root / "summary.json").write_text(
        json.dumps(overall, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nAll results written to: {output_root}")

    failed = [r for r in runs if r.get("status") == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
