#!/usr/bin/env python3

"""
Plot the b- and c-flavour scale factors from a simultaneous Loose/Medium/Tight fit.

Reads the summary written by run_simultaneousWP_fits.py
(ALL_FIT_RESULTS_simultaneousWP*.csv) and produces:

  SF_vs_pt_<tau21>.{png,pdf}   SF vs pT bin, rows b and c, one column per year,
                               three WP series per panel, asymmetric errors.
  SF_vs_tau21.{png,pdf}        the same SFs against the tau21 cut, showing how
                               stable each measurement is against that choice.

Usage
-----
    python mutag_calib/scripts/plot_SFs_simultaneousWP.py <ALL_FIT_RESULTS...csv> \
        -o <plots_dir> --tau21 0.30
"""

import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
import pandas as pd

WP_TIERS = ["Loose", "Medium", "Tight"]

# Categorical slots 1-3 of the validated reference palette, in fixed order.
# Do not cycle or re-order: the ordering is what clears the CVD gates.
WP_COLOR = {"Loose": "#2a78d6", "Medium": "#eb6834", "Tight": "#1baf7a"}
# Secondary encoding, so the series stay separable without colour.
WP_MARKER = {"Loose": "o", "Medium": "s", "Tight": "^"}

FLAVOUR_LABEL = {"b": "b jets", "c": "c jets"}


def year_label(y):
    """2016 is split into eras, whose names are twice as long as a plain year."""
    return str(y).replace("_", " ")

INK = "#000000"
INK_SOFT = "#4a4a4a"
GRID = "#d9d8d4"
SURFACE = "#ffffff"

# A fitted value within this of a declared bound is treated as pinned
BOUND_TOL = 1e-3


def style():
    """CMS style, scaled down: hep.style.CMS is sized for one square pad and is
    far too large for these multi-panel grids."""
    hep.style.use(hep.style.CMS)
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "savefig.bbox": "tight",
        "font.size": 13, "axes.labelsize": 14, "legend.fontsize": 13,
        "xtick.labelsize": 12, "ytick.labelsize": 12,
        "xtick.major.size": 7, "xtick.minor.size": 3.5,
        "ytick.major.size": 7, "ytick.minor.size": 3.5,
        "axes.linewidth": 1.1, "axes.labelpad": 6,
    })


def cms_frame(fig, axes_row, era, cms_size=17, lumi_size=14):
    """CMS label above the first panel, energy/era above the last."""
    hep.cms.text("Preliminary", ax=axes_row[0], fontsize=cms_size)
    hep.cms.lumitext(f"{era}  (13 TeV)", ax=axes_row[-1], fontsize=lumi_size)


def panel_tag(ax, text, fontsize=14):
    """Identify a panel from inside the frame.

    An axes title would sit in the same strip hep.cms.text() writes into, so the
    two collide on the first panel; in-frame keeps every panel labelled the same
    way and costs no vertical space.
    """
    ax.text(0.04, 0.955, text, transform=ax.transAxes, ha="left", va="top",
            fontsize=fontsize, fontweight="bold", color=INK, zorder=6,
            bbox=dict(facecolor=SURFACE, edgecolor="none", alpha=0.85, pad=2.5))


def stack_below_axes(fig, axes_flat, label=None, label_size=15,
                     note=None, note_size=12):
    """Put a shared x label and/or a footnote below the rendered tick labels.

    Rotated or dense tick labels reach further down than either tight_layout's
    rect or supxlabel's default y knows about, so measure what was actually
    drawn and stack from there.
    """
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    bottom = min(t.get_window_extent(rend).y0
                 for a in axes_flat for t in a.get_xticklabels() if t.get_text())
    y0 = fig.transFigure.inverted().transform((0, bottom))[1]
    if label:
        fig.supxlabel(label, fontsize=label_size, y=y0 - 0.030)
    if note:
        fig.text(0.5, y0 - (0.075 if label else 0.035), note,
                 ha="center", fontsize=note_size, color=INK_SOFT)


def pt_sort_key(label):
    """(low, high) of a 'Pt-300to400' / 'Pt-300toInf' style label, in GeV."""
    match = re.match(r"(\d+)to(\d+|Inf)$", label)
    if not match:
        return (1e9, 1e9)
    low = float(match.group(1))
    high = np.inf if match.group(2) == "Inf" else float(match.group(2))
    return (low, high)


