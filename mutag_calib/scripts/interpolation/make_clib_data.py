"""
Build a correctionlib (schema_version 2) JSON for the Xbb tagger scale factors

    binning on WP   (edges = measured WPs, piecewise-linear between them)
      -> binning on pt   (era-dependent bins, flow = clamp)
           -> category systematic: nom / up / down   (absolute SF values)
                -> formula "[0]+[1]*x"  with x = WP   (straight line between 2 WPs)

nom = SF_nominal, up = SF + sigma_tot, down = SF - sigma_tot, interpolated linearly in WP, as in the interpolation plots.

Usage:
    python3 make_xbb_sf_correctionlib.py
    python3 make_xbb_sf_correctionlib.py --years 2017 2018 "2022 preEE" # select years
    python3 make_xbb_sf_correctionlib.py -o corrections # ouput folder
"""

import argparse
import json
import os

import numpy as np

WPS = np.array([0.5, 0.6, 0.7, 0.8, 0.9, 0.99])

PT_BINS_RUN2 = [(250, 300), (300, 400), (400, 450), (450, None)]
PT_BINS_RUN3 = [(250, 300), (300, 350), (350, 425), (425, None)]

# SF by wp per pT bin
DATA = {
    "2016 PreVFP": dict(
        bins=PT_BINS_RUN2,
        sf=np.array([
            [1.005, 0.995, 0.994, 0.970, 0.945, 0.903],   # [250, 300]
            [0.971, 0.973, 0.968, 0.971, 0.968, 0.950],   # [300, 400]
            [0.988, 0.985, 0.985, 0.982, 0.968, 0.937],   # [400, 450]
            [0.995, 0.998, 0.999, 0.982, 0.970, 0.952],   # [450, inf]
        ]),
        sigma=np.array([
            [0.052, 0.071, 0.065, 0.070, 0.112, 0.150],
            [0.033, 0.036, 0.036, 0.041, 0.054, 0.058],
            [0.047, 0.043, 0.043, 0.049, 0.053, 0.080],
            [0.024, 0.027, 0.028, 0.031, 0.048, 0.083],
        ]),
    ),
    "2016 PostVFP": dict(
        bins=PT_BINS_RUN2,
        sf=np.array([
            [0.971, 0.961, 0.964, 0.983, 0.985, 0.976],
            [0.963, 0.957, 0.956, 0.960, 0.952, 0.954],
            [0.978, 0.977, 0.977, 0.971, 0.958, 0.954],
            [0.961, 0.966, 0.964, 0.961, 0.941, 0.900],
        ]),
        sigma=np.array([
            [0.046, 0.048, 0.039, 0.042, 0.063, 0.082],
            [0.037, 0.039, 0.045, 0.050, 0.057, 0.070],
            [0.028, 0.030, 0.035, 0.051, 0.046, 0.061],
            [0.042, 0.040, 0.043, 0.046, 0.062, 0.115],
        ]),
    ),
    "2017": dict(
        bins=PT_BINS_RUN2,
        sf=np.array([
            [1.044, 1.036, 1.030, 1.020, 0.994, 0.999],
            [0.975, 0.972, 0.970, 0.967, 0.962, 0.952],
            [1.007, 1.003, 1.004, 1.004, 1.006, 0.973],
            [1.005, 1.006, 1.010, 1.010, 1.006, 0.990],
        ]),
        sigma=np.array([
            [0.038, 0.040, 0.076, 0.096, 0.071, 0.093],
            [0.038, 0.040, 0.043, 0.044, 0.046, 0.056],
            [0.026, 0.029, 0.035, 0.037, 0.041, 0.045],
            [0.022, 0.023, 0.024, 0.029, 0.046, 0.081],
        ]),
    ),
    "2018": dict(
        bins=PT_BINS_RUN2,
        sf=np.array([
            [1.074, 1.070, 1.073, 1.077, 1.077, 1.076],
            [0.975, 0.976, 0.978, 0.974, 0.970, 0.957],
            [0.976, 0.976, 0.976, 0.973, 0.968, 0.944],
            [0.987, 0.992, 0.998, 0.994, 0.990, 0.966],
        ]),
        sigma=np.array([
            [0.064, 0.066, 0.074, 0.076, 0.083, 0.100],
            [0.044, 0.044, 0.053, 0.058, 0.060, 0.066],
            [0.029, 0.030, 0.034, 0.039, 0.052, 0.060],
            [0.022, 0.022, 0.021, 0.024, 0.033, 0.050],
        ]),
    ),
    "2022 preEE": dict(
        bins=PT_BINS_RUN3,
        sf=np.array([
            [0.964, 0.961, 0.959, 0.960, 0.947, 0.948],   # [250, 300]
            [1.013, 1.014, 1.009, 1.004, 0.995, 0.985],   # [300, 350]
            [1.005, 1.005, 1.006, 1.005, 0.993, 0.972],   # [350, 425]
            [1.012, 1.018, 1.022, 1.014, 1.008, 0.981],   # [425, inf]
        ]),
        sigma=np.array([
            [0.039, 0.043, 0.049, 0.056, 0.062, 0.062],
            [0.030, 0.025, 0.025, 0.027, 0.032, 0.043],
            [0.031, 0.034, 0.037, 0.042, 0.047, 0.059],
            [0.021, 0.023, 0.024, 0.029, 0.044, 0.076],
        ]),
    ),
    "2022 postEE": dict(
        bins=PT_BINS_RUN3,
        sf=np.array([
            [1.013, 1.018, 1.015, 1.012, 1.011, 1.012],
            [1.011, 1.011, 1.018, 1.017, 1.017, 1.017],
            [1.031, 1.038, 1.044, 1.048, 1.050, 1.053],
            [1.030, 1.042, 1.052, 1.058, 1.049, 1.060],
        ]),
        sigma=np.array([
            [0.031, 0.031, 0.032, 0.034, 0.045, 0.070],
            [0.043, 0.043, 0.047, 0.053, 0.062, 0.062],
            [0.036, 0.040, 0.045, 0.051, 0.069, 0.077],
            [0.043, 0.048, 0.054, 0.063, 0.068, 0.093],
        ]),
    ),
    "2023 preBPix": dict(
        bins=PT_BINS_RUN3,
        sf=np.array([
            [0.977, 0.976, 0.972, 0.969, 0.961, 0.963],
            [0.967, 0.968, 0.974, 0.963, 0.962, 0.969],
            [0.977, 0.977, 0.974, 0.972, 0.969, 0.976],
            [0.982, 0.986, 0.988, 0.985, 0.982, 0.988],
        ]),
        sigma=np.array([
            [0.028, 0.026, 0.029, 0.036, 0.048, 0.059],
            [0.061, 0.053, 0.029, 0.032, 0.041, 0.046],
            [0.034, 0.024, 0.023, 0.029, 0.033, 0.046],
            [0.023, 0.019, 0.020, 0.022, 0.034, 0.081],
        ]),
    ),
    "2023 postBPix": dict(
        bins=PT_BINS_RUN3,
        sf=np.array([
            [0.997, 0.993, 0.987, 0.982, 0.978, 0.956],
            [0.989, 0.991, 0.988, 0.979, 0.978, 0.970],
            [0.975, 0.975, 0.968, 0.955, 0.950, 0.924],
            [0.990, 0.990, 0.991, 0.982, 0.974, 0.947],
        ]),
        sigma=np.array([
            [0.045, 0.042, 0.047, 0.044, 0.047, 0.066],
            [0.031, 0.031, 0.033, 0.040, 0.056, 0.059],
            [0.061, 0.058, 0.060, 0.058, 0.062, 0.099],
            [0.036, 0.035, 0.031, 0.034, 0.045, 0.084],
        ]),
    ),
    "2024": dict(
        bins=PT_BINS_RUN3,
        sf=np.array([
            [0.985, 0.992, 1.005, 1.000, 0.991, 0.985],   # [250, 300]
            [0.995, 0.995, 1.011, 1.001, 0.976, 0.982],   # [300, 350]
            [0.985, 0.993, 1.019, 1.020, 1.004, 1.014],   # [350, 425]
            [0.992, 1.000, 1.029, 1.029, 1.003, 1.001],   # [425, inf]
        ]),
        sigma=np.array([
            [0.041, 0.025, 0.028, 0.038, 0.047, 0.042],
            [0.020, 0.016, 0.021, 0.028, 0.057, 0.050],
            [0.022, 0.021, 0.031, 0.040, 0.051, 0.063],
            [0.025, 0.024, 0.052, 0.057, 0.041, 0.045],
        ]),
    ),
    "2025": dict(
        bins=PT_BINS_RUN3,
        sf=np.array([
            [1.021, 1.021, 1.011, 1.001, 0.996, 0.977],
            [1.021, 1.017, 1.010, 0.991, 0.972, 0.944],
            [1.006, 1.005, 1.000, 0.994, 0.978, 0.958],
            [1.004, 1.014, 1.017, 1.012, 0.996, 0.967],
        ]),
        sigma=np.array([
            [0.063, 0.050, 0.043, 0.046, 0.046, 0.052],
            [0.043, 0.042, 0.044, 0.054, 0.070, 0.074],
            [0.044, 0.040, 0.047, 0.056, 0.063, 0.089],
            [0.049, 0.047, 0.045, 0.051, 0.061, 0.084],
        ]),
    ),
}

