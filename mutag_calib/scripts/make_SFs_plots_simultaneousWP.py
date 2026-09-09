#!/usr/bin/env python3

"""Final scale factors with their full uncertainty budget, from a simultaneous fit.

The simultaneous-WP counterpart of make_SFs_plots_glopart.py. Same uncertainty
model, three differences that follow from the fit itself:

  * One leaf carries all three working points.
  * Categories are discovered by walking the tree.
  * The fit errors are MINOS intervals and asymmetric.

Uncertainty budget, per (year, pT bin, working point):

    err_fit          combine fit error (stat + every nuisance), asymmetric, at
                     the nominal tau21 cut
    err_tau21        max |SF(t) - SF(0.30)| over t in {0.20, 0.25, 0.35, 0.40}
    err_reweight     |SF(0.30, MC reweighted to data) - SF(0.30)|
    total            the three in quadrature, separately per side

Outputs, per year:
    SF<f>_vs_pt_<year>.{png,pdf}       SF vs pT bin, one series per WP,
                                       inner bar = fit only, outer = total
    SF<f>_vs_tau21_<year>.{png,pdf}    stability against the tau21 cut
    SF<f>_uncertainties_<year>.json    the machine-readable budget
and once for the whole tree:
    SF<f>_table.tex                    LaTeX summary table

Usage:
    python mutag_calib/scripts/make_SFs_plots_simultaneousWP.py \
        <datacards_simultaneousWP> -o <out_dir> [--SF-type b|c]
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_SFs_simultaneousWP import (  # noqa: E402
    WP_TIERS, WP_COLOR, WP_MARKER, INK, INK_SOFT, SURFACE,
    style, order_pt_bins, panel_tag, year_label, cms_frame, stack_below_axes,
)

# Integrated luminosity per era, fb^-1, taken from pocket_coffea's lumi.picobarns
# (the same table the templates were normalised with). Each figure covers one
# era, so it must carry that era's lumi -- a Run-2 sum would overstate it.
LUMI_FB = {
    "2016_PreVFP": 19.65,
    "2016_PostVFP": 16.98,
    "2017": 41.48,
    "2018": 59.83,
}


def era_text(year, override=None):
    """Upper-right CMS label for a single-era figure."""
    if override:
        return override
    lumi = LUMI_FB.get(str(year))
    if lumi is None:
        print(f"[WARN] no luminosity known for era {year!r}; "
              "labelling the figure without one")
        return year_label(year)
    return rf"{year_label(year)}, {lumi:.1f} fb$^{{-1}}$"


TAU21_VALUES = [0.20, 0.25, 0.30, 0.35, 0.40]
TAU21_CENTRAL = 0.30
REWEIGHT_KEY = "0.30_reweight"

# Each SF scales one exclusive score slice, not a cumulative working point, so
# the table labels the slice (B/C/D, matching the datacards) rather than the WP
# whose name the POI carries. Slice A carries no SF: it absorbs the migration.
SLICE_OF_WP = {"Loose": "B", "Medium": "C", "Tight": "D"}
SLICE_DEF = {
    "B": r"$\mathrm{L} \leq s < \mathrm{M}$",
    "C": r"$\mathrm{M} \leq s < \mathrm{T}$",
    "D": r"$s \geq \mathrm{T}$",
}
SLICE_ORDER = ["B", "C", "D"]
SUFFIX = "-simultaneousWP"


def cut_dirname(t):
    return f"tau21_{t:.2f}".replace(".", "p")


def pt_of(category):
    m = re.search(r"_Pt-([^_]+)_", category)
    return m.group(1) if m else category


def pt_label(pt):
    m = re.match(r"(\d+)to(\d+|Inf)$", pt)
    if not m:
        return pt
    lo, hi = m.groups()
    return f"{lo}-inf" if hi == "Inf" else f"{lo}-{hi}"


def collect(base_dir, flavour):
    """{year: {pt: {wp: {tau21_key: (val, errUp, errDown)}}}}"""
    data = {}
    base = Path(base_dir)
    for year_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        for cat_dir in sorted(year_dir.iterdir()):
            if not cat_dir.is_dir() or not cat_dir.name.endswith(SUFFIX):
                continue
            pt = pt_of(cat_dir.name)
            keys = [(t, cut_dirname(t)) for t in TAU21_VALUES]
            keys.append((REWEIGHT_KEY, "tau21_0p30_reweight"))
            for key, dirname in keys:
                path = cat_dir / dirname / "fitResults.json"
                if not path.is_file():
                    continue
                with open(path) as handle:
                    row = json.load(handle)
                for wp in WP_TIERS:
                    name = f"SF_{flavour}_{wp}"
                    if name not in row:
                        continue
                    (data.setdefault(year_dir.name, {})
                         .setdefault(pt, {})
                         .setdefault(wp, {})[key]) = (
                        float(row[name]),
                        float(row[f"{name}_errUp"]),
                        float(row[f"{name}_errDown"]),
                    )
    return data


def budget(series):
    """Full uncertainty budget for one (year, pt, wp), or None if incomplete."""
    if TAU21_CENTRAL not in series:
        return None
    value, err_up, err_dn = series[TAU21_CENTRAL]

    # tau21: spread of the central value across the cut scan. Deliberately the
    # max deviation rather than an RMS, matching make_SFs_plots_glopart.py, so
    # the two methods' budgets stay directly comparable.
    variations = [abs(series[t][0] - value) for t in TAU21_VALUES
                  if t != TAU21_CENTRAL and t in series]
    err_tau21 = max(variations) if variations else 0.0

    err_reweight = (abs(series[REWEIGHT_KEY][0] - value)
                    if REWEIGHT_KEY in series else 0.0)

    # The two systematics are one-sided shifts with no preferred direction, so
    # they enter both sides; only the fit error is genuinely asymmetric.
    extra = err_tau21 ** 2 + err_reweight ** 2
    return dict(value=value, err_fit_up=err_up, err_fit_dn=err_dn,
                err_tau21=err_tau21, err_reweight=err_reweight,
                n_tau21=len(variations),
                total_up=math.sqrt(err_up ** 2 + extra),
                total_dn=math.sqrt(err_dn ** 2 + extra))


def figure_vs_pt(year, per_pt, pts, flavour, out_stem, era, formats):
    fig, ax = plt.subplots(figsize=(9.0, 6.6))
    xs = {p: i for i, p in enumerate(pts)}
    any_point = False
    for k, wp in enumerate(WP_TIERS):
        off = (k - 1) * 0.20
        X, Y, FU, FD, TU, TD = [], [], [], [], [], []
        for p in pts:
            b = per_pt.get(p, {}).get(wp)
            if not b:
                continue
            X.append(xs[p] + off); Y.append(b["value"])
            FU.append(b["err_fit_up"]); FD.append(b["err_fit_dn"])
            TU.append(b["total_up"]);   TD.append(b["total_dn"])
        if not X:
            continue
        any_point = True
        X = np.array(X, float)
        # outer bar: total. inner bar: fit only. Same colour, different weight,
        # so the systematic contribution is the visible difference.
        ax.errorbar(X, Y, yerr=[TD, TU], fmt="none", ecolor=WP_COLOR[wp],
                    elinewidth=1.6, capsize=4, capthick=1.6, alpha=0.55, zorder=3,
                    label=r"total (fit $\oplus$ $\tau_{21}$ $\oplus$ reweight)"
                    if k == 0 else None)
        ax.errorbar(X, Y, yerr=[FD, FU], fmt="none", ecolor=WP_COLOR[wp],
                    elinewidth=4.0, capsize=0, zorder=4,
                    label="fit only" if k == 0 else None)
        ax.plot(X, Y, linestyle="none", marker=WP_MARKER[wp], markersize=8,
                color=WP_COLOR[wp], zorder=5, label=wp)
    if not any_point:
        plt.close(fig)
        return False

    ax.axhline(1.0, color=INK_SOFT, lw=1.1, ls="--", zorder=1)
    ax.set_xticks(range(len(pts)))
    ax.set_xticklabels([p.replace("to", "–").replace("Inf", "∞") for p in pts])
    ax.set_xlim(-0.6, len(pts) - 0.4)
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_ylabel(f"SF, {flavour} jets")
    ax.set_xlabel(r"FatJet $p_{T}$ [GeV]")
    panel_tag(ax, year_label(year))
    cms_frame(fig, [ax], era)
    handles, labels = ax.get_legend_handles_labels()
    order = ([labels.index(w) for w in WP_TIERS if w in labels]
             + [i for i, l in enumerate(labels) if l not in WP_TIERS])
    ax.legend([handles[i] for i in order], [labels[i] for i in order],
              loc="best", frameon=False, fontsize=12, ncol=2)
    fig.tight_layout()
    for ext in formats:
        fig.savefig(f"{out_stem}.{ext}", dpi=200)
    plt.close(fig)
    return True


def figure_vs_tau21(year, per_pt, pts, flavour, out_stem, era, formats):
    fig, axes = plt.subplots(1, len(pts), figsize=(4.2 * len(pts), 5.2),
                             squeeze=False, sharey=True)
    axes = axes[0]
    for col, p in enumerate(pts):
        ax = axes[col]
        for wp in WP_TIERS:
            series = per_pt.get(p, {}).get(wp, {})
            ts = sorted(t for t in series if isinstance(t, float))
            if not ts:
                continue
            y = [series[t][0] for t in ts]
            eu = [series[t][1] for t in ts]
            ed = [series[t][2] for t in ts]
            ax.errorbar(ts, y, yerr=[ed, eu], marker=WP_MARKER[wp], markersize=7,
                        lw=1.8, capsize=3, color=WP_COLOR[wp], zorder=3,
                        label=wp if col == 0 else None)
            if REWEIGHT_KEY in series:
                ax.plot([TAU21_CENTRAL], [series[REWEIGHT_KEY][0]], linestyle="none",
                        marker=WP_MARKER[wp], markersize=9, markerfacecolor="none",
                        markeredgecolor=WP_COLOR[wp], markeredgewidth=1.8, zorder=4,
                        label=("MC reweighted" if (col == 0 and wp == "Loose") else None))
        ax.axhline(1.0, color=INK_SOFT, lw=1.1, ls="--", zorder=1)
        ax.axvline(TAU21_CENTRAL, color=INK_SOFT, lw=1.0, ls=":", zorder=1)
        ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        panel_tag(ax, f"{p.replace('to', '–').replace('Inf', '∞')} GeV", fontsize=13)
        if col == 0:
            ax.set_ylabel(f"SF, {flavour} jets")
    cms_frame(fig, axes, era)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.94),
               ncol=len(labels), frameon=False, fontsize=12)
    fig.suptitle(f"{year_label(year)} — stability against the "
                 r"$\tau_{21}$ cut", fontsize=15, y=1.005)
    fig.tight_layout(rect=[0, 0.03, 1, 0.90])
    stack_below_axes(fig, axes, label=r"$\tau_{21}$ cut",
                     note="Error bars are the fit uncertainty only. Hollow marker: "
                          "MC-reweighted-to-data variant at the nominal cut.")
    for ext in formats:
        fig.savefig(f"{out_stem}.{ext}", dpi=200)
    plt.close(fig)


def latex_table(rows, path, flavour, pt_order):
    """Ordered by score slice first, then pT, within each era."""
    rank_pt = {p: i for i, p in enumerate(pt_order)}
    rows = sorted(rows, key=lambda r: (r["year"],
                                       SLICE_ORDER.index(SLICE_OF_WP[r["wp"]]),
                                       rank_pt.get(r["pt"], len(rank_pt))))
    with open(path, "w") as f:
        f.write("\\begin{table}[htbp]\n\\centering\n\\small\n")
        f.write("\\begin{tabular}{|c|c|c|c|c|c|c|}\n\\hline\n")
        f.write("era & slice & $p_\\mathrm{T}$ [GeV] & $\\mathrm{SF}$ & "
                "$\\mathrm{err_{fit}}$ & $\\tau_{21}^\\mathrm{cut}$ / "
                "$\\tau_{21}^\\mathrm{rw}$ & $\\sigma_\\mathrm{tot}$ \\\\\n\\hline\n")
        last = None
        for r in rows:
            sl = SLICE_OF_WP[r["wp"]]
            key = (r["year"], sl)
            if key != last:
                if last is not None:      # the header already ends with \hline
                    f.write("\\hline\n")
                last = key
            lo_hi = pt_label(r["pt"]).replace("-inf", ", $\\infty$").replace("-", ", ")
            f.write(f"{r['year'].replace('_', ' ')} & {sl} & [{lo_hi}] & "
                    f"{r['value']:.3f} & "
                    f"$^{{+{r['err_fit_up']:.3f}}}_{{-{r['err_fit_dn']:.3f}}}$ & "
                    f"{r['err_tau21']:.3f} / {r['err_reweight']:.3f} & "
                    f"$^{{+{r['total_up']:.3f}}}_{{-{r['total_dn']:.3f}}}$ \\\\\n")
        f.write("\\hline\n\\end{tabular}\n")
        slice_lines = ", ".join(f"{k}: {SLICE_DEF[k]}" for k in SLICE_ORDER)
        f.write(f"""\\caption{{Scale factors $\\mathrm{{SF}}_\\mathrm{{{flavour}}}$ for the GloParT
XbbVsQCDTopW tagger, from the simultaneous fit of the three working points.
Each scale factor is applied to one \\emph{{exclusive}} slice of the tagger score $s$,
delimited by the Loose (L), Medium (M) and Tight (T) working-point thresholds:
{slice_lines}. The complementary slice $s < \\mathrm{{L}}$ carries no free scale factor;
it absorbs the migration required to conserve the total yield of each flavour.
$\\mathrm{{err_{{fit}}}}$ is the MINOS profile-likelihood interval from combine and covers
statistics and every nuisance in the datacard (pileup, luminosity, ISR, FSR, JER, JES,
light- and c-jet systematics, Madgraph/Pythia QCD); it is asymmetric where $\\mathrm{{SF}}_b$
and $\\mathrm{{SF}}_c$ are nearly degenerate. $\\tau_{{21}}^\\mathrm{{cut}}$ is the largest
deviation of the central value between the nominal $\\tau_{{21}} < 0.30$ selection and the
variations at 0.20, 0.25, 0.35 and 0.40. $\\tau_{{21}}^\\mathrm{{rw}}$ is the shift when the MC
is reweighted to data at the nominal cut. The two systematics are one-sided shifts and are
applied to both sides; $\\sigma_\\mathrm{{tot}}$ adds all three in quadrature per side.}}\n""")
        f.write("\\end{table}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base_dir", help="datacards_simultaneousWP directory")
    ap.add_argument("-o", "--output-dir", required=True)
    ap.add_argument("--SF-type", "-sf", dest="flavour", default="b", choices=["b", "c"])
    ap.add_argument("--era", default=None,
                    help="override the upper-right label for EVERY figure. By "
                         "default each figure gets its own era and luminosity "
                         "from LUMI_FB, which is what a single-year plot needs.")
    ap.add_argument("--formats", nargs="+", default=["png", "pdf"])
    args = ap.parse_args()

    style()
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    data = collect(args.base_dir, args.flavour)
    if not data:
        raise SystemExit(f"no *{SUFFIX} results found under {args.base_dir}")

    table_rows, incomplete, pt_order = [], [], []
    for year in sorted(data):
        per_pt_raw = data[year]
        pts, _ = order_pt_bins(list(per_pt_raw))
        for p in pts:
            if p not in pt_order:
                pt_order.append(p)
        per_pt = {}
        for p in pts:
            for wp in WP_TIERS:
                b = budget(per_pt_raw.get(p, {}).get(wp, {}))
                if b is None:
                    incomplete.append(f"{year}/{p}/{wp}")
                    continue
                per_pt.setdefault(p, {})[wp] = b
                table_rows.append(dict(year=year, pt=p, wp=wp, **b))

        ydir = out / year; ydir.mkdir(parents=True, exist_ok=True)
        f = args.flavour
        era = era_text(year, args.era)
        figure_vs_pt(year, per_pt, pts, f, ydir / f"SF{f}_vs_pt_{year}",
                     era, args.formats)
        figure_vs_tau21(year, per_pt_raw, pts, f, ydir / f"SF{f}_vs_tau21_{year}",
                        era, args.formats)
        with open(ydir / f"SF{f}_uncertainties_{year}.json", "w") as handle:
            json.dump(per_pt, handle, indent=2)
        print(f"[OK] {year}: {sum(len(v) for v in per_pt.values())} (pT, WP) points")

    latex_table(table_rows, out / f"SF{args.flavour}_table.tex",
                args.flavour, pt_order)
    print(f"[OK] LaTeX table -> {out / f'SF{args.flavour}_table.tex'}")
    if incomplete:
        print(f"[WARN] {len(incomplete)} (year, pT, WP) had no nominal "
              f"tau21={TAU21_CENTRAL} fit and were skipped:")
        for label in incomplete:
            print(f"        {label}")

    n_tau = [r["n_tau21"] for r in table_rows]
    if n_tau and min(n_tau) < len(TAU21_VALUES) - 1:
        print(f"[WARN] some points have fewer than {len(TAU21_VALUES)-1} tau21 "
              f"variations (min {min(n_tau)}); their tau21 systematic is "
              "underestimated")


if __name__ == "__main__":
    main()
