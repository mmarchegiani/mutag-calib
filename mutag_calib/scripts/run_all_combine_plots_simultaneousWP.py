#!/usr/bin/env python3

"""
Pre/post-fit plots for the simultaneous Loose/Medium/Tight fits.

run_all_combine_plots.py cannot be reused: it filters against a hard-coded
ALLOWED_CATEGORIES set with no "-simultaneousWP" entries, and it builds channel
names by appending "_pass_"/"_fail_", assuming the two-region layout. The
simultaneous fit has four channels.

make_combine_plots.py itself is reused unchanged. It plots two channels per
call, so it runs twice per category with the slices paired, and the outputs are
renamed from pass/fail to the slice they actually show.

Usage:
    python mutag_calib/scripts/run_all_combine_plots_simultaneousWP.py \
        <datacards_simultaneousWP> -o <plots_dir>
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MAKE_PLOTS = SCRIPT_DIR / "make_combine_plots.py"
FIT_RE = re.compile(r"fitDiagnostics\.(.+)\.root")

SUFFIX = "-simultaneousWP"

# make_combine_plots.py takes one --passch and one --failch, and derives the era
# from the passch by splitting on "_pass_" -- so every pair must put a *-pass
# slice in the passch slot. These two pairs cover all four slices exactly once.
SLICE_PAIRS = [
    ("Loose-pass", "Loose-fail"),
    ("Tight-pass", "Medium-pass"),
]

# make_combine_plots.py writes fixed filenames; map them onto the slice shown.
OUTPUT_TEMPLATES = [
    ("prefit_pass_bcl_data_band", "prefit_{pass_slice}_bcl_data_band"),
    ("prefit_fail_bcl_data_band", "prefit_{fail_slice}_bcl_data_band"),
    ("postfit_sb_pass_bcl_data_band", "postfit_sb_{pass_slice}_bcl_data_band"),
    ("postfit_sb_fail_bcl_data_band", "postfit_sb_{fail_slice}_bcl_data_band"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_dir", help="datacards_simultaneousWP directory")
    parser.add_argument("-o", "--output-dir", dest="output_dir", required=True,
                        help="Output directory for plots")
    parser.add_argument("--postfit-group", default="shapes_fit_s",
                        choices=["shapes_fit_s", "shapes_fit_b"])
    args = parser.parse_args()

    # Must be absolute: make_combine_plots.py runs with cwd set to the tau21
    # directory, so a relative --outdir would land inside the datacards tree.
    output_dir = Path(args.output_dir).resolve()

    successful, failed = [], []

    # The MINOS pass writes fitDiagnostics.<category>.minos.root alongside the
    # main file, without --saveShapes, so plotting it would fail or half-succeed
    # and overwrite good plots with empty ones.
    fit_files = [f for f in sorted(Path(args.base_dir).glob("*/*/*/fitDiagnostics.*.root"))
                 if not f.name.endswith(".minos.root")]
    for fit_file in fit_files:
        tau_dir = fit_file.parent
        category = tau_dir.parent.name
        year = tau_dir.parent.parent.name
        if not category.endswith(SUFFIX):
            continue

        base = category[: -len(SUFFIX)].replace("-", "_")
        target = output_dir / year / category / tau_dir.name
        target.mkdir(parents=True, exist_ok=True)
        label = f"{year}/{category}/{tau_dir.name}"
        print(f"\n Processing {label}")

        for pass_slice, fail_slice in SLICE_PAIRS:
            command = [
                sys.executable, str(MAKE_PLOTS),
                "--file", fit_file.name,
                "--passch", f"{base}_{pass_slice.replace('-', '_')}_{year}",
                "--failch", f"{base}_{fail_slice.replace('-', '_')}_{year}",
                "--outdir", str(target),
                "--postfit-group", args.postfit_group,
            ]
            result = subprocess.run(command, cwd=tau_dir)
            if result.returncode != 0:
                print(f"[FAIL] {label}: {pass_slice}/{fail_slice}")
                failed.append((label, f"{pass_slice}/{fail_slice}"))
                continue

            # Rename pass/fail outputs to the slice they actually show, so the
            # second pair does not overwrite the first.
            for source, template in OUTPUT_TEMPLATES:
                destination = template.format(
                    pass_slice=pass_slice, fail_slice=fail_slice
                )
                for extension in ("pdf", "png"):
                    src = target / f"{source}.{extension}"
                    if src.exists():
                        src.replace(target / f"{destination}.{extension}")
            successful.append((label, f"{pass_slice}/{fail_slice}"))

    print(f"\n{len(successful)} plot sets written, {len(failed)} failed")
    for label, pair in failed:
        print(f"  [FAIL] {label}: {pair}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
