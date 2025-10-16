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

from pocket_coffea.utils.stat import MCProcess, DataProcess, SystematicUncertainty, MCProcesses, DataProcesses, Systematics
from pocket_coffea.utils.stat.combine import combine_datacards

# Import the configuration to get the same parameters
import mutag_calib
from mutag_calib.configs.fit_templates.fit_templates_run3 import parameters
from mutag_calib.utils.stat.datacard_mutag import DatacardMutag

def load_parameters():
    """Load parameters from the configuration files."""
    # Get the same parameters as used in fit_templates_Run3.py
    taggers = parameters["mutag_calibration"]["taggers"]
    pt_binning_list = parameters["mutag_calibration"]["pt_binning"]["2022_preEE"]
    wp_dict = parameters["mutag_calibration"]["wp"]["2022_preEE"]
    
    return taggers, pt_binning_list, wp_dict


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
            if sample_name.startswith("DATA_"):
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
            typ="lnN", 
            processes=mc_process_names,
            value=1.01,  # 1% pileup uncertainty
            years=years,
        ),
        # Add process-specific uncertainties
        SystematicUncertainty(
            name="light_norm",
            typ="lnN",
            processes=["light"],
            value=1.10,  # 10% normalization uncertainty for light jets
            years=years,
        ),
        SystematicUncertainty(
            name="c_norm", 
            typ="lnN",
            processes=["c"],
            value=1.15,  # 15% normalization uncertainty for c jets
            years=years,
        ),
    ])
    
    return systematics

def get_passfail_ratio(datacards):
    sumw_percat = {}
    for cat, datacard in datacards.items():
        shape_histograms = datacard.create_shape_histogram_dict(is_data=False)
        sumw_percat[cat] = {process_name.split("_nominal")[0] : hist.values().sum() for process_name, hist in shape_histograms.items()}

    passfail_ratio = defaultdict(dict)
    parent_categories = set(['-'.join(cat.split("-")[:-1]) for cat in datacards.keys()])
    for parent_cat in parent_categories:
        sumw_pass = sumw_percat[f"{parent_cat}-pass"]
        sumw_fail = sumw_percat[f"{parent_cat}-fail"]
        for flavor in sumw_pass.keys():
            passfail_ratio[parent_cat][flavor] = float(sumw_pass[flavor] / sumw_fail[flavor])

    return dict(passfail_ratio)

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

def main():
    parser = argparse.ArgumentParser(description="Create combine datacards from pocketcoffea output")
    parser.add_argument("input_file", help="Path to the pocketcoffea output .coffea file")
    parser.add_argument("--output-dir", "-o", default=None, help="Output directory for datacards")
    parser.add_argument("--variable", default="FatJetGood_logsumcorrSVmass", help="Variable to use for the fit")
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
    
    # Load configuration parameters
    taggers, pt_binning_list, wp_dict = load_parameters()
    msd = 40.  # Mass cut value used in the analysis
    
    # Categorize samples
    samples = categorize_samples(cutflow)
    print(f"Found samples: {samples}")
    print(f"Available histograms: {list(histograms.keys())}")

    successful_categories = []
    failed_categories = []

    for year in args.years:
        # Define processes and systematics
        mc_processes, data_processes = define_processes(samples, [year])
        
        # Update process samples based on what we found
        for process_name, process in mc_processes.items():
            process.samples = samples[process_name]
        
        for process_name, process in data_processes.items():
            process.samples = samples[process_name]
        
        systematics = define_systematics([year], [p_name for p_name, p in mc_processes.items()])
        
        # Create output directory
        if args.output_dir is None:
            args.output_dir = str(Path(args.input_file).parent / "datacards")
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Dictionary to store all datacards for combination
        all_datacards = {}
        
        # Create datacards for each combination
        for cat in categories:

            print(f"Creating datacard: Year: {year}\tCategory: {cat}")
            
            # Create datacard
            datacard = DatacardMutag(
                histograms=histograms[args.variable],
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
            all_datacards[cat] = datacard
                
        passfail_ratio = get_passfail_ratio(all_datacards)

        # Loop over categories again to dump datacards modified with pass/fail ratios
        parent_categories = set()
        for cat in categories:
            # Extract parent category (without pass/fail)
            parent_category = '-'.join(cat.split("-")[:-1])
            parent_categories.add(parent_category)
            region = cat.split("-")[-1]
            # Create directory for this category
            category_dir = output_dir / year / parent_category / region
            category_dir.mkdir(parents=True, exist_ok=True)
            datacard = all_datacards[cat]

            # Modify action of rateParam for fail regions by passing the passfail_ratio argument
            if cat.endswith("-pass"):
                kwargs = {"directory" : str(category_dir)}
            elif cat.endswith("-fail"):
                parent_cat = '-'.join(cat.split("-")[:-1])
                kwargs = {"directory" : str(category_dir), "passfail_ratio" : passfail_ratio[parent_cat]}
            try:
                datacard.dump(**kwargs)
                successful_categories.append({"year": year, "category": cat, "folder": str(category_dir)})
            except Exception as e:
                print(f"Failed to create datacard for Year: {year}, Category: {cat}")
                print(str(e))
                failed_categories.append({"year": year, "category": cat, "error": str(e)})

        # Create combined datacard for pass+fail regions, for each parent category
        for parent_cat in parent_categories:
            print(f"\nCreating combined datacard for category: {parent_cat} (pass+fail)")
            directory = output_dir / year / parent_cat
            combine_datacards(
                datacards={f"{region}/datacard.txt": all_datacards[f"{parent_cat}-{region}"] for region in ["pass", "fail"]},
                directory=directory
            )
            # Save pass/fail ratio to a YAML file
            filename = directory / "passfail_ratio.yaml"
            print(f"Saving pass/fail ratio to {filename}")
            with open(filename, "w") as f:
                yaml.dump({"passfail_ratio" : passfail_ratio[parent_cat]}, f, indent=4)

            print(f"Combined datacard saved in {directory}")

    # Print summary report
    print_report(successful_categories, failed_categories)

if __name__ == "__main__":
    main()
