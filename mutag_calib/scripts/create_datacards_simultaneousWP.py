#!/usr/bin/env python

"""
Create combine datacards for a SIMULTANEOUS fit of the three GloParT WP tiers
(Loose, Medium, Tight), sharing one signal strength and all nuisances.

Why not just combineCards.py of the three per-WP fits
----------------------------------------------------
The WP tiers are *exclusive* score slices, so the six per-WP regions hold only
four distinct event samples:

    A = (-Inf, L)   Loose-fail
    B = [L, M)      Loose-pass  == Medium-fail
    C = [M, T)      Medium-pass == Tight-fail
    D = [T, Inf)    Tight-pass

Merging all six would enter slices B and C twice and overstate the sensitivity.
So this builds one channel per slice (4 channels) and puts the WP dependence
into the rate parameters instead.

The rate-parameter model
------------------------
Let f_A..f_D be a flavour's MC fractions in the four slices (sum = 1). Three
scale factors per flavour float together in one likelihood. Slice D feeds all
three WPs, so only a simultaneous fit gives the SF-to-SF covariance, and because
it is one card every nuisance is correlated across the WPs automatically.

SF_X scales the exclusive slice that WP X opens -- the weight you would apply to
a simulated jet landing in that score bin -- and slice A absorbs the
compensation that keeps the total flavour yield fixed:

    A: (1 - SF_L*f_B - SF_M*f_C - SF_T*f_D) / f_A,  B: SF_L,  C: SF_M,  D: SF_T

Note these are NOT the cumulative working-point SFs, eff(score >= X), which is
what is usually quoted. The two are a linear reparametrisation of each other:
run_inclusive_WP_crosscheck.py converts to the cumulative basis when comparing
against a 2-region inclusive fit.

Parameter naming
----------------
The b parameter is SF_b, not r. combine always creates its own POI named r, and
a datacard rateParam of the same name is either applied on top of it (scaling
signal twice) or silently dropped. The generated run_fit.sh freezes r at 1 and
redefines the POIs.

Output layout
-------------
    <output-dir>/<year>/<base>-simultaneousWP/<tau21_str>/
        {Loose-fail,Loose-pass,Medium-pass,Tight-pass}/{datacard.txt,shapes.root}
        combine_cards.sh        combineCards.py + text2workspace.py
        run_fit.sh              combine -M FitDiagnostics with the right POIs
        wp_efficiencies.yaml    MC slice fractions and cumulative efficiencies
        pois.yaml               SF definition and POI names, for extraction

Usage
-----
    python mutag_calib/scripts/create_datacards_simultaneousWP.py <output.coffea> \
        --years 2017 2018 -o <dir>/datacards_simultaneousWP

Fitted POIs are SF_b_Loose/Medium/Tight (and the c equivalents); correlations
come from the fitDiagnostics covariance.
"""

import argparse
import os
import sys
import yaml
from pathlib import Path
from collections import defaultdict

import numpy as np
from coffea.util import load

sys.path.insert(0, str(Path(__file__).parent))
from create_datacards import (  # noqa: E402
    DatacardMutag,
    add_Madgraph_systematic_1d,
    categorize_samples,
    define_processes,
    define_systematics,
    get_1d_histogram,
    get_tau21_str,
    print_report,
)
from pocket_coffea.utils.stat.combine import combine_datacards  # noqa: E402

WP_TIERS = ["Loose", "Medium", "Tight"]

# The four exclusive score slices in increasing order, named by the coffea
# category holding each. Loose-pass == Medium-fail and Medium-pass ==
# Tight-fail, so only one of each pair is used.
SLICES = ["Loose-fail", "Loose-pass", "Medium-pass", "Tight-pass"]

TAU21_CUTS = [0.2, 0.25, 0.3, 0.35, 0.4]

# Which of the four slices each WP tier "opens": Loose opens [L,M), Medium opens
# [M,T), Tight opens [T,Inf). Used by the exclusive SF definition.
TIER_SLICE_INDEX = {"Loose": 1, "Medium": 2, "Tight": 3}

