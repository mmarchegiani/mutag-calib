#!/usr/bin/env python

"""
Script to create combine datacards from pocketcoffea output for mutag calibration.

This script creates datacards for each tagger working point and pt bin combination,
with pass and fail categories. It organizes the datacards following the structure
defined in the fit templates configuration.
"""

import os
import argparse
import yaml
from pathlib import Path
from collections import defaultdict
import uproot
from coffea.util import load
from hist import Hist
from hist.axis import StrCategory

from pocket_coffea.utils.stat import MCProcess, DataProcess, SystematicUncertainty, MCProcesses, DataProcesses, Systematics
from pocket_coffea.utils.stat.combine import combine_datacards

# Import the configuration to get the same parameters
import mutag_calib
from mutag_calib.utils.stat.datacard_mutag import DatacardMutag


def define_processes(samples, years):
    """Define MC and data processes for the analysis."""
    
    # Define MC processes based on flavor tagging
    mc_processes = MCProcesses([
        MCProcess(
            name="light",
            samples=samples["light"],  # Will be populated from sample names ending with _l
            years=years,
            is_signal=False,
            has_rateParam=True,
        ),
        MCProcess(
            name="c",
            samples=samples["c"],  # Will be populated from sample names ending with _c or _cc  
            years=years,
            is_signal=False,
            has_rateParam=True,
        ),
        MCProcess(
            name="b",
            samples=samples["b"],  # Will be populated from sample names ending with _b or _bb
            years=years,
            is_signal=True,        # b-jets are the signal process for the calibration
            has_rateParam=True,
        )
    ])
    
    # Define data process
    data_processes = DataProcesses([
        DataProcess(
            name="data_obs",
            samples=[],  # Will be populated from sample names starting with DATA_
            years=years,
        )
    ])
    
    return mc_processes, data_processes


def categorize_samples(cutflow):
    """Categorize samples based on their names."""
    light_samples = set()
    c_samples = set()
    b_samples = set()
    data_samples = set()

    baseline_category = "inclusive"

    for dataset, samples_dict in cutflow[baseline_category].items():
        for sample_name in samples_dict.keys():
            if sample_name.startswith("QCD_Madgraph_"):  # we don't want QCD Madgraph samples in the datacards, we use it for systematics
                continue
            elif sample_name.startswith("VJets_"):  # only for debugging
                continue
            elif sample_name.startswith("SingleTop_"):  # only for debugging
                continue
            elif sample_name.startswith("DATA_"):
                data_samples.add(sample_name)
            elif sample_name.endswith("_l"):
                light_samples.add(sample_name)
            elif sample_name.endswith(("_c", "_cc")):
                c_samples.add(sample_name)
            elif sample_name.endswith(("_b", "_bb")):
                b_samples.add(sample_name)
    
    return {
        "light": sorted(list(light_samples)),
        "c": sorted(list(c_samples)),
        "b": sorted(list(b_samples)),
        "data_obs": sorted(list(data_samples))
    }


def define_systematics(years, mc_process_names):
    """Define systematic uncertainties."""
    systematics = Systematics([
        # Add basic systematic uncertainties
        SystematicUncertainty(
            name="lumi", 
            typ="lnN",
            processes=mc_process_names,
            value=1.025,  # 2.5% luminosity uncertainty
            years=years,
        ),
        SystematicUncertainty(
            name="pileup",
            typ="shape",
            processes={name : 1.0 for name in mc_process_names},
            #value=1.01,  # 1% pileup uncertainty
            years=years,
        ),
        # Add process-specific uncertainties
        SystematicUncertainty(
            name="light_norm",
            typ="lnN",
            processes=["light"],
            value=1.20,  # 20% normalization uncertainty for light jets
            years=years,
        ),
        SystematicUncertainty(
            name="c_norm", 
            typ="lnN",
            processes=["c"],
            value=1.20,  # 20% normalization uncertainty for c jets
            years=years,
        ),
    ])
    
    return systematics

def get_passfail_ratio(datacards):
    """Calculate the pass/fail ratio for each category and tau21 cut value.
    
    Args:
        datacards: Nested dictionary of format datacards[category][tau21] = datacard
    
    Returns:
        Dictionary of pass/fail ratios organized by parent category and tau21 cut
    """
    sumw_percat = defaultdict(dict)
    # First level: categories
    for cat in datacards:
        # Second level: tau21 cuts
        for tau21, datacard in datacards[cat].items():
            shape_histograms = datacard.create_shape_histogram_dict(is_data=False)
            sumw_percat[cat][tau21] = {
                process_name.split("_nominal")[0]: hist.values().sum() 
                for process_name, hist in shape_histograms.items()
            }

    passfail_ratio = defaultdict(lambda: defaultdict(dict))
    parent_categories = set(['-'.join(cat.split("-")[:-1]) for cat in datacards.keys()])
    
    for parent_cat in parent_categories:
        for tau21 in datacards[f"{parent_cat}-pass"].keys():
            sumw_pass = sumw_percat[f"{parent_cat}-pass"][tau21]
            sumw_fail = sumw_percat[f"{parent_cat}-fail"][tau21]
            for flavor in sumw_pass.keys():
                passfail_ratio[parent_cat][tau21][flavor] = float(sumw_pass[flavor] / sumw_fail[flavor])

    return dict(passfail_ratio)

