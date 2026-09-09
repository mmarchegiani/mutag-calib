#!/usr/bin/env python3

"""
Extract the per-WP scale factors and their correlations from a simultaneous
Loose/Medium/Tight fit, run from inside the fit directory.

Companion to extract_fit_results.py, which assumes the single-WP POI set. Here
the POIs are read back from pois.yaml rather than hard-coded, and the SF-to-SF
correlation matrix -- the whole reason for fitting the WPs together -- is
written out alongside the values.

Outputs, in the current directory:
    fitResults.csv          one row: values + errors, flat column names
    fitResults.json         same, plus the correlation matrix
    correlations.csv        the POI correlation matrix
"""

import glob
import json
import os

import pandas as pd
import ROOT
import yaml

ROOT.gROOT.SetBatch(True)


def main():
    with open("pois.yaml") as handle:
        poi_config = yaml.safe_load(handle)

    # Only the flavours that actually float in the fit; SF_light is frozen by
    # run_fit.sh, and a frozen parameter is not in floatParsFinal().
    pois = []
    for process_name in ("b", "c"):
        for name in poi_config["pois"].get(process_name, []):
            if name not in pois:
                pois.append(name)

    cut = os.path.basename(os.getcwd())
    category = os.path.basename(os.path.dirname(os.getcwd()))
    year = os.path.basename(os.path.dirname(os.path.dirname(os.getcwd())))

    # run_fit.sh passes --name .<category>, so match that file by name rather
    # than requiring the glob to return exactly one -- a leftover from a manual
    # combine run used to abort the extraction here.
    expected = f"fitDiagnostics.{category}.root"
    if os.path.isfile(expected):
        fit_path = expected
    else:
        candidates = sorted(g for g in glob.glob("fitDiagnostics.*.root")
                            if not g.endswith(".minos.root"))
        if len(candidates) == 1:
            fit_path = candidates[0]
            print(f"[WARN] {expected} not found, falling back to {fit_path}")
        elif not candidates:
            raise RuntimeError(f"No fitDiagnostics file in {os.getcwd()}")
        else:
            raise RuntimeError(
                f"{expected} not found and {len(candidates)} other fitDiagnostics "
                f"files present, cannot choose: {candidates}"
            )

    fit_file = ROOT.TFile.Open(fit_path)
    fit_s = fit_file.Get("fit_s")
    if not fit_s:
        raise RuntimeError("fit_s not found in ROOT file")
    final_pars = fit_s.floatParsFinal()

    row = {
        "year": year,
        "category": category,
        "cut": cut,
        "sf_definition": poi_config.get("sf_definition"),
    }
    found = []
    for poi in pois:
        par = final_pars.find(poi)
        if not par:
            print(f"[WARN] POI {poi} not found in the fit result (frozen?)")
            continue
        found.append(poi)
        row[poi] = par.getVal()
        row[f"{poi}_errUp"] = par.getErrorHi()
        row[f"{poi}_errDown"] = abs(par.getErrorLo())

    # Uncertainties come from the MINOS pass when available. The main fit runs
    # --robustHesse, right for the covariance but only symmetric; when SF_b and
    # SF_c are nearly degenerate, the profile likelihood is strongly asymmetric.
    # The MINOS pass provides the more accurate asymmetric uncertainties.
    # Only errUp/errDown come from here. Falls back to symmetric errors if the
    # MINOS pass is missing or did not converge.
    minos_path = f"fitDiagnostics.{category}.minos.root"
    if os.path.isfile(minos_path):
        minos_file = ROOT.TFile.Open(minos_path)
        minos_fit = minos_file.Get("fit_s") if minos_file and not minos_file.IsZombie() else None
        if minos_fit:
            minos_pars = minos_fit.floatParsFinal()
            n_used = 0
            for poi in found:
                par = minos_pars.find(poi)
                # A MINOS error that came back exactly symmetric means MINOS did
                # not actually run for that parameter; keep the robustHesse one
                # rather than silently relabelling a parabolic error as MINOS.
                if par and abs(par.getErrorHi() - abs(par.getErrorLo())) > 1e-9:
                    row[f"{poi}_errUp"] = par.getErrorHi()
                    row[f"{poi}_errDown"] = abs(par.getErrorLo())
                    n_used += 1
            row["minos_pois"] = n_used
            row["minos_status"] = int(minos_fit.status())
            print(f"[OK] MINOS errors used for {n_used}/{len(found)} POIs")
        if minos_file:
            minos_file.Close()
    else:
        row["minos_pois"] = 0

    # Correlation matrix over the POIs that actually floated. This is what the
    # simultaneous fit buys over three independent per-WP fits.
    correlations = {
        a: {b: float(fit_s.correlation(a, b)) for b in found} for a in found
    }
    for a in found:
        for b in found:
            if a != b:
                row[f"corr_{a}_{b}"] = correlations[a][b]

    pd.DataFrame([row]).to_csv("fitResults.csv", index=False)
    pd.DataFrame(correlations).loc[found, found].to_csv("correlations.csv")
    with open("fitResults.json", "w") as handle:
        json.dump({**row, "correlations": correlations}, handle, indent=2)

    print(f"[OK] {len(found)} POIs extracted: {', '.join(found)}")
    print("[OK] Results saved in fitResults.csv, correlations.csv, fitResults.json")


if __name__ == "__main__":
    main()
