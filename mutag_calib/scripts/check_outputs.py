#!/usr/bin/env python3

"""
Check a PocketCoffea output directory for missing / truncated / corrupt
per-dataset .coffea outputs, and print the --filter-datasets option needed
to re-run whatever is bad.

Runs are regularly lost part-way through (dropped ssh session, dask worker
that can't reach the scheduler, ...), which leaves the output directory with
a partial set of output_<dataset>.coffea files -- and, if the run died mid-
write, possibly a truncated one. This compares, for every dataset in the
run's own config.json:

    cutflow['initial'][dataset]   vs   filesets[dataset].metadata.nevents

Usage:
    python3 mutag_calib/scripts/check_outputs.py <OUTPUT_DIR>
    python3 mutag_calib/scripts/check_outputs.py <OUTPUT_DIR> --cfg <config.py>
    python3 mutag_calib/scripts/check_outputs.py <OUTPUT_DIR> --exclude DS1,DS2
    python3 mutag_calib/scripts/check_outputs.py <OUTPUT_DIR> --quiet   # list only
"""

import os
import json
import argparse

from coffea.util import load


# Datasets whose processed event count is legitimately below metadata.nevents,
# i.e. a mismatch here is expected and does NOT mean the output is truncated.
# Excluded from the re-run list by default; use --include-known to override.
KNOWN_INCOMPLETE = {
    # One file (.../100000/b0898d8f-c29b-4d85-86fd-d66b2105f16c.root) was
    # unreadable (_lzma.LZMAError: Corrupt input data) and was dropped from
    # datasets/MC_QCD_MuEnriched_run2.json, leaving 97 of 98 files.
    # metadata.nevents still reports the full 98-file DAS total, so this
    # dataset always comes up ~719,743 events (~1%) short.
    "QCD_Pt-170To300_MuEnrichedPt5_Pt-170to300_2017":
        "97/98 files - corrupt file dropped, metadata.nevents not updated",
}


def main():
    ap = argparse.ArgumentParser(
        description="Check PocketCoffea outputs and emit --filter-datasets for the bad ones"
    )
    ap.add_argument("output_dir", help="PocketCoffea output directory (must contain config.json)")
    ap.add_argument("--cfg", default=None,
                    help="Path to the .py config; if given, prints the full pocket-coffea run command")
    ap.add_argument("-ro", "--run-options", default="mutag_calib/configs/params/run_options.yaml",
                    help="Run options yaml, only used when building the full command with --cfg")
    ap.add_argument("--exclude", default="",
                    help="Comma-separated datasets to leave out of the re-run list")
    ap.add_argument("--include-known", action="store_true",
                    help="Also re-run the KNOWN_INCOMPLETE datasets (excluded by default)")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="Print only the comma-separated dataset list (for scripting)")
    args = ap.parse_args()

    outdir = args.output_dir.rstrip("/")
    cfg_path = os.path.join(outdir, "config.json")
    if not os.path.isfile(cfg_path):
        raise SystemExit(f"No config.json in {outdir} -- is that a PocketCoffea output directory?")

    filesets = json.load(open(cfg_path))["datasets"]["filesets"]
    excluded = {d for d in args.exclude.split(",") if d}

    ok, missing, incomplete, corrupt = [], [], [], []

    for ds in sorted(filesets):
        expected = int(filesets[ds]["metadata"]["nevents"])
        path = os.path.join(outdir, f"output_{ds}.coffea")

        if not os.path.exists(path):
            missing.append((ds, expected))
            continue
        try:
            initial = load(path)["cutflow"]["initial"][ds]
        except Exception as e:
            corrupt.append((ds, f"{type(e).__name__}: {str(e)[:60]}"))
            continue

        if initial == expected:
            ok.append(ds)
        else:
            incomplete.append((ds, initial, expected))

    # Build the re-run list
    rerun = [ds for ds, _ in missing]
    rerun += [ds for ds, _ in corrupt]
    for ds, _, _ in incomplete:
        if ds in KNOWN_INCOMPLETE and not args.include_known:
            continue
        rerun.append(ds)
    rerun = sorted(set(rerun) - excluded)

    if not args.quiet:
        print(f"\n{outdir}  ({len(filesets)} datasets in config.json)\n")
        print(f"  OK         : {len(ok)}")
        print(f"  MISSING    : {len(missing)}")
        print(f"  INCOMPLETE : {len(incomplete)}")
        print(f"  CORRUPT    : {len(corrupt)}")

        if missing:
            print("\nMISSING (never produced):")
            for ds, exp in missing:
                print(f"  {ds}   (expected {exp:,} events)")

        if corrupt:
            print("\nCORRUPT (failed to load -- likely truncated mid-write):")
            for ds, err in corrupt:
                print(f"  {ds}\n      {err}")

        if incomplete:
            print("\nINCOMPLETE (processed fewer events than metadata.nevents):")
            for ds, init, exp in incomplete:
                d = init - exp
                note = ""
                if ds in KNOWN_INCOMPLETE:
                    note = f"   [EXPECTED: {KNOWN_INCOMPLETE[ds]}]"
                print(f"  {ds}\n      {init:,} / {exp:,}  ({d:+,}, {100.0*d/exp:+.2f}%){note}")

        if excluded:
            print(f"\nExcluded by --exclude: {', '.join(sorted(excluded))}")

        print()
        if not rerun:
            print("Nothing to re-run -- all outputs complete.\n")
            return
        print(f"{len(rerun)} dataset(s) need re-running:\n")

    ds_list = ",".join(rerun)
    if not rerun:
        return

    if args.cfg and not args.quiet:
        print(
            f"pocket-coffea run --cfg {args.cfg} \\\n"
            f"  -o {outdir} \\\n"
            f"  -e dask@lxplus \\\n"
            f"  -ro {args.run_options} \\\n"
            f"  --process-separately \\\n"
            f"  --filter-datasets {ds_list}\n"
        )
    else:
        print(f"--filter-datasets {ds_list}" if not args.quiet else ds_list)


if __name__ == "__main__":
    main()
