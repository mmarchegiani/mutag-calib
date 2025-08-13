#!/usr/bin/env python3
"""
Script to extract BTagMu triggers for Run 3 data-taking periods from ROOT files.
This script reads one data file and one MC file for each period and extracts
all HLT trigger paths starting with 'BTagMu'.
"""

import json
import uproot
import yaml
from collections import defaultdict
import argparse
import sys
import os

def load_datasets(data_file, mc_file):
    """Load dataset files and return their contents."""
    with open(data_file, 'r') as f:
        data_datasets = json.load(f)
    
    with open(mc_file, 'r') as f:
        mc_datasets = json.load(f)
    
    return data_datasets, mc_datasets

def get_first_file_for_period(datasets, year_period):
    """Get the first file for a given year period."""
    for dataset_name, dataset_info in datasets.items():
        if dataset_info['metadata']['year'] == year_period:
            if dataset_info['files']:
                return dataset_info['files'][0]
    return None

def extract_hlt_triggers(root_file_path):
    """Extract HLT trigger paths starting with 'BTagMu' from a ROOT file."""
    try:
        print(f"Opening file: {root_file_path}")
        with uproot.open(root_file_path) as f:
            # Get the Events tree
            tree = f['Events']
            
            # Get all branch names that start with 'HLT_BTagMu'
            all_branches = tree.keys()
            hlt_branches = [branch for branch in all_branches if branch.startswith('HLT_BTagMu')]
            
            # Separate AK4 and AK8 triggers
            ak4_triggers = []
            ak8_triggers = []
            other_triggers = []
            
            for branch in hlt_branches:
                # Remove 'HLT_' prefix
                trigger_name = branch.replace('HLT_', '')
                # Remove any trailing type information (like '/B', '/I', etc.)
                if '/' in trigger_name:
                    trigger_name = trigger_name.split('/')[0]
                
                # Categorize triggers
                if 'AK4' in trigger_name and trigger_name not in ak4_triggers:
                    ak4_triggers.append(trigger_name)
                elif 'AK8' in trigger_name and trigger_name not in ak8_triggers:
                    ak8_triggers.append(trigger_name)
                elif trigger_name not in other_triggers:
                    other_triggers.append(trigger_name)
            
            return {
                'ak4': sorted(ak4_triggers),
                'ak8': sorted(ak8_triggers),
                'other': sorted(other_triggers)
            }
    
    except Exception as e:
        print(f"Error processing file {root_file_path}: {e}")
        return {'ak4': [], 'ak8': [], 'other': []}