# Below this MC fraction a slice counts as empty: its formula denominator is
# meaningless, so use the plain SF. Carrying no yield, the choice is inert.
EPS_FRACTION = 1e-9


def unique(values: list) -> list:
    """Order-preserving de-duplication (--poi-mode shared repeats one name)."""
    return list(dict.fromkeys(values))


def fmt(value: float) -> str:
    """Format a number for a combine formula.

    12 significant digits, not fewer: the slice-C denominator (e_M - e_T) is a
    difference of nearly equal efficiencies, so rounding it too early leaves the
    prefit multiplier visibly off 1.
    """
    return f"{value:.12g}"


class DatacardMutagSimultaneousWP(DatacardMutag):
    """Datacard for one exclusive tagger-score slice of the simultaneous WP fit.

    Unlike DatacardMutag this does not know about pass/fail: the per-slice
    multiplier is handed in fully formed via :meth:`set_rate_parameters`, as
    either a plain rateParam (``SF_x rateParam * proc 1 [lo,hi]``) or a formula
    rateParam with a name guaranteed not to collide with any parameter.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # {"<process>_<year>": spec}, see set_rate_parameters
        self.rate_parameters = {}
        # {"<poi>": "[lo,hi]"} declared on this card via extArg
        self.ext_args = {}

    def set_rate_parameters(self, rate_parameters: dict, ext_args: dict = None) -> None:
        self.rate_parameters = rate_parameters
        self.ext_args = ext_args or {}

    def ext_args_section(self) -> str:
        """Declare the POIs as free parameters.

        The formula rateParams reference POIs that may never appear on their own
        anywhere in the combination (SF_L and SF_M in --poi-mode per-wp), and
        ModelBuilder.doRateParams() raises "dependent parameters not found" for
        those. extArg creates them explicitly, with a range, before the rate
        parameters are processed (ModelBuilder.doModel calls doExtArgs first).
        """
        content = ""
        for name, param_range in self.ext_args.items():
            content += f"{name} extArg 1 {param_range}{self.linesep}"
        return content

    @staticmethod
    def pad(text: str, width: int) -> str:
        """Left-justify to `width`, but always leave at least one space.

        str.ljust() is a no-op when the string is already longer than the
        width, which silently glues the next column on. The formula rateParam
        names here are bin-keyed and ~80 characters, far wider than
        adjust_syst_colum (the longest systematic name, ~20), so plain ljust
        produced "rp_..._2017rateParam" and combine failed with
        "Unsupported pdf *" on the shifted token.
        """
        return text.ljust(width) if len(text) < width else text + " "

    def rate_parameters_section(self) -> str:
        content = ""
        for process in self.mc_processes.values():
            for year in process.years:
                if not process.has_rateParam:
                    continue
                spec = self.rate_parameters.get(f"{process.name}_{year}")
                if spec is None:
                    continue
                if spec["kind"] == "plain":
                    line = self.pad(spec["poi"], self.adjust_syst_colum)
                    line += self.pad("rateParam", self.adjust_columns)
                    line += f"* {process.name}_{year} 1 {spec['range']}"
                else:
                    line = self.pad(spec["name"], self.adjust_syst_colum)
                    line += self.pad("rateParam", self.adjust_columns)
                    line += (
                        f"* {process.name}_{year} {spec['formula']} "
                        f"{','.join(spec['args'])}"
                    )
                content += line + self.linesep
        return content

    def content(self, shapes_filename: str) -> str:
        content = self.preamble()
        content += self.sectionsep + self.linesep

        content += self.shape_section(shapes_name=shapes_filename)
        content += self.sectionsep + self.linesep

        content += self.observation_section()
        content += self.sectionsep + self.linesep

        content += self.expectation_section()
        content += self.sectionsep + self.linesep

        content += self.systematics_section()
        content += self.sectionsep + self.linesep

        content += self.rate_parameters_section()
        content += self.sectionsep + self.linesep

        if self.ext_args:
            content += self.ext_args_section()
            content += self.sectionsep + self.linesep

        if self.mcstat:
            content += self.mcstat_section()
            content += self.sectionsep + self.linesep

        return content

    def dump(
        self,
        directory: os.PathLike,
        card_name: str = "datacard.txt",
        shapes_name: str = "shapes.root",
    ) -> None:
        import uproot

        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, card_name), "w") as card:
            card.write(self.content(shapes_filename=shapes_name))

        shape_histograms = self.create_shape_histogram_dict(is_data=False)
        if self.has_data:
            shape_histograms_data = self.create_shape_histogram_dict(is_data=True)
        # This class overrides dump(), so it must call the guard itself -- the
        # copy in DatacardMutag.dump() is never reached from here.
        self._neutralise_empty_variations(shape_histograms)
        with uproot.recreate(os.path.join(directory, shapes_name)) as root_file:
            if self.has_data:
                for shape, histogram in shape_histograms_data.items():
                    root_file[shape] = histogram
            for shape, histogram in shape_histograms.items():
                root_file[shape] = histogram


def reweight_mc_to_data(histograms_1d, categories, samples, years):
    """Reweight MC to data bin-by-bin over the union of the four score slices.

    create_datacards.get_1d_histogram_reweighed() does the same thing for a
    two-region fit, but it locates its inclusive region by the hard-coded
    "<parent>-pass"/"<parent>-fail" labels, which do not exist here -- it would
    find no matching category and silently return the histograms untouched. This
    version takes the fit categories explicitly.

    MC (b + c + light) summed over ``categories`` is scaled to match data in the
    same region; the weights are applied to every MC variation in those
    categories. Data is left alone. Operates in place and returns the dict.
    """
    if isinstance(years, str):
        years = [years]

    example = None
    for per_dataset in histograms_1d.values():
        for histogram in per_dataset.values():
            if "variation" in [axis.name for axis in histogram.axes]:
                example = histogram
                break
        if example is not None:
            break
    if example is None:
        return histograms_1d

    cat_axis = example.axes["cat"]
    nom_index = example.axes["variation"].index("nominal")
    fit_axes = [ax for ax in example.axes if ax.name not in ("cat", "variation")]
    if len(fit_axes) != 1:
        raise RuntimeError("Expected exactly one fit variable axis after tau21 integration")
    n_fit_bins = len(fit_axes[0].edges) - 1

    cat_indices = []
    for label in categories:
        try:
            cat_indices.append(cat_axis.index(label))
        except KeyError:
            continue
    if not cat_indices:
        return histograms_1d

    mc_samples = set(samples["light"] + samples["c"] + samples["b"])
    data_samples = set(samples["data_obs"])
    mc_sum = np.zeros(n_fit_bins, dtype=float)
    data_sum = np.zeros(n_fit_bins, dtype=float)

    for process_name, per_dataset in histograms_1d.items():
        for dataset, histogram in per_dataset.items():
            if not any(year in dataset for year in years):
                continue
            values = histogram.view(flow=False)["value"]
            if values.ndim == 3:
                projection = values[cat_indices, nom_index, :].sum(axis=0)
            elif values.ndim == 2:
                projection = values[cat_indices, :].sum(axis=0)
            else:
                raise RuntimeError(f"Unsupported histogram dimensionality {values.ndim}")
            if process_name in mc_samples:
                mc_sum += projection
            elif process_name in data_samples:
                data_sum += projection

    with np.errstate(divide="ignore", invalid="ignore"):
        weights = np.where(mc_sum > 0.0, data_sum / mc_sum, 1.0)
        weights = np.nan_to_num(weights, nan=1.0, posinf=1.0, neginf=1.0)

    for process_name, per_dataset in histograms_1d.items():
        if process_name not in mc_samples:
            continue
        for dataset, histogram in per_dataset.items():
            if not any(year in dataset for year in years):
                continue
            view = histogram.view(flow=False)
            if view["value"].ndim == 3:
                scale = weights[np.newaxis, np.newaxis, :]
                view["value"][cat_indices, :, :] *= scale
                view["variance"][cat_indices, :, :] *= scale**2
            else:
                scale = weights[np.newaxis, :]
                view["value"][cat_indices, :] *= scale
                view["variance"][cat_indices, :] *= scale**2

    return histograms_1d


def nominal_yields(datacard) -> dict:
    """Nominal MC yield per '<process>_<year>' key for one datacard."""
    shapes = datacard.create_shape_histogram_dict(is_data=False)
    suffix = "_nominal"
    return {
        name[: -len(suffix)]: float(histogram.values().sum())
        for name, histogram in shapes.items()
        if name.endswith(suffix)
    }


def compute_wp_efficiencies(slice_datacards: dict) -> dict:
    """MC fractions and cumulative WP efficiencies per '<process>_<year>' key.

    :param slice_datacards: {slice_name: datacard} for the four exclusive slices
    :return: {process_key: {"fractions": [f_A, f_B, f_C, f_D],
                            "eff": {"Loose": e_L, "Medium": e_M, "Tight": e_T},
                            "total": total MC yield}}
    """
    yields = {name: nominal_yields(card) for name, card in slice_datacards.items()}

    process_keys = sorted({key for per_slice in yields.values() for key in per_slice})
    efficiencies = {}
    for key in process_keys:
        counts = [yields[name].get(key, 0.0) for name in SLICES]
        total = sum(counts)
        if total <= 0:
            print(f"  [WARN] process {key} has zero total MC yield, SF will be inert")
            fractions = [0.0, 0.0, 0.0, 0.0]
        else:
            fractions = [count / total for count in counts]
        _, f_b, f_c, f_d = fractions
        efficiencies[key] = {
            "fractions": fractions,
            "eff": {
                "Loose": f_b + f_c + f_d,
                "Medium": f_c + f_d,
                "Tight": f_d,
            },
            "total": total,
        }
    return efficiencies


def poi_names(process_name: str, share: bool = False) -> list:
    """POI name attached to each WP tier for a given flavour.

    The b-flavour parameter is SF_b and never `r`: see the module docstring.

    :param share: collapse the three tiers onto one POI for this flavour
        (used by --nonsignal-sf shared).
    """
    base = f"SF_{process_name}"
    if share:
        return [base, base, base]
    return [f"{base}_{tier}" for tier in WP_TIERS]


def poi_ranges(efficiencies: dict, key_to_process: dict,
               pois_by_process: dict) -> dict:
    """Upper bound for each POI so no slice can be driven negative.

    A corrected efficiency cannot exceed 1, bounding each SF by 1/f_X, the
    inverse of the slice fraction it scales. With --nonsignal-sf shared one POI
    carries all tiers, so the tightest bound wins.

    These are box constraints, so necessary but not sufficient: they do not
    enforce the sum rule SF_L*f_B + SF_M*f_C + SF_T*f_D <= 1 that keeps slice A
    positive. If the fit wanders past it, combine reports a negative yield.
    """
    ranges = {}
    for key, info in efficiencies.items():
        process_name = key_to_process.get(key)
        if process_name is None:
            continue
        for tier, poi in zip(WP_TIERS, pois_by_process[process_name]):
            scaled = info["fractions"][TIER_SLICE_INDEX[tier]]
            upper = 5.0 if scaled <= 0 else min(5.0, 0.995 / scaled)
            # keep the pre-fit value of 1 inside the range
            upper = max(1.05, upper)
            ranges[poi] = min(ranges.get(poi, upper), upper)
    return {poi: f"[0,{fmt(upper)}]" for poi, upper in ranges.items()}


def build_rate_parameter_spec(
    slice_index, info, pois, ranges, bin_name, process_name
):
    """The rateParam spec for one (slice, flavour).

    Returns either
        {"kind": "plain",   "poi": <name>, "range": "[0,hi]"}
    or  {"kind": "formula", "name": <unique name>, "formula": ..., "args": [...]}
    """
    f_a, f_b, f_c, f_d = info["fractions"]
    e_l = info["eff"]["Loose"]
    poi_l, poi_m, poi_t = pois
    # --nonsignal-sf shared repeats one name for this flavour, and with
    # SF_L = SF_M = SF_T the slice-A formula collapses to (1 - SF*e_L)/f_A.
    shared = poi_l == poi_m == poi_t

    def plain(poi):
        return {"kind": "plain", "poi": poi, "range": ranges[poi]}

    def formula(expression, args):
        # Must differ from every workspace parameter name: doRateParams() skips
        # a formula whose name exists, leaving the bare parameter in its place.
        # Keying on the bin keeps it unique if categories are ever combined.
        return {
            "kind": "formula",
            "name": f"rp_{process_name}_{bin_name}",
            "formula": expression,
            "args": args,
        }

    # Slice A absorbs the compensation that keeps the flavour yield fixed, so it
    # is the only slice whose multiplier depends on more than one SF.
    if slice_index == 0:
        if f_a <= EPS_FRACTION:
            return plain(poi_l)
        if shared:
            return formula(f"(1-@0*{fmt(e_l)})/{fmt(f_a)}", [poi_l])
        return formula(
            f"(1-@0*{fmt(f_b)}-@1*{fmt(f_c)}-@2*{fmt(f_d)})/{fmt(f_a)}",
            [poi_l, poi_m, poi_t],
        )

    # Every passing slice is scaled directly by its own SF.
    return plain(pois[slice_index - 1])


def write_fit_script(directory, pois_by_process, category):
    """FitDiagnostics command with the POIs of this model.

    combine's built-in `r` still multiplies the signal process (b), so it is
    pinned to 1; the physics POIs are the SF_* parameters. SF_light is frozen at
    1 as in the per-WP workflow.
    """
    float_pois = unique(pois_by_process["b"] + pois_by_process["c"])
    frozen_pois = unique(pois_by_process["light"])
    set_parameters = ["r=1"] + [f"{poi}=1" for poi in frozen_pois]
    freeze = ["r"] + frozen_pois

    script = f"""#!/bin/bash