def order_pt_bins(labels):
    """Exclusive bins in increasing pT, with the inclusive bin last.

    The widest bin (300toInf) spans the others, so it is a summary point rather
    than another step along the axis; keeping it at the right edge stops it
    reading as part of the trend.
    """
    labels = list(dict.fromkeys(labels))

    def width(label):
        low, high = pt_sort_key(label)
        return (1e4 if np.isinf(high) else high) - low

    widest = max(labels, key=width)
    rest = sorted((x for x in labels if x != widest), key=pt_sort_key)
    return rest + [widest], widest


def load(csv_path):
    df = pd.read_csv(csv_path)
    # Drop "*_reweight" rows: that is the MC-reweighted systematic-check card at
    # the same tau21 value, not another point on the tau21 axis.
    df = df[~df["cut"].str.endswith("_reweight")].copy()
    df["pt"] = df["category"].str.extract(r"_Pt-([^_]+)_")
    df["tau21"] = df["cut"].str.replace("tau21_0p", "0.", regex=False).astype(float)
    df["year"] = df["year"].astype(str)

    # --nonsignal-sf shared gives one SF_c column instead of per-tier ones. Alias
    # it onto all three tier names so the per-tier plotting code works unchanged.
    # The c panel then repeats one value across WPs, which is honest: it really
    # is one parameter, not three that agree.
    for flavour in ("b", "c", "light"):
        base = f"SF_{flavour}"
        if base not in df.columns:
            continue
        for tier in WP_TIERS:
            if f"{base}_{tier}" in df.columns:
                continue
            for suffix in ("", "_errUp", "_errDown"):
                if f"{base}{suffix}" in df.columns:
                    df[f"{base}_{tier}{suffix}"] = df[f"{base}{suffix}"]
    return df


def auto_ylim_b(df, pad=0.12, headroom=0.16):
    """Range covering every SF_b central value, with room for the panel tag."""
    vals = np.concatenate([df[f"SF_b_{t}"].to_numpy(float)
                           for t in WP_TIERS if f"SF_b_{t}" in df])
    vals = vals[np.isfinite(vals)]
    if not len(vals):
        return (0.35, 1.75)
    lo, hi = float(vals.min()), float(vals.max())
    hi = max(hi, 1.0)          # the SF = 1 reference line must stay visible
    lo = min(lo, 1.0)
    span = max(hi - lo, 1e-3)
    lo, hi = lo - pad * span, hi + pad * span
    return (lo, hi + headroom * (hi - lo))


def at_bound(value, upper):
    return value <= BOUND_TOL or (upper is not None and value >= upper - BOUND_TOL)


def draw_series(ax, xs, ys, lo, hi, pinned, tier, ylim, label=None):
    """One WP series, with error bars clipped to the panel.

    SF_c_Medium can carry an uncertainty of +/-4.6 -- larger than the parameter's
    own [0,5] range -- and letting matplotlib autoscale to that flattens every
    other point in the row to a smear. So the panel keeps a fixed physical range
    and any bar running past it is cut at the frame and capped with a caret, the
    standard "continues beyond" mark, rather than silently rescaling the axis.
    """
    ymin, ymax = ylim
    ylo, yhi = ys - lo, ys + hi
    cut_lo, cut_hi = ylo < ymin, yhi > ymax
    colour = WP_COLOR[tier]

    ax.vlines(xs, np.clip(ylo, ymin, ymax), np.clip(yhi, ymin, ymax),
              color=colour, lw=1.4, alpha=0.9, zorder=3)
    # Flat caps on ends that are real, carets on ends that are cut off.
    for mask, ends, marker in ((~cut_lo, np.clip(ylo, ymin, ymax), "_"),
                               (~cut_hi, np.clip(yhi, ymin, ymax), "_"),
                               (cut_lo, np.full_like(ys, ymin), "v"),
                               (cut_hi, np.full_like(ys, ymax), "^")):
        if mask.any():
            ax.plot(xs[mask], ends[mask], linestyle="none", marker=marker,
                    markersize=6 if marker in "v^" else 5,
                    color=colour, markeredgewidth=1.4, zorder=3)

    if (~pinned).any():
        ax.plot(xs[~pinned], ys[~pinned], linestyle="none", marker=WP_MARKER[tier],
                markersize=7.5, color=colour, zorder=4, label=label)
    if pinned.any():
        # Hollow: the fit ran into the rateParam range instead of finding a minimum.
        ax.plot(xs[pinned], ys[pinned], linestyle="none", marker=WP_MARKER[tier],
                markersize=8.5, markerfacecolor="none", markeredgecolor=colour,
                markeredgewidth=2.0, zorder=5,
                label=label if not (~pinned).any() else None)