def add_Madgraph_systematic(histogram_logsumSVmass_tau21):
    """Function to add the Madgraph systematic uncertainty to the histogram."""
    # select the qcd_samples
    qcd_samples = [
        s for s in histogram_logsumSVmass_tau21.keys()
        if s.startswith("QCD_")
    ]
    #extract the flavors
    flavors = {
        s.split("__")[1].split("_")[-1]
        for s in qcd_samples
        if "__" in s and len(s.split("__")[1].split("_")) >= 2
    }
    print(f"flavors: {flavors}")
    for flav in flavors:
        mu_name = f"QCD_MuEnriched__QCD_MuEnriched_{flav}"
        mg_name = f"QCD_Madgraph__QCD_Madgraph_{flav}"
        # check that both MuEnriched and Madgraph flavor samples are in the keys
        if mu_name not in histogram_logsumSVmass_tau21 or mg_name not in histogram_logsumSVmass_tau21:
            continue
        mu_datasets = histogram_logsumSVmass_tau21[mu_name]
        mg_datasets = histogram_logsumSVmass_tau21[mg_name]
        mg_sum = sum(h.values().sum() for h in mg_datasets.values())
        mu_sum = sum(h.values().sum() for h in mu_datasets.values())
        ratio = mg_sum / mu_sum
        for dataset, h_mu in mu_datasets.items():
            current_vars = list(h_mu.axes["variation"])  # variations already present
            print(f"current_vars: {current_vars}")
            new_vars = current_vars + [f"QCD_MuEnriched_ratio_Up", f"QCD_MuEnriched_ratio_Down"]  # adding new variations
            print(f"new_vars: {new_vars}")
            new_vars_axis = StrCategory(new_vars, name="variation")  # new variation axis
            new_hist = Hist(
                h_mu.axes["cat"],
                new_vars_axis,
                h_mu.axes["FatJetGood.logsumcorrSVmass"],
                h_mu.axes["FatJetGood.tau21"],
                storage=h_mu.storage_type()
            )
            for v in current_vars:
                new_hist[{ "variation": v }].view(flow=True)[:] = h_mu[{ "variation": v }].view(flow=True)
            nominal_vals = h_mu[{ "variation": "nominal" }].view(flow=True)
            new_hist[{ "variation": "QCD_MuEnriched_ratio_Up" }].view(flow=True)[:] = nominal_vals * ratio
            new_hist[{ "variation": "QCD_MuEnriched_ratio_Down" }].view(flow=True)[:] = nominal_vals * (2 - ratio)
            if ratio > 2:
                raise ValueError(f"ratio > 2 for flavor {flav}, cannot create down variation")
            histogram_logsumSVmass_tau21[mu_name][dataset] = new_hist

def get_1d_histogram(h2d_dict, tau21_cut):
    """Function to get the 1D histogram from the 2D histogram by integrating over the axis corresponding to tau21."""
    h1d_dict = {}
    for proc, ds_dict in h2d_dict.items():
        # print(f"\nProcessing {proc}...\n")
        h1d_dict[proc] = {}
        # print(f"{ds_dict.keys()}\n")
        for ds, histo2d in ds_dict.items():
            # print(f"Dataset: {ds}\n")
            ax_tau21 = histo2d.axes["FatJetGood.tau21"]
            bin_stop = next(i for i, edge in enumerate(ax_tau21.edges[1:]) if edge > tau21_cut)
            histo_cut = histo2d.integrate(ax_tau21.name, 0, bin_stop)
            h1d_dict[proc][ds] = histo_cut
    # print(f"{h1d_dict.keys()}\n")
    return h1d_dict

def print_report(successful_categories, failed_categories):
    for d_cat in successful_categories:
        print(f"✅ Year: {d_cat['year']}, Category: {d_cat['category']}, Folder: {d_cat['folder']}")
    for d_cat in failed_categories:
        print(f"❌ Year: {d_cat['year']}, Category: {d_cat['category']}, Error: {d_cat['error']}")

    # Summary printout counting successes and failures rate
    ncat = len(successful_categories) + len(failed_categories)
    print("\nSummary Report:")
    print(f"Total categories processed: {ncat}")
    print(f"✅  Successful: {len(successful_categories)} / {ncat}")
    print(f"❌  Failed: {len(failed_categories)} / {ncat}")

# Helper function to extract the tau21 string for directory naming
get_tau21_str = lambda x: f"tau21_{x:.2f}".replace('.', 'p')

