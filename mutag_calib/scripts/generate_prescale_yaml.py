#!/usr/bin/env python

"""
Script to generate YAML output with average prescale factors by year and HLT trigger path.

This script reads the prescale JSON files and calculates the average prescale factor
for each HLT trigger path within each data-taking year, then outputs in the requested YAML format.
"""

import os
import json
import yaml
import argparse
from pathlib import Path
from collections import defaultdict
import numpy as np

def load_yaml_config(config_path):
    """Load the YAML configuration file with prescales."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def resolve_config_path(path_string, config_dir):
    """Resolve ${config_dir:} placeholders in file paths."""
    if "${config_dir:}" in path_string:
        return path_string.replace("${config_dir:}", config_dir)
    return path_string

def load_prescale_json(json_path):
    """Load and parse a prescale JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def parse_prescale_data(data):
    """Parse prescale data to extract run numbers, lumi sections, and weights."""
    prescale_info = []
    
    # Navigate the JSON structure
    corrections = data.get("corrections", [])
    for correction in corrections:
        if correction.get("name") == "prescaleWeight":
            content = correction.get("data", {}).get("content", [])
            
            for run_entry in content:
                run_number = run_entry["key"]
                path_content = run_entry["value"]["content"]
                
                for path_entry in path_content:
                    hlt_path = path_entry["key"]
                    weight_data = path_entry["value"]
                    
                    # Handle different weight data structures
                    if isinstance(weight_data, (int, float)):
                        # Simple constant weight
                        prescale_info.append({
                            'run': run_number,
                            'hlt_path': hlt_path,
                            'lumi_start': 1,
                            'lumi_end': float('inf'),
                            'weight': float(weight_data),
                            'lumi_range_size': float('inf')
                        })
                    elif isinstance(weight_data, dict) and weight_data.get("nodetype") == "binning":
                        # Binned weights by lumi section
                        edges = weight_data["edges"]
                        content_weights = weight_data["content"]
                        
                        for i, weight in enumerate(content_weights):
                            lumi_start = edges[i]
                            lumi_end = edges[i+1] if i+1 < len(edges) else float('inf')
                            lumi_range_size = lumi_end - lumi_start if lumi_end != float('inf') else float('inf')
                            
                            prescale_info.append({
                                'run': run_number,
                                'hlt_path': hlt_path,
                                'lumi_start': lumi_start,
                                'lumi_end': lumi_end,
                                'weight': float(weight),
                                'lumi_range_size': lumi_range_size
                            })
    
    return prescale_info

def calculate_weighted_average(prescale_entries):
    """Calculate weighted average prescale, weighting by luminosity section range size."""
    if not prescale_entries:
        return 0.0
    
    total_weight = 0.0
    total_range = 0.0
    
    for entry in prescale_entries:
        weight = entry['weight']
        range_size = entry['lumi_range_size']
        
        if range_size == float('inf'):
            # For infinite ranges, treat as having weight 1000 (arbitrary large number)
            # This ensures constant prescales for entire runs have proper influence
            range_size = 1000.0
        
        total_weight += weight * range_size
        total_range += range_size
    
    if total_range == 0:
        return 0.0
    
    return total_weight / total_range

def generate_prescale_yaml(config_path, output_path=None):
    """Generate YAML output with average prescale factors by year and HLT path."""
    
    # Load configuration
    config_path = Path(config_path)
    if not config_path.exists():
        print(f"Error: Configuration file {config_path} does not exist")
        return
    
    config = load_yaml_config(config_path)
    config_dir = config_path.parent
    
    # Extract prescale information
    hlt_triggers_prescales = config.get("HLT_triggers_prescales", {})
    
    # Dictionary to store results: year -> trigger_group -> hlt_path -> list of prescale entries
    results = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    print(f"Processing prescale files...")
    
    processed_files = set()
    
    for year, year_data in hlt_triggers_prescales.items():
        print(f"\nProcessing year: {year}")
        
        for trigger_group, triggers in year_data.items():
            print(f"  Processing trigger group: {trigger_group}")
            
            for trigger_name, json_path in triggers.items():
                resolved_path = resolve_config_path(json_path, str(config_dir))
                json_file = Path(resolved_path)
                
                if not json_file.exists():
                    print(f"    Warning: JSON file not found: {json_file}")
                    continue
                
                # Avoid processing the same file multiple times
                file_key = str(json_file)
                if file_key in processed_files:
                    print(f"    Skipping already processed file: {json_file.name}")
                    continue
                processed_files.add(file_key)
                
                print(f"    Processing: {trigger_name} -> {json_file.name}")
                
                try:
                    prescale_json = load_prescale_json(json_file)
                    prescale_info = parse_prescale_data(prescale_json)
                    
                    # Group prescale entries by HLT path
                    for entry in prescale_info:
                        hlt_path = entry['hlt_path']
                        results[year][trigger_group][hlt_path].append(entry)
                    
                    print(f"      Found {len(prescale_info)} prescale entries")
                    
                except Exception as e:
                    print(f"      Error processing {json_file}: {e}")
                    continue
    
    # Calculate averages and format output
    output_data = {"HLT_triggers_prescales": {}}
    
    print(f"\nCalculating averages...")
    
    for year in sorted(results.keys()):
        output_data["HLT_triggers_prescales"][year] = {}
        print(f"\nYear {year}:")
        
        for trigger_group in sorted(results[year].keys()):
            output_data["HLT_triggers_prescales"][year][trigger_group] = {}
            print(f"  {trigger_group}:")
            
            for hlt_path in sorted(results[year][trigger_group].keys()):
                prescale_entries = results[year][trigger_group][hlt_path]
                avg_prescale = calculate_weighted_average(prescale_entries)
                
                # Round to reasonable precision
                if avg_prescale == int(avg_prescale):
                    avg_prescale = int(avg_prescale)
                else:
                    avg_prescale = round(avg_prescale, 3)
                
                output_data["HLT_triggers_prescales"][year][trigger_group][hlt_path] = avg_prescale
                
                print(f"    {hlt_path}: {avg_prescale} (from {len(prescale_entries)} entries)")
    
    # Save to file
    if output_path is None:
        output_path = "average_prescales.yaml"
    
    output_path = Path(output_path)
    
    with open(output_path, 'w') as f:
        yaml.dump(output_data, f, default_flow_style=False, sort_keys=False, 
                 allow_unicode=True, width=1000)
    
    print(f"\nYAML output saved to: {output_path}")
    
    # Also print to console for immediate viewing
    print(f"\nGenerated YAML content:")
    print("=" * 80)
    yaml_str = yaml.dump(output_data, default_flow_style=False, sort_keys=False, 
                        allow_unicode=True, width=1000)
    print(yaml_str)

def main():
    parser = argparse.ArgumentParser(description="Generate YAML with average prescale factors by year and HLT path")
    parser.add_argument("--config", default="mutag_calib/configs/params/triggers_prescales_run3.yaml",
                       help="Path to triggers prescales YAML config file")
    parser.add_argument("--output", "-o", default="average_prescales.yaml",
                       help="Output YAML file path")
    
    args = parser.parse_args()
    
    generate_prescale_yaml(args.config, args.output)

if __name__ == "__main__":
    main()