def draw_panel(ax, sub, flavour, x_labels, inclusive, upper_bounds, ylim,
               legend_labels=False, dodge=0.17):
    """One (flavour, year) panel: SF vs pT bin, three WP series."""
    positions = {label: i for i, label in enumerate(x_labels)}

    for k, tier in enumerate(WP_TIERS):
        col = f"SF_{flavour}_{tier}"
        if col not in sub:
            continue
        offset = (k - 1) * dodge
        xs, ys, lo, hi, pinned = [], [], [], [], []
        for label in x_labels:
            row = sub[sub["pt"] == label]
            if row.empty or pd.isna(row[col].iloc[0]):
                continue
            value = float(row[col].iloc[0])
            xs.append(positions[label] + offset)
            ys.append(value)
            lo.append(float(row[f"{col}_errDown"].iloc[0]))
            hi.append(float(row[f"{col}_errUp"].iloc[0]))
            pinned.append(at_bound(value, upper_bounds.get(col)))
        if not xs:
            continue
        draw_series(ax, np.array(xs), np.array(ys), np.array(lo), np.array(hi),
                    np.array(pinned, dtype=bool), tier, ylim,
                    label=tier if legend_labels else None)

    ax.axhline(1.0, color=INK_SOFT, lw=1.1, ls="--", zorder=1)
    ceiling = max((upper_bounds.get(f"SF_{flavour}_{t}") or 0) for t in WP_TIERS)
    if ceiling and ylim[0] < ceiling < ylim[1]:
        ax.axhline(ceiling, color=INK_SOFT, lw=1.0, ls=":", zorder=1)
        ax.text(0.985, ceiling, " fit bound ", transform=ax.get_yaxis_transform(),
                ha="right", va="bottom", fontsize=10, color=INK_SOFT)
    if inclusive in positions:
        ax.axvline(positions[inclusive] - 0.5, color=GRID, lw=1.0, ls=":", zorder=1)
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels([l.replace("to", "\u2013").replace("Inf", "\u221e") for l in x_labels])
    ax.set_xlim(-0.55, len(x_labels) - 0.45)
    ax.set_ylim(*ylim)
    ax.set_axisbelow(True)
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())


def figure_vs_pt(df, tau21, upper_bounds, ylims, outdir, formats, title, era):
    sel = df[np.isclose(df["tau21"], tau21)]
    if sel.empty:
        raise SystemExit(f"No rows with tau21 = {tau21}; available: {sorted(df.tau21.unique())}")
    years = sorted(sel["year"].unique())
    x_labels, inclusive = order_pt_bins(sel["pt"])

    fig, axes = plt.subplots(2, len(years), figsize=(6.4 * len(years), 8.4),
                             sharex=True, sharey="row", squeeze=False,
                             gridspec_kw={"hspace": 0.09, "wspace": 0.06})
    for row, flavour in enumerate(["b", "c"]):
        for col, year in enumerate(years):
            ax = axes[row][col]
            draw_panel(ax, sel[sel["year"] == year], flavour, x_labels, inclusive,
                       upper_bounds, ylims[flavour],
                       legend_labels=(row == 0 and col == 0))
            panel_tag(ax, f"{year_label(year)}   {FLAVOUR_LABEL[flavour]}")
            if col == 0:
                ax.set_ylabel(f"SF, {FLAVOUR_LABEL[flavour]}")

    cms_frame(fig, axes[0], era)
    handles, labels = axes[0][0].get_legend_handles_labels()
    order = [labels.index(t) for t in WP_TIERS if t in labels]
    fig.legend([handles[i] for i in order], [labels[i] for i in order],
               loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=3,
               frameon=False, fontsize=14, handletextpad=0.4, columnspacing=2.2)
    fig.suptitle(f"{title} ($\\tau_{{21}} < {tau21:.2f}$)", fontsize=17, y=1.005)
    fig.tight_layout(rect=[0, 0.035, 1, 0.93])
    stack_below_axes(
        fig, axes[1], label=r"FatJet $p_{T}$ [GeV]",
        note="Hollow marker: parameter pinned at a fit bound.   "
             "Caret: error bar continues beyond the frame.")

    stem = outdir / f"SF_vs_pt_tau21_{str(tau21).replace('.', 'p')}"
    for ext in formats:
        fig.savefig(f"{stem}.{ext}", dpi=200)
    plt.close(fig)
    return stem