def main():
    parser = argparse.ArgumentParser(description="Create combine datacards from pocketcoffea output")
    parser.add_argument("input_file", help="Path to the pocketcoffea output .coffea file")
    parser.add_argument("--output-dir", "-o", default=None, help="Output directory for datacards")
    parser.add_argument("--variable", default="FatJetGood_logsumcorrSVmass_tau21", help="Variable to use for the fit")
    parser.add_argument("--years", nargs="+", default=["2022_preEE", "2022_postEE", "2023_preBPix", "2023_postBPix"], 
                       help="Years to include in the analysis")
    parser.add_argument("--verbose", "-v", action="store_true", default=False, help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Load the coffea output
    print(f"Loading coffea output from {args.input_file}")
    output = load(args.input_file)
    
    # Extract histograms, cutflow, and metadata
    histograms = output["variables"]
    cutflow = output["cutflow"]
    datasets_metadata = output["datasets_metadata"]
    categories = [cat for cat in cutflow.keys() if cat.startswith('msd')]
    
    # Categorize samples
    samples = categorize_samples(cutflow)
    print(f"Found samples: {samples}")
    print(f"Available histograms: {list(histograms.keys())}")

    successful_categories = []
    failed_categories = []

    for year in args.years:
        # Define processes and systematics
        mc_processes, data_processes = define_processes(samples, [year])
        print(f"{mc_processes.items()}")
        print(f"{data_processes.items()}")
        
        # Update process samples based on what we found
        for process_name, process in mc_processes.items():
            process.samples = samples[process_name]
        
        for process_name, process in data_processes.items():
            process.samples = samples[process_name]
        
        systematics = define_systematics([year], [p_name for p_name, p in mc_processes.items()])

        # Add the variation QCD_Madgraph/QCD_MuEnriched to the Hist
        add_Madgraph_systematic(histograms[args.variable])
        
        # Create output directory
        if args.output_dir is None:
            args.output_dir = str(Path(args.input_file).parent / "datacards")
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Dictionary to store all datacards for combination
        all_datacards = defaultdict(dict)
        
        # Create datacards for each combination
        for cat in categories:

            for tau21 in [0.2, 0.25, 0.3, 0.35, 0.4]:
                print(f"Creating datacard: Year: {year}\tCategory: {cat}\ttau21 < {tau21}")
                
                # Get the 1D histogram by integrating over tau21 axis with a specific cut: tau21 < tau21_cut
                histo_1d = get_1d_histogram(histograms[args.variable], tau21)
                # Create datacard
                datacard = DatacardMutag(
                    histograms=histo_1d,
                    datasets_metadata=datasets_metadata,
                    cutflow=cutflow,
                    years=[year],
                    mc_processes=mc_processes,
                    data_processes=data_processes,
                    systematics=systematics,
                    category=cat,  # Category string matching the multicuts structure
                    verbose=args.verbose
                )
                
                # Store for combination between pass and fail regions
                all_datacards[cat][tau21] = datacard
                
        passfail_ratio = get_passfail_ratio(all_datacards)

        # Loop over categories again to dump datacards modified with pass/fail ratios
        parent_categories = set()
        for cat in categories:
            for tau21 in [0.2, 0.25, 0.3, 0.35, 0.4]:
                # Extract parent category (without pass/fail)
                parent_category = '-'.join(cat.split("-")[:-1])
                parent_categories.add(parent_category)
                region = cat.split("-")[-1]
                # Create directory for this category
                tau21_str = get_tau21_str(tau21)
                category_dir = output_dir / year / parent_category / tau21_str / region
                category_dir.mkdir(parents=True, exist_ok=True)
                datacard = all_datacards[cat][tau21]

                # Modify action of rateParam for fail regions by passing the passfail_ratio argument
                if cat.endswith("-pass"):
                    kwargs = {"directory" : str(category_dir)}
                elif cat.endswith("-fail"):
                    parent_cat = '-'.join(cat.split("-")[:-1])
                    kwargs = {"directory" : str(category_dir), "passfail_ratio" : passfail_ratio[parent_cat][tau21]}
                try:
                    datacard.dump(**kwargs)
                    successful_categories.append({"year": year, "category": cat, "folder": str(category_dir)})
                except Exception as e:
                    print(f"Failed to create datacard for Year: {year}, Category: {cat}")
                    print(str(e))
                    failed_categories.append({"year": year, "category": cat, "error": str(e)})

        # Create combined datacard for pass+fail regions, for each parent category
        for parent_cat in parent_categories:
            for tau21 in [0.2, 0.25, 0.3, 0.35, 0.4]:
                print(f"\nCreating combined datacard for category: {parent_cat} with tau21 < {tau21} (pass + fail)")
                tau21_str = get_tau21_str(tau21)
                directory = output_dir / year / parent_cat / tau21_str
                combine_datacards(
                    datacards={f"{region}/datacard.txt": all_datacards[f"{parent_cat}-{region}"][tau21] for region in ["pass", "fail"]},
                    directory=directory
                )
                # Save pass/fail ratio to a YAML file
                filename = directory / "passfail_ratio.yaml"
                print(f"Saving pass/fail ratio to {filename}")
                with open(filename, "w") as f:
                    yaml.dump({"passfail_ratio" : passfail_ratio[parent_cat][tau21]}, f, indent=4)

                print(f"Combined datacard saved in {directory}")

    # Print summary report
    print_report(successful_categories, failed_categories)

if __name__ == "__main__":
    main()
