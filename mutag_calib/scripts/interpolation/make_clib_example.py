"""
Build a correctionlib (schema_version 2) JSON for the Xbb tagger scale factors

    binning on WP   (edges = measured WPs, piecewise-linear between them)
      -> binning on pt   (era-dependent bins, flow = clamp)
           -> category systematic: nom / up / down   (absolute SF values)
                -> formula "[0]+[1]*x"  with x = WP   (straight line between 2 WPs)

nom = SF_nominal, up = SF + sigma_tot, down = SF - sigma_tot, interpolated linearly in WP, as in the interpolation plots.
"""

import argparse
import json
import os

import numpy as np

WPS = np.array([0.5, 0.6, 0.7, 0.8, 0.9])

PT_BINS = [(300, 350), (350, 425), (425, None)]

# SF by wp per pT bin
DATA = {
    "2020": dict(
        bins=PT_BINS,
        sf=np.array([
            [0.999, 0.997, 0.995, 0.993, 0.991],   # [300, 400]
            [0.989, 0.987, 0.985, 0.983, 0.981],   # [400, 450]
            [0.979, 0.977, 0.975, 0.973, 0.971],   # [450, inf]
        ]),
        sigma=np.array([
            [0.033, 0.036, 0.039, 0.042, 0.045],   # [300, 400]
            [0.041, 0.044, 0.047, 0.050, 0.053],   # [400, 450]
            [0.023, 0.026, 0.029, 0.032, 0.035],   # [450, inf]
        ]),
    )
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
            "interpolated linearly in WP). Parameters stored as slope + intercept"
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
    ap.add_argument("-o", "--outdir", default=".")
    args = ap.parse_args()

    years = list(DATA)
    os.makedirs(args.outdir, exist_ok=True)
    for y in years:
        out = os.path.join(args.outdir, f"Xbb_SF_{y.replace(' ', '_')}.json")
        with open(out, "w") as f:
            json.dump(build_file(y, DATA[y]), f, indent=2)
        print(f"[ok] {y} -> {out}")

if __name__ == "__main__":
    main()
