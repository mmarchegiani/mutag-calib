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

from pocket_coffea.utils.stat import MCProcess, DataProcess, SystematicUncertainty, Datacard, Processes, Systematics, combine_datacards

# Import the configuration to get the same parameters
import mutag_calib
from mutag_calib.configs.fit_templates.fit_templates_Run3 import parameters


def load_parameters():
    """Load parameters from the configuration files."""
    # Get the same parameters as used in fit_templates_Run3.py
    taggers = parameters["mutag_calibration"]["taggers"]
    pt_binning = parameters["mutag_calibration"]["pt_binning"]["2022_preEE"]
    wp_dict = parameters["mutag_calibration"]["wp"]["2022_preEE"]
    
    return taggers, pt_binning, wp_dict


def define_processes(years):
    """Define MC and data processes for the analysis."""
    
    # Define MC processes based on flavor tagging
    mc_processes = Processes([
        MCProcess(
            name="light",
            samples=[],  # Will be populated from sample names ending with _l
            years=years,
            is_signal=False,
            has_rateParam=True,
        ),
        MCProcess(
            name="c",
            samples=[],  # Will be populated from sample names ending with _c or _cc  
            years=years,
            is_signal=False,
            has_rateParam=True,
        ),
        MCProcess(
            name="b",
            samples=[],  # Will be populated from sample names ending with _b or _bb
            years=years,
            is_signal=True,  # b-jets are typically the signal in b-tagging studies
            has_rateParam=False,
        )
    ])
    
    # Define data process
    data_processes = Processes([
        DataProcess(
            name="data_obs",
            samples=[],  # Will be populated from sample names starting with DATA_
            years=years,
        )
    ])
    
    return mc_processes, data_processes


def categorize_samples(cutflow):
    """Categorize samples based on their names."""
    light_samples = []
    c_samples = []
    b_samples = []
    data_samples = []
    
    for sample_name in cutflow.keys():
        if sample_name.startswith("DATA_"):
            data_samples.append(sample_name)
        elif sample_name.endswith("_l"):
            light_samples.append(sample_name)
        elif sample_name.endswith(("_c", "_cc")):
            c_samples.append(sample_name)
        elif sample_name.endswith(("_b", "_bb")):
            b_samples.append(sample_name)
    
    return {
        "light": light_samples,
        "c": c_samples, 
        "b": b_samples,
        "data_obs": data_samples
    }


def define_systematics(years, mc_process_names):
    """Define systematic uncertainties."""
    systematics = Systematics([
        # Add basic systematic uncertainties
        SystematicUncertainty(
            name="lumi", 
            type="lnN",
            processes=mc_process_names,
            value=1.025,  # 2.5% luminosity uncertainty
            years=years,
        ),
        SystematicUncertainty(
            name="pileup",
            type="lnN", 
            processes=mc_process_names,
            value=1.01,  # 1% pileup uncertainty
            years=years,
        ),
        # Add process-specific uncertainties
        SystematicUncertainty(
            name="light_norm",
            type="lnN",
            processes=["light"],
            value=1.10,  # 10% normalization uncertainty for light jets
            years=years,
        ),
        SystematicUncertainty(
            name="c_norm", 
            type="lnN",
            processes=["c"],
            value=1.15,  # 15% normalization uncertainty for c jets
            years=years,
        ),
    ])
    
    return systematics


def create_category_name(pt_bin_name, tagger_name):
    """Create category name for the datacard."""
    return f"{pt_bin_name}_{tagger_name}"


def main():
    parser = argparse.ArgumentParser(description="Create combine datacards from pocketcoffea output")
    parser.add_argument("input_file", help="Path to the pocketcoffea output .coffea file")
    parser.add_argument("--output-dir", "-o", default="datacards", help="Output directory for datacards")
    parser.add_argument("--variable", default="FatJetGood_msoftdrop", help="Variable to use for the fit")
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
    
    # Load configuration parameters
    taggers, pt_binning, wp_dict = load_parameters()
    msd = 40.  # Mass cut value used in the analysis
    
    # Categorize samples
    sample_categories = categorize_samples(cutflow)
    print(f"Found samples: {sample_categories}")
    
    # Define processes and systematics
    mc_processes, data_processes = define_processes(args.years)
    
    # Update process samples based on what we found
    for process in mc_processes:
        process.samples = sample_categories[process.name]
    
    for process in data_processes:
        process.samples = sample_categories[process.name]
    
    systematics = define_systematics(args.years, [p.name for p in mc_processes])
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Dictionary to store all datacards for combination
    all_datacards = {}
    
    # Loop over pt bins and tagger working points (following the structure in L97-108)
    print("Creating datacards for each pt bin and tagger working point...")
    
    # Generate pt bin names 
    pt_bin_names = []
    for pt_low, pt_high in pt_binning.values():
        pt_bin_names.append(f'Pt-{pt_low}to{pt_high}')
    
    # Generate tagger category names
    tagger_names = []
    for tagger in taggers:
        for wp, wp_value in wp_dict[tagger].items():
            for region in ["pass", "fail"]:
                tagger_names.append(f"msd{int(msd)}{tagger}{region}{wp}wp")
    
    # Create datacards for each combination
    for pt_bin_name in pt_bin_names:
        for tagger_name in tagger_names:
            category_name = create_category_name(pt_bin_name, tagger_name)
            
            # Create directory for this category
            category_dir = output_dir / category_name
            category_dir.mkdir(exist_ok=True)
            
            print(f"Creating datacard for category: {category_name}")
            
            try:
                # Create datacard
                datacard = Datacard(
                    histograms=histograms,
                    datasets_metadata=datasets_metadata,
                    cutflow=cutflow,
                    years=args.years,
                    mc_processes=mc_processes,
                    data_processes=data_processes,
                    systematics=systematics,
                    category=f"tagger__{tagger_name}__pt__{pt_bin_name}",  # Category string matching the multicuts structure
                    variable=args.variable,
                )
                
                # Save datacard
                datacard_filename = f"datacard_{category_name}.txt"
                datacard_path = category_dir / datacard_filename
                
                datacard.save_card(str(datacard_path))
                datacard.save_histograms(str(category_dir / f"templates_{category_name}.root"))
                
                # Store for combination
                all_datacards[str(datacard_path)] = datacard
                
                print(f"  Saved datacard: {datacard_path}")
                print(f"  Saved templates: {category_dir / f'templates_{category_name}.root'}")
                
            except Exception as e:
                print(f"  Error creating datacard for {category_name}: {e}")
                continue
    
    # Create combined datacard
    print(f"\nCreating combined datacard...")
    try:
        combine_datacards(
            datacards=all_datacards,
            directory=str(output_dir),
            output_name="combined_datacard.txt"
        )
        print(f"Combined datacard saved: {output_dir / 'combined_datacard.txt'}")
    except Exception as e:
        print(f"Error creating combined datacard: {e}")
    
    print(f"\nDatacard creation completed. Output directory: {output_dir}")
    print(f"Total categories created: {len(all_datacards)}")


if __name__ == "__main__":
    main()