# Simultaneous {'/'.join(WP_TIERS)} fit, exclusive SF definition
combine -M FitDiagnostics \\
    -d workspace.root \\
    --name .{category} \\
    --skipBOnlyFit \\
    --cminDefaultMinimizerStrategy 0 \\
    --robustHesse 1 \\
    --saveShapes --saveWithUncertainties --saveOverallShapes --saveWorkspace \\
    --ignoreCovWarning \\
    --redefineSignalPOIs {','.join(float_pois)} \\
    --setParameters {','.join(set_parameters)} \\
    --freezeParameters {','.join(freeze)}

# Second pass, for the UNCERTAINTIES only
# --robustHesse gives a trustworthy covariance but only a symmetric
# parabolic error, and in this model the profile likelihood is strongly
# asymmetric wherever SF_b and SF_c are near-degenerate.
# The two cannot be combined in one call: --robustHesse overwrites the MINOS
# errors with its own symmetric ones.
combine -M FitDiagnostics \
    -d workspace.root \
    --name .{category}.minos \
    --skipBOnlyFit \
    --cminDefaultMinimizerStrategy 0 \
    --minos all \
    --ignoreCovWarning \
    --redefineSignalPOIs {','.join(float_pois)} \
    --setParameters {','.join(set_parameters)} \
    --freezeParameters {','.join(freeze)}
