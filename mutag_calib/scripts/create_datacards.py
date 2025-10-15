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
from coffea.util import load

from pocket_coffea.utils.stat import MCProcess, DataProcess, SystematicUncertainty, Datacard, MCProcesses, DataProcesses, Systematics
from pocket_coffea.utils.stat.combine import combine_datacards

# Import the configuration to get the same parameters
import mutag_calib
from mutag_calib.configs.fit_templates.fit_templates_run3 import parameters


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
            is_signal=True,  # b-jets are the signal for the mutag calibration measurement
            has_rateParam=False,
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
        successful_categories = []
        failed_categories = []
        for cat in categories:
                
            # Create directory for this category
            category_dir = output_dir / year / cat
            category_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"Creating datacard for category: {cat}")
            
            try:
                # Create datacard
                datacard = Datacard(
                    histograms=histograms[args.variable],
                    datasets_metadata=datasets_metadata,
                    cutflow=cutflow,
                    years=[year],
                    mc_processes=mc_processes,
                    data_processes=data_processes,
                    systematics=systematics,
                    category=cat,  # Category string matching the multicuts structure
                )
                
                datacard.dump(str(category_dir))
                
                # Store for combination
                all_datacards[str(category_dir)] = datacard
                
                successful_categories.append({"year": year, "category": cat, "folder": str(category_dir)})
                
            except Exception as e:
                failed_categories.append({"year": year, "category": cat, "error": str(e)})
                print(f"  Error creating datacard for {cat}: {e}")
                continue
    
    print_report(successful_categories, failed_categories)

    # Create combined datacard
    print(f"\nCreating combined datacard...")
    combine_datacards(
        datacards=all_datacards,
        directory=str(output_dir)
    )
    print(f"Combined datacard saved: {output_dir / 'combined_datacard.txt'}")
    
    print(f"\nDatacard creation completed. Output directory: {output_dir}")
    print(f"Total categories created: {len(all_datacards)}")


if __name__ == "__main__":
    main()