def figure_vs_tau21(df, upper_bounds, ylims, outdir, formats, title, era):
    years = sorted(df["year"].unique())
    x_labels, _ = order_pt_bins(df["pt"])

    nrow = 2 * len(years)
    fig, axes = plt.subplots(nrow, len(x_labels),
                             figsize=(3.6 * len(x_labels), 3.0 * nrow),
                             sharex=True, sharey="row", squeeze=False,
                             gridspec_kw={"hspace": 0.09, "wspace": 0.06})
    for yi, year in enumerate(years):
        for row_in_year, flavour in enumerate(["b", "c"]):
            row = yi * 2 + row_in_year
            for col, label in enumerate(x_labels):
                ax = axes[row][col]
                sub = df[(df["year"] == year) & (df["pt"] == label)].sort_values("tau21")
                for tier in WP_TIERS:
                    c = f"SF_{flavour}_{tier}"
                    if c not in sub or sub[c].isna().all():
                        continue
                    ys = sub[c].to_numpy()
                    ax.plot(sub["tau21"], np.clip(ys, *ylims[flavour]),
                            color=WP_COLOR[tier], lw=1.8, zorder=2, alpha=0.85)
                    draw_series(ax, sub["tau21"].to_numpy(), ys,
                                sub[f"{c}_errDown"].to_numpy(),
                                sub[f"{c}_errUp"].to_numpy(),
                                np.array([at_bound(v, upper_bounds.get(c)) for v in ys]),
                                tier, ylims[flavour],
                                label=tier if (row == 0 and col == 0) else None)
                ax.axhline(1.0, color=INK_SOFT, lw=1.1, ls="--", zorder=1)
                ax.set_ylim(*ylims[flavour])
                ax.set_axisbelow(True)
                bin_label = label.replace("to", "\u2013").replace("Inf", "\u221e")
                # short flavour here: the row's y label already spells it out, and the
                # long form overflows the panel once the year is an era name.
                panel_tag(ax, f"{year_label(year)}  {bin_label} GeV   {flavour}",
                          fontsize=12)
                if col == 0:
                    ax.set_ylabel(f"SF, {FLAVOUR_LABEL[flavour]}")

    cms_frame(fig, axes[0], era)
    handles, labels = axes[0][0].get_legend_handles_labels()
    order = [labels.index(t) for t in WP_TIERS if t in labels]
    fig.legend([handles[i] for i in order], [labels[i] for i in order],
               loc="upper center", bbox_to_anchor=(0.5, 0.965), ncol=3,
               frameon=False, fontsize=14, handletextpad=0.4, columnspacing=2.2)
    fig.suptitle(f"{title} \u2014 stability against the $\\tau_{{21}}$ cut",
                 fontsize=17, y=1.003)
    fig.tight_layout(rect=[0, 0.02, 1, 0.955])
    stack_below_axes(fig, axes[-1], label=r"$\tau_{21}$ cut",
                     note="Hollow marker: parameter pinned at a fit bound.   "
                          "Caret: error bar continues beyond the frame.")

    stem = outdir / "SF_vs_tau21"
    for ext in formats:
        fig.savefig(f"{stem}.{ext}", dpi=200)
    plt.close(fig)
    return stem


