#!/usr/bin/env python

"""
Interactive prescale analysis script.

This script provides more detailed analysis capabilities for trigger prescale factors,
including visualization and specific queries.
"""

import os
import json
import yaml
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

def load_and_parse_all_prescales(config_path):
    """Load and parse all prescale data from the configuration."""
    
    config_path = Path(config_path)
    config_dir = config_path.parent
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    hlt_triggers_prescales = config.get("HLT_triggers_prescales", {})
    all_data = []
    
    for year, year_data in hlt_triggers_prescales.items():
        for trigger_group, triggers in year_data.items():
            for trigger_name, json_path in triggers.items():
                resolved_path = json_path.replace("${config_dir:}", str(config_dir))
                json_file = Path(resolved_path)
                
                if not json_file.exists():
                    continue
                
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    
                    # Parse the correctionlib JSON structure
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
                                    
                                    if isinstance(weight_data, (int, float)):
                                        all_data.append({
                                            'year': year,
                                            'trigger_group': trigger_group,
                                            'trigger_name': trigger_name,
                                            'run': run_number,
                                            'hlt_path': hlt_path,
                                            'lumi_start': 1,
                                            'lumi_end': float('inf'),
                                            'weight': float(weight_data),
                                            'lumi_range_size': float('inf')
                                        })
                                    elif isinstance(weight_data, dict) and weight_data.get("nodetype") == "binning":
                                        edges = weight_data["edges"]
                                        content = weight_data["content"]
                                        
                                        for i, weight in enumerate(content):
                                            lumi_start = edges[i]
                                            lumi_end = edges[i+1] if i+1 < len(edges) else float('inf')
                                            lumi_range_size = lumi_end - lumi_start if lumi_end != float('inf') else float('inf')
                                            
                                            all_data.append({
                                                'year': year,
                                                'trigger_group': trigger_group,
                                                'trigger_name': trigger_name,
                                                'run': run_number,
                                                'hlt_path': hlt_path,
                                                'lumi_start': lumi_start,
                                                'lumi_end': lumi_end,
                                                'weight': float(weight),
                                                'lumi_range_size': lumi_range_size
                                            })
                
                except Exception as e:
                    print(f"Error processing {json_file}: {e}")
    
    return pd.DataFrame(all_data)

def analyze_run_range(df, run_start, run_end):
    """Analyze prescales for a specific run range."""
    mask = (df['run'] >= run_start) & (df['run'] <= run_end)
    subset = df[mask]
    
    if len(subset) == 0:
        print(f"No data found for run range {run_start}-{run_end}")
        return None
    
    print(f"\n{'='*60}")
    print(f"ANALYSIS FOR RUN RANGE {run_start} - {run_end}")
    print(f"{'='*60}")
    print(f"Total entries: {len(subset)}")
    print(f"Unique runs: {subset['run'].nunique()}")
    print(f"Run numbers: {sorted(subset['run'].unique())}")
    
    # Average by HLT path in this range
    path_avg = subset.groupby('hlt_path')['weight'].agg(['mean', 'std', 'min', 'max', 'count'])
    print(f"\nAverage prescales by HLT path:")
    for path, stats in path_avg.iterrows():
        print(f"  {path}:")
        print(f"    Mean: {stats['mean']:.4f} ± {stats['std']:.4f}")
        print(f"    Min: {stats['min']:.4f}, Max: {stats['max']:.4f}")
        print(f"    Count: {stats['count']}")
    
    # Prescale distribution
    print(f"\nPrescale value distribution:")
    value_counts = subset['weight'].value_counts().sort_index()
    for weight, count in value_counts.items():
        percentage = 100 * count / len(subset)
        print(f"  Weight {weight:g}: {count} entries ({percentage:.1f}%)")
    
    return subset