def main():
    parser = argparse.ArgumentParser(description='Extract BTagMu triggers for Run 3')
    parser.add_argument('--data-file', required=True, help='Path to DATA_BTagMu_run3.json')
    parser.add_argument('--mc-file', required=True, help='Path to MC_QCD_MuEnriched_run3.json')
    parser.add_argument('--output-ak4', default='triggers_AK4_run3.yaml', help='Output YAML file for AK4 triggers')
    parser.add_argument('--output-ak8', default='triggers_AK8_run3.yaml', help='Output YAML file for AK8 triggers')
    parser.add_argument('--output-yaml', default='triggers_run3.yaml', help='Output YAML file with all triggers')
    parser.add_argument('--use-mc-only', action='store_true', help='Use only MC files (skip data files)')
    
    args = parser.parse_args()
    
    # Load datasets
    print("Loading dataset files...")
    data_datasets, mc_datasets = load_datasets(args.data_file, args.mc_file)
    
    # Define the periods to process
    periods = ['2022_preEE', '2022_postEE', '2023_preBPix', '2023_postBPix']
    
    # Dictionary to store triggers for each period
    all_triggers = {}
    ak4_triggers_all = {}
    ak8_triggers_all = {}
    
    for period in periods:
        print(f"\nProcessing period: {period}")
        
        ak4_triggers_set = set()
        ak8_triggers_set = set()
        other_triggers_set = set()
        
        # Process data file for this period (unless using MC only)
        if not args.use_mc_only:
            data_file = get_first_file_for_period(data_datasets, period)
            if data_file:
                print(f"Processing DATA file for {period}")
                triggers_dict = extract_hlt_triggers(data_file)
                ak4_triggers_set.update(triggers_dict['ak4'])
                ak8_triggers_set.update(triggers_dict['ak8'])
                other_triggers_set.update(triggers_dict['other'])
                print(f"Found {len(triggers_dict['ak4'])} AK4, {len(triggers_dict['ak8'])} AK8, {len(triggers_dict['other'])} other BTagMu triggers in DATA")
            else:
                print(f"Warning: No DATA file found for period {period}")
        
        # Process MC file for this period
        mc_file = get_first_file_for_period(mc_datasets, period)
        if mc_file:
            print(f"Processing MC file for {period}")
            triggers_dict = extract_hlt_triggers(mc_file)
            ak4_triggers_set.update(triggers_dict['ak4'])
            ak8_triggers_set.update(triggers_dict['ak8'])
            other_triggers_set.update(triggers_dict['other'])
            print(f"Found {len(triggers_dict['ak4'])} AK4, {len(triggers_dict['ak8'])} AK8, {len(triggers_dict['other'])} other BTagMu triggers in MC")
        else:
            print(f"Warning: No MC file found for period {period}")
        
        # Store unique triggers for this period
        all_triggers_for_period = sorted(list(ak4_triggers_set | ak8_triggers_set | other_triggers_set))
        
        if all_triggers_for_period:
            all_triggers[period] = {
                'BTagMu': all_triggers_for_period
            }
            print(f"Total unique BTagMu triggers for {period}: {len(all_triggers_for_period)}")
        else:
            print(f"No BTagMu triggers found for period {period}")
        
        # Store AK4 and AK8 triggers separately
        if ak4_triggers_set:
            ak4_triggers_all[period] = {
                'BTagMu': sorted(list(ak4_triggers_set))
            }
        
        if ak8_triggers_set:
            ak8_triggers_all[period] = {
                'BTagMu': sorted(list(ak8_triggers_set))
            }
    
    # Create the output structures
    output_structure_all = {
        'HLT_triggers': all_triggers
    }
    
    output_structure_ak4 = {
        'HLT_triggers': ak4_triggers_all
    }
    
    output_structure_ak8 = {
        'HLT_triggers': ak8_triggers_all
    }
    
    # Write to YAML file (all triggers)
    print(f"\nWriting all triggers to {args.output_yaml}")
    with open(args.output_yaml, 'w') as f:
        yaml.dump(output_structure_all, f, default_flow_style=False, sort_keys=False)
    
    # Write to YAML files (separate AK4 and AK8)
    print(f"Writing AK4 triggers to {args.output_ak4}")
    with open(args.output_ak4, 'w') as f:
        yaml.dump(output_structure_ak4, f, default_flow_style=False, sort_keys=False)
    
    print(f"Writing AK8 triggers to {args.output_ak8}")
    with open(args.output_ak8, 'w') as f:
        yaml.dump(output_structure_ak8, f, default_flow_style=False, sort_keys=False)
    
    print("Done!")
    
    # Print summary
    print("\nSummary:")
    print("\nAK4 Triggers:")
    for period, triggers in ak4_triggers_all.items():
        print(f"  {period}: {len(triggers['BTagMu'])} triggers")
        for trigger in triggers['BTagMu']:
            print(f"    - {trigger}")
    
    print("\nAK8 Triggers:")
    for period, triggers in ak8_triggers_all.items():
        print(f"  {period}: {len(triggers['BTagMu'])} triggers")
        for trigger in triggers['BTagMu']:
            print(f"    - {trigger}")
    
    print("\nAll Triggers (combined):")
    for period, triggers in all_triggers.items():
        print(f"  {period}: {len(triggers['BTagMu'])} triggers")

if __name__ == "__main__":
    main()