TAGGER = "GloParT-3 Xbb (XbbVsQCD)"
PT_MAX = 13000.0      # upper edge for the open-ended last pT bin
WP_EPS = 1e-6         # makes the last measured WP fall inside the last WP bin
SYSTS = ("nom", "up", "down")

def line(w0, w1, y0, y1):
    """Parameters [intercept, slope] of the straight line through (w0, y0) and (w1, y1)."""
    slope = (y1 - y0) / (w1 - w0)
    return [float(y0 - slope * w0), float(slope)]

def formula(params):
    return {
        "nodetype": "formula",
        "expression": "[0]+[1]*x",
        "parser": "TFormula",
        "variables": ["WP"],
        "parameters": params,
    }

def build_correction(year, d):
    sf, sig = d["sf"], d["sigma"]
    bins = d["bins"]
    pt_edges = [float(b[0]) for b in bins] + [PT_MAX]
    # up / down / nominal curves per pT bin
    curves = {
        "nom": sf,
        "up": sf + sig,
        "down": sf - sig,
    }
    if np.isnan(sf).any():
        raise ValueError(f"{year}: nan SF points are not supported in the JSON; "
                         "fill or drop them first")

    wp_edges = [float(w) for w in WPS[:-1]] + [float(WPS[-1]) + WP_EPS]

    wp_content = []
    for iw in range(len(WPS) - 1):                       # interval [WPS[iw], WPS[iw+1]]
        pt_content = []
        for ib in range(len(bins)):
            cat = []
            for s in SYSTS:
                y = curves[s][ib]
                cat.append({
                    "key": s,
                    "value": formula(line(WPS[iw], WPS[iw + 1], y[iw], y[iw + 1])),
                })
            pt_content.append({"nodetype": "category", "input": "systematic", "content": cat})
        wp_content.append({
            "nodetype": "binning",
            "input": "pt",
            "edges": pt_edges,
            "content": pt_content,
            "flow": "clamp",
        })

    return {
        "name": "Xbb_SF",
        "version": 1,
        "description": (
            f"{TAGGER} tagging SF, {year}. Cumulative: SF of score > WP. "
            f"Piecewise linear in WP between the measured points "
            f"{', '.join(str(w) for w in WPS)}; a WP outside [{WPS[0]}, {WPS[-1]}] is an error. "
            f"pt clamped to the bins [{', '.join(str(int(e)) for e in pt_edges[:-1])}, inf). "
            "systematic: nom/up/down, absolute SF values (up/down = SF +/- sigma_tot, "
            "interpolated linearly in WP). Parameters stored as slope+intercept"
        ),
        "inputs": [
            {"name": "WP", "type": "real", "description": "Working point on the score (score > WP)"},
            {"name": "pt", "type": "real", "description": "Fat jet pt (nominal JEC/JER), GeV"},
            {"name": "systematic", "type": "string", "description": "nom, up or down"},
        ],
        "output": {"name": "sf", "type": "real"},
        "data": {
            "nodetype": "binning",
            "input": "WP",
            "edges": wp_edges,
            "content": wp_content,
            "flow": "error",   # WP outside [first, last measured WP] is an error
        },
    }

def build_file(year, d):
    return {
        "schema_version": 2,
        "description": f"{TAGGER} tagging scale factors, {year}",
        "corrections": [build_correction(year, d)],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", default=["all"],
                    help=f"eras to write, or 'all'. Available: {list(DATA)}")
    ap.add_argument("-o", "--outdir", default=".")
    args = ap.parse_args()

    years = list(DATA) if args.years == ["all"] else args.years
    os.makedirs(args.outdir, exist_ok=True)
    for y in years:
        out = os.path.join(args.outdir, f"Xbb_SF_{y.replace(' ', '_')}.json")
        with open(out, "w") as f:
            json.dump(build_file(y, DATA[y]), f, indent=2)
        print(f"[ok] {y} -> {out}")

if __name__ == "__main__":
    main()