def analyze_luminosity_sections(df):
    """Analyze prescale patterns by luminosity section ranges."""
    print(f"\n{'='*60}")
    print(f"LUMINOSITY SECTION ANALYSIS")
    print(f"{'='*60}")
    
    # Group by lumi range size
    finite_ranges = df[df['lumi_range_size'] != float('inf')]
    if len(finite_ranges) > 0:
        print(f"\nLumi section range size statistics:")
        print(f"  Mean range size: {finite_ranges['lumi_range_size'].mean():.2f}")
        print(f"  Median range size: {finite_ranges['lumi_range_size'].median():.2f}")
        print(f"  Min range size: {finite_ranges['lumi_range_size'].min():.0f}")
        print(f"  Max range size: {finite_ranges['lumi_range_size'].max():.0f}")
        
        # Binning by range size
        ranges_bins = [1, 10, 50, 100, 500, 1000, float('inf')]
        finite_ranges['range_bin'] = pd.cut(finite_ranges['lumi_range_size'], 
                                           bins=ranges_bins, right=False, include_lowest=True)
        range_analysis = finite_ranges.groupby('range_bin')['weight'].agg(['mean', 'count'])
        
        print(f"\nPrescales by lumi section range size:")
        for range_bin, stats in range_analysis.iterrows():
            print(f"  {range_bin}: mean={stats['mean']:.4f}, count={stats['count']}")
    
    # Count entries with infinite ranges (constant prescales for entire run)
    inf_count = len(df[df['lumi_range_size'] == float('inf')])
    print(f"\nEntries with constant prescale for entire run: {inf_count}")

def create_prescale_plots(df, output_dir):
    """Create visualization plots for prescale analysis."""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    plt.style.use('default')
    
    # 1. Prescale distribution histogram
    plt.figure(figsize=(10, 6))
    plt.hist(df['weight'], bins=50, alpha=0.7, edgecolor='black')
    plt.xlabel('Prescale Weight')
    plt.ylabel('Frequency')
    plt.title('Distribution of Prescale Weights')
    plt.yscale('log')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'prescale_distribution.png', dpi=150)
    plt.close()
    
    # 2. Prescales by run number
    if df['run'].nunique() > 1:
        plt.figure(figsize=(12, 6))
        run_avg = df.groupby('run')['weight'].mean()
        plt.plot(run_avg.index, run_avg.values, 'o-', alpha=0.7)
        plt.xlabel('Run Number')
        plt.ylabel('Average Prescale Weight')
        plt.title('Average Prescale Weight by Run Number')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'prescales_by_run.png', dpi=150)
        plt.close()
    
    # 3. Prescales by HLT path
    if df['hlt_path'].nunique() > 1:
        plt.figure(figsize=(12, 8))
        path_data = df.groupby('hlt_path')['weight'].agg(['mean', 'std'])
        
        x_pos = range(len(path_data))
        plt.errorbar(x_pos, path_data['mean'], yerr=path_data['std'], 
                    fmt='o', capsize=5, capthick=2)
        plt.xlabel('HLT Path')
        plt.ylabel('Average Prescale Weight')
        plt.title('Average Prescale Weight by HLT Path')
        plt.xticks(x_pos, path_data.index, rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'prescales_by_hlt_path.png', dpi=150)
        plt.close()
    
    print(f"Plots saved to: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Interactive prescale analysis")
    parser.add_argument("--config", default="mutag_calib/configs/params/triggers_prescales_run3.yaml",
                       help="Path to triggers prescales YAML config file")
    parser.add_argument("--run-start", type=int, help="Start of run range to analyze")
    parser.add_argument("--run-end", type=int, help="End of run range to analyze")
    parser.add_argument("--output-dir", "-o", default="prescale_plots",
                       help="Output directory for plots")
    parser.add_argument("--plot", action="store_true", help="Generate plots")
    
    args = parser.parse_args()
    
    # Load all prescale data
    print("Loading prescale data...")
    df = load_and_parse_all_prescales(args.config)
    
    if len(df) == 0:
        print("No prescale data found!")
        return
    
    print(f"Loaded {len(df)} prescale entries")
    print(f"Run range: {df['run'].min()} - {df['run'].max()}")
    print(f"Years: {sorted(df['year'].unique())}")
    print(f"HLT paths: {sorted(df['hlt_path'].unique())}")
    
    # Overall statistics
    print(f"\nOVERALL STATISTICS:")
    print(f"  Mean prescale: {df['weight'].mean():.4f}")
    print(f"  Std prescale: {df['weight'].std():.4f}")
    print(f"  Zero prescale fraction: {(df['weight'] == 0).mean():.4f}")
    print(f"  Unique prescale values: {sorted(df['weight'].unique())}")
    
    # Run range analysis if specified
    if args.run_start and args.run_end:
        analyze_run_range(df, args.run_start, args.run_end)
    
    # Luminosity section analysis
    analyze_luminosity_sections(df)
    
    # Generate plots if requested
    if args.plot:
        create_prescale_plots(df, args.output_dir)

if __name__ == "__main__":
    main()