"""
    path = Path(directory) / "run_fit.sh"
    with open(path, "w") as handle:
        handle.write(script)
    os.chmod(path, 0o755)


def build_category(
    base_category,
    histograms_1d,
    datasets_metadata,
    cutflow,
    years_group,
    mc_processes,
    data_processes,
    systematics,
    year,
    nonsignal_sf,
    verbose,
):
    """Build the four slice datacards of one (mass, pt, tau21) category."""
    slice_datacards = {}
    for slice_name in SLICES:
        slice_datacards[slice_name] = DatacardMutagSimultaneousWP(
            histograms=histograms_1d[slice_name],
            datasets_metadata=datasets_metadata,
            cutflow=cutflow,
            years=years_group,
            mc_processes=mc_processes,
            data_processes=data_processes,
            systematics=systematics,
            category=f"{base_category}-{slice_name}",
            bin_suffix=year,
            verbose=verbose,
        )

    efficiencies = compute_wp_efficiencies(slice_datacards)
    mc_process_names = [name for name, _ in mc_processes.items()]
    key_to_process = {
        f"{name}_{year_tag}": name
        for name in mc_process_names
        for year_tag in years_group
    }
    # c and light are nuisances, not the measurement, and are a small fraction of
    # every passing slice. Three free SF_c per category are so weakly constrained
    # that they run to their bounds and drag SF_b with them; --nonsignal-sf
    # shared gives them one SF each instead.
    signal_names = {name for name, process in mc_processes.items() if process.is_signal}
    pois_by_process = {
        name: poi_names(
            name,
            share=(nonsignal_sf == "shared" and name not in signal_names),
        )
        for name in mc_process_names
    }
    ranges = poi_ranges(efficiencies, key_to_process, pois_by_process)

    for slice_index, slice_name in enumerate(SLICES):
        datacard = slice_datacards[slice_name]
        specs = {}
        for process_name in mc_process_names:
            for year_tag in years_group:
                key = f"{process_name}_{year_tag}"
                if key not in efficiencies:
                    continue
                specs[key] = build_rate_parameter_spec(
                    slice_index,
                    efficiencies[key],
                    pois_by_process[process_name],
                    ranges,
                    datacard.bin,
                    process_name,
                )
        # All POIs are declared once, on the first slice card, so that the
        # formulas on the other cards always find their dependencies.
        ext_args = ranges if slice_index == 0 else {}
        datacard.set_rate_parameters(specs, ext_args)

    return slice_datacards, efficiencies, ranges, pois_by_process


def main():
    parser = argparse.ArgumentParser(
        description="Create combine datacards for a simultaneous Loose/Medium/Tight WP fit"
    )
    parser.add_argument("input_file", help="Path to the pocketcoffea output .coffea file")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Output directory (default: <input dir>/datacards_simultaneousWP)")
    parser.add_argument("--variable", default="FatJetGood_logsumcorrSVmass_tau21",
                        help="Variable to use for the fit")
    parser.add_argument("--years", nargs="+", default=["2017", "2018"],
                        help="Years to include in the analysis")
    parser.add_argument("--combined-years", action="store_true", default=False,
                        help="Treat all years as a single combined measurement")
    parser.add_argument("--category-prefix", default="globalParT3mass-80to170",
                        help="Only build categories whose name starts with this prefix")
    parser.add_argument("--nonsignal-sf", choices=["per-wp", "shared"], default="per-wp",
                        help="Whether the non-signal flavours (c, light) also get one SF "
                             "per WP. 'per-wp' (default) mirrors the b treatment. "
                             "'shared' gives c and light a single SF each across the three "
                             "tiers, which is much better conditioned: the per-WP SF_c are "
                             "only weakly constrained and destabilise the fit. The b SFs "
                             "stay per-WP either way.")
    parser.add_argument("--tau21-cuts", nargs="+", type=float, default=TAU21_CUTS,
                        help="tau21 upper cuts to build datacards for")
    parser.add_argument("--reweight", action="store_true", default=False,
                        help="Also build the MC-reweighted-to-data variant at tau21 < 0.30")
    parser.add_argument("--verbose", "-v", action="store_true", default=False)
    args = parser.parse_args()

    print(f"Loading coffea output from {args.input_file}\n")
    output = load(args.input_file)

    histograms = output["variables"]
    cutflow = output["cutflow"]
    datasets_metadata = output["datasets_metadata"]

    # Group the coffea categories "<base>-<tier>-<region>" by their base
    # (mass bin + pt bin + tagger), keeping only bases with all four slices.
    bases = defaultdict(set)
    for category in cutflow.keys():
        if not category.startswith(args.category_prefix):
            continue
        parts = category.rsplit("-", 2)
        if len(parts) != 3 or parts[1] not in WP_TIERS:
            continue
        bases[parts[0]].add(f"{parts[1]}-{parts[2]}")

    base_categories = sorted(
        base for base, found in bases.items() if set(SLICES).issubset(found)
    )
    if not base_categories:
        raise RuntimeError(
            f"No category with all four slices {SLICES} found for prefix "
            f"'{args.category_prefix}'. Available: {sorted(bases)}"
        )
    print(f"Base categories to fit simultaneously: {base_categories}\n")

    samples = categorize_samples(cutflow)
    print(f"Found samples: {samples}\n")

    if args.output_dir is None:
        args.output_dir = str(Path(args.input_file).parent / "datacards_simultaneousWP")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    year_groups = [args.years] if args.combined_years else [[y] for y in args.years]

    successful_categories = []
    failed_categories = []

    for years_group in year_groups:
        year = years_group[0]
        mc_processes, data_processes = define_processes(samples, years_group)
        for process_name, process in mc_processes.items():
            process.samples = samples[process_name]
        for process_name, process in data_processes.items():
            process.samples = samples[process_name]
        systematics = define_systematics(
            years_group, [name for name, _ in mc_processes.items()]
        )

        for base_category in base_categories:
            for tau21 in args.tau21_cuts:
                variants = [("", False)]
                if args.reweight and abs(tau21 - 0.3) < 1e-6:
                    variants.append(("_reweight", True))

                for suffix, reweighted in variants:
                    tau21_str = get_tau21_str(tau21) + suffix
                    label = f"{year}/{base_category}/{tau21_str}"
                    print(f"\n=== Building simultaneous WP datacards: {label} ===")

                    # One 1D histogram dict per slice: the Madgraph systematic is
                    # built per category, so it has to be added slice by slice.
                    slice_categories = [f"{base_category}-{name}" for name in SLICES]
                    histograms_1d = {}
                    for slice_name in SLICES:
                        category = f"{base_category}-{slice_name}"
                        histo = get_1d_histogram(histograms[args.variable], tau21)
                        if reweighted:
                            reweight_mc_to_data(
                                histo, slice_categories, samples, years_group
                            )
                        add_Madgraph_systematic_1d(histo, category)
                        histograms_1d[slice_name] = histo

                    try:
                        (
                            slice_datacards,
                            efficiencies,
                            ranges,
                            pois_by_process,
                        ) = build_category(
                            base_category, histograms_1d, datasets_metadata,
                            cutflow, years_group, mc_processes, data_processes,
                            systematics, year,
                            args.nonsignal_sf, args.verbose,
                        )
                    except Exception as error:  # noqa: BLE001
                        print(f"Failed to build {label}: {error}")
                        failed_categories.append(
                            {"year": year, "category": base_category, "error": str(error)}
                        )
                        continue

                    directory = (
                        output_dir / year / f"{base_category}-simultaneousWP" / tau21_str
                    )
                    directory.mkdir(parents=True, exist_ok=True)

                    for slice_name, datacard in slice_datacards.items():
                        try:
                            datacard.dump(directory=str(directory / slice_name))
                            successful_categories.append({
                                "year": year,
                                "category": f"{base_category}-{slice_name}",
                                "folder": str(directory / slice_name),
                            })
                        except Exception as error:  # noqa: BLE001
                            print(f"Failed to dump {label}/{slice_name}: {error}")
                            failed_categories.append({
                                "year": year,
                                "category": f"{base_category}-{slice_name}",
                                "error": str(error),
                            })

                    combine_datacards(
                        datacards={
                            f"{slice_name}/datacard.txt": slice_datacards[slice_name]
                            for slice_name in SLICES
                        },
                        directory=directory,
                    )
                    write_fit_script(
                        directory, pois_by_process,
                        f"{base_category}-simultaneousWP",
                    )

                    with open(directory / "wp_efficiencies.yaml", "w") as handle:
                        yaml.dump(
                            {
                                "slices": SLICES,
                                "efficiencies": {
                                    key: {
                                        "fractions": [float(f) for f in info["fractions"]],
                                        "eff": {k: float(v) for k, v in info["eff"].items()},
                                        "total": float(info["total"]),
                                    }
                                    for key, info in efficiencies.items()
                                },
                            },
                            handle,
                            indent=4,
                        )
                    with open(directory / "pois.yaml", "w") as handle:
                        yaml.dump(
                            {
                                "sf_definition": "exclusive",
                                "nonsignal_sf": args.nonsignal_sf,
                                "pois": pois_by_process,
                                "ranges": ranges,
                            },
                            handle,
                            indent=4,
                        )
                    print(f"Simultaneous WP datacards written to {directory}")

    print_report(successful_categories, failed_categories)


if __name__ == "__main__":
    main()