def write_table(df, tau21, outdir):
    """The non-colour route to the same numbers (contrast relief)."""
    sel = df[np.isclose(df["tau21"], tau21)].copy()
    x_labels, _ = order_pt_bins(sel["pt"])
    sel["pt"] = pd.Categorical(sel["pt"], categories=x_labels, ordered=True)
    cols = ["year", "pt"] + [f"SF_{f}_{t}" for f in ("b", "c") for t in WP_TIERS]
    table = sel.sort_values(["year", "pt"])[cols]
    path = outdir / f"SF_table_tau21_{str(tau21).replace('.', 'p')}.csv"
    table.to_csv(path, index=False)
    print(f"\nScale factors at tau21 < {tau21:.2f}\n")
    print(table.to_string(index=False, float_format=lambda x: f"{x:7.3f}"))
    return path


def read_upper_bounds(datacards_dir):
    """Declared rateParam upper bounds, from any pois.yaml in the tree.

    Only used to decide whether a fitted value is pinned; falls back to 5 (the
    default range in create_datacards_simultaneousWP.py) when unavailable.
    """
    bounds = {}
    if datacards_dir:
        import yaml
        for path in sorted(Path(datacards_dir).glob("*/*/*/pois.yaml")):
            with open(path) as handle:
                ranges = yaml.safe_load(handle).get("ranges", {})
            for name, spec in ranges.items():
                hi = float(str(spec).strip("[]").split(",")[1])
                bounds[name] = min(bounds.get(name, hi), hi)
            break
    return bounds


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", help="ALL_FIT_RESULTS_simultaneousWP*.csv")
    parser.add_argument("-o", "--outdir", default="SF_plots_simultaneousWP")
    parser.add_argument("--tau21", type=float, default=0.30,
                        help="tau21 cut for the SF-vs-pT figure (default 0.30)")
    parser.add_argument("--datacards-dir", default=None,
                        help="datacards_simultaneousWP tree, to read the declared "
                             "rateParam bounds from pois.yaml (default: assume 5)")
    parser.add_argument("--ylim-b", nargs=2, type=float, default=None,
                        metavar=("LO", "HI"),
                        help="y-range of the b panels (default: fitted to the data, "
                             "so no measured SF_b falls outside the frame)")
    parser.add_argument("--ylim-c", nargs=2, type=float, default=[-0.3, 6.4],
                        metavar=("LO", "HI"),
                        help="y-range of the c panels. The default spans the [0,5] "
                             "rateParam range the SF_c may take plus headroom above "
                             "it, so the pile-up of pinned points at the bound is "
                             "visibly a ceiling and does not collide with the label")
    parser.add_argument("--title", default="GloParT $X_{bb}$ scale factors, simultaneous WP fit",
                        help="Figure title prefix (LaTeX-in-mathtext OK); "
                             "default assumes the simultaneous-fit source")
    # 41.48 + 59.83 fb-1, read from pocket_coffea's lumi.picobarns inside the
    # pocketcoffea container -- the table the templates were normalised with.
    parser.add_argument("--era", default=r"2017+2018, 101 fb$^{-1}$",
                        help="text placed before '(13 TeV)' above the last panel")
    parser.add_argument("--formats", nargs="+", default=["png", "pdf"])
    args = parser.parse_args()

    style()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load(args.csv)
    bounds = read_upper_bounds(args.datacards_dir)
    default_bounds = {f"SF_{f}_{t}": bounds.get(f"SF_{f}_{t}", 5.0)
                      for f in ("b", "c") for t in WP_TIERS}

    # A hardcoded y-range silently pushed real SF_b measurements off the frame,
    # where they showed only as a caret. Fit the range to the central values so
    # every measured point is inside it; error bars running past still get a caret.
    ylims = {"b": tuple(args.ylim_b) if args.ylim_b else auto_ylim_b(df),
             "c": tuple(args.ylim_c)}
    a = figure_vs_pt(df, args.tau21, default_bounds, ylims, outdir,
                 args.formats, args.title, args.era)
    b = figure_vs_tau21(df, default_bounds, ylims, outdir,
                    args.formats, args.title, args.era)
    t = write_table(df, args.tau21, outdir)

    print(f"\nWrote:\n  {a}.{{{','.join(args.formats)}}}"
          f"\n  {b}.{{{','.join(args.formats)}}}\n  {t}")


if __name__ == "__main__":
    main()
