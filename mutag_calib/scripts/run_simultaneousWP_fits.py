#!/usr/bin/env python3

"""
Drive the full combine chain over a datacards_simultaneousWP tree.

run_combine_cards.py / run_fit_results.py filter against a hard-coded
ALLOWED_CATEGORIES set with no "-simultaneousWP" entries, so they would silently
skip everything here. This walks the tree instead and, per leaf, runs:

    combine_cards.sh     combineCards.py + text2workspace.py
    run_fit.sh           combine -M FitDiagnostics with the right POIs
    extract_fit_results_simultaneousWP.py

then concatenates every per-category fitResults.csv into one summary table.

Usage:
    # everything
    python mutag_calib/scripts/run_simultaneousWP_fits.py <datacards_simultaneousWP>

    # re-run a subset (repeatable; no '/' means substring match on the label)
    ... <dir> --only Pt-300to400 --only '2017/*/tau21_0p30'

    # resume: only the categories that have no fitResults.csv yet
    ... <dir> --missing-only

    # see what would run, without running it
    ... <dir> --only Pt-400to450 --list

The summary CSV is always rebuilt from every fitResults.csv in the tree, so a
partial re-run still produces a complete table.
"""

import argparse
import fnmatch
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXTRACT = SCRIPT_DIR / "extract_fit_results_simultaneousWP.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_dir", help="datacards_simultaneousWP directory")
    parser.add_argument("--skip-workspace", action="store_true",
                        help="Reuse an existing workspace.root instead of rebuilding it")
    parser.add_argument("--skip-fit", action="store_true",
                        help="Only re-run the result extraction")
    parser.add_argument("--only", action="append", metavar="PATTERN",
                        help="Re-run just the categories whose '<year>/<category>/<cut>' "
                             "label matches this shell glob. Repeatable; a leaf is run if "
                             "it matches any pattern. A pattern with no '/' is matched "
                             "against the whole label with implicit '*' on both sides, so "
                             "--only Pt-300to400 and --only '2017/*/tau21_0p30' both work.")
    parser.add_argument("--missing-only", action="store_true",
                        help="Re-run only the categories that have no fitResults.csv yet, "
                             "i.e. resume after a partial or failed run.")
    parser.add_argument("--list", action="store_true",
                        help="Print the selected categories and exit without running.")
    parser.add_argument("--csv-all-results", default="ALL_FIT_RESULTS_simultaneousWP.csv",
                        help="Summary CSV, written inside base_dir")
    args = parser.parse_args()

    all_leaves = sorted(Path(args.base_dir).glob("*/*/*/combine_cards.sh"))
    if not all_leaves:
        raise SystemExit(f"No combine_cards.sh found under {args.base_dir}")

    def selected(script):
        label = os.path.relpath(script.parent, args.base_dir)
        if args.missing_only and (script.parent / "fitResults.csv").is_file():
            return False
        if not args.only:
            return True
        return any(
            fnmatch.fnmatch(label, pattern if "/" in pattern else f"*{pattern}*")
            for pattern in args.only
        )

    leaves = [script for script in all_leaves if selected(script)]
    skipped = len(all_leaves) - len(leaves)
    if skipped:
        print(f"Selected {len(leaves)} of {len(all_leaves)} categories "
              f"({skipped} skipped by --only/--missing-only)")
    if args.list:
        for script in leaves:
            print("  " + os.path.relpath(script.parent, args.base_dir))
        return 0
    if not leaves:
        raise SystemExit("No categories selected; nothing to do.")

    failures = []
    for script in leaves:
        directory = script.parent
        label = os.path.relpath(directory, args.base_dir)
        print(f"\n=== {label} ===", flush=True)

        steps = []
        if not args.skip_workspace:
            steps.append(["bash", "combine_cards.sh"])
        if not args.skip_fit:
            steps.append(["bash", "run_fit.sh"])
        steps.append([sys.executable, str(EXTRACT)])

        for step in steps:
            result = subprocess.run(step, cwd=directory)
            if result.returncode != 0:
                print(f"[FAIL] {label}: {' '.join(step)} -> {result.returncode}", flush=True)
                failures.append((label, " ".join(step)))
                break

    print(f"\n{len(leaves) - len(failures)} / {len(leaves)} categories completed")
    for label, step in failures:
        print(f"  [FAIL] {label}: {step}")

    # POI column names differ between categories (--nonsignal-sf shared gives one
    # SF_c instead of three), so concat with sort=False and let missing columns
    # be NaN rather than assuming one fixed schema.
    results = sorted(Path(args.base_dir).glob("*/*/*/fitResults.csv"))
    if results:
        import pandas as pd

        summary = pd.concat([pd.read_csv(path) for path in results],
                            ignore_index=True, sort=False)
        # Path(base) / "abs/or/relative/path" silently produces base/base/... when the
        # caller passes a path that is already usable from the cwd, which is how a
        # 48-fit run ended by throwing away its own summary. Only join a bare name.
        given = Path(args.csv_all_results)
        summary_path = (given if given.is_absolute() or len(given.parts) > 1
                        else Path(args.base_dir) / given)
        summary.to_csv(summary_path, index=False)
        print(f"Summary of {len(summary)} fits written to {summary_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
