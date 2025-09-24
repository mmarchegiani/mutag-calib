#!/usr/bin/env python3
"""
Minimal example to reproduce JEC file error with Coffea for multiple files
"""

import coffea
from coffea.jetmet_tools import CorrectedJetsFactory, JECStack
from coffea.lookup_tools import extractor
import gzip
import argparse
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Test JEC files with Coffea')
    parser.add_argument('--config-dir', type=str, required=True,
                       help='Path to configuration directory containing jec/Summer22/ subdirectory')
    args = parser.parse_args()
    
    print(f"Coffea version: {coffea.__version__}")
    print(f"Config directory: {args.config_dir}")
    
    # List of JEC files to test
    jec_files = [
        "jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L1FastJet_AK8PFPuppi.jec.txt.gz",
        "jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L2L3Residual_AK8PFPuppi.jec.txt.gz",
        "jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L2Relative_AK8PFPuppi.jec.txt.gz",
        "jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L2Residual_AK8PFPuppi.jec.txt.gz",
        "jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L3Absolute_AK8PFPuppi.jec.txt.gz",
        "jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_Uncertainty_AK8PFPuppi.junc.txt.gz",
        "jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_UncertaintySources_AK8PFPuppi.junc.txt.gz"
    ]
    
    # Convert relative paths to absolute paths
    full_paths = [os.path.join(args.config_dir, jec_file) for jec_file in jec_files]
    
    print(f"\nTesting {len(full_paths)} JEC files...\n")
    
    results = {}
    
    for i, jec_file_path in enumerate(full_paths, 1):
        jec_filename = os.path.basename(jec_file_path)
        print(f"=" * 80)
        print(f"Testing file {i}/{len(full_paths)}: {jec_filename}")
        print(f"Full path: {jec_file_path}")
        
        # Check if file exists
        if not os.path.exists(jec_file_path):
            print(f"❌ File not found: {jec_file_path}")
            results[jec_filename] = "File not found"
            continue
        
        try:
            # Method 1: Direct approach using extractor (most likely to reproduce the error)
            print("\n📝 Method 1: Using extractor directly")
            ext = extractor()
            ext.add_weight_sets([f"* * {jec_file_path}"])
            ext.finalize()
            
            # This should trigger the same error you're seeing for .jec files
            if jec_file_path.endswith('.jec.txt.gz'):
                jec_stack = JECStack(ext.make_evaluator())
                print("✅ Method 1: Success - JECStack created successfully")
                results[jec_filename] = "Success"
            else:
                print("ℹ️  Method 1: Skipping JECStack for .junc file (uncertainty file)")
                results[jec_filename] = "Success (uncertainty file)"
            
        except Exception as e:
            print(f"❌ Method 1: Error occurred - {e}")
            print(f"   Error type: {type(e).__name__}")
            results[jec_filename] = f"Error: {e}"

        try:
            # Method 2: Examine file contents
            print("\n📖 Method 2: Examining file contents")
            with gzip.open(jec_file_path, 'rt') as f:
                lines = f.readlines()
                
            print(f"   File has {len(lines)} lines")
            print("   First few lines:")
            for j, line in enumerate(lines[:3]):
                print(f"     Line {j+1}: {line.strip()}")
                
            # Look for the corrector name line
            print("\n   Looking for corrector name patterns:")
            corrector_lines_found = 0
            for j, line in enumerate(lines[:10]):  # Check first 10 lines
                if any(keyword in line.lower() for keyword in ['summer22', 'version', 'corrector', 'name']) or line.strip().startswith('{'):
                    print(f"     Line {j+1}: {line.strip()}")
                    corrector_lines_found += 1
                    
            if corrector_lines_found == 0:
                print("     No obvious corrector name patterns found in first 10 lines")
                
        except Exception as e:
            print(f"❌ Method 2: Error reading file - {e}")

        try:
            # Method 3: Extract corrector name from filename
            print("\n🔍 Method 3: Analyzing filename format")
            
            # Remove directory path and file extensions
            base_name = os.path.basename(jec_file_path)
            if base_name.endswith('.jec.txt.gz'):
                corrector_name = base_name.replace('.jec.txt.gz', '')
                file_type = "JEC correction"
            elif base_name.endswith('.junc.txt.gz'):
                corrector_name = base_name.replace('.junc.txt.gz', '')
                file_type = "JEC uncertainty"
            else:
                corrector_name = base_name
                file_type = "Unknown"
                
            print(f"   File type: {file_type}")
            print(f"   Extracted corrector name: {corrector_name}")
            
            # Check corrector name format
            parts = corrector_name.split('_')
            print(f"   Name parts: {parts}")
            print(f"   Number of parts: {len(parts)}")
            
            if len(parts) >= 6:
                print(f"   Campaign: {parts[0]}")
                print(f"   Date: {parts[1]}")  
                print(f"   Run period: {parts[2]}")
                print(f"   Version: {parts[3]}")
                print(f"   Data type: {parts[4]}")
                print(f"   Correction level: {parts[5]}")
                if len(parts) > 6:
                    print(f"   Jet algorithm: {parts[6]}")
            else:
                print("   ⚠️  Warning: Corrector name has fewer parts than expected")
                
        except Exception as e:
            print(f"❌ Method 3: Error analyzing filename - {e}")
        
        print()  # Add blank line between files
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    success_count = 0
    error_count = 0
    not_found_count = 0
    
    for filename, result in results.items():
        status_icon = "✅" if "Success" in result else "❌" if "Error" in result else "⚠️"
        print(f"{status_icon} {filename}: {result}")
        
        if "Success" in result:
            success_count += 1
        elif "Error" in result:
            error_count += 1
        elif "not found" in result:
            not_found_count += 1
    
    print(f"\nResults: {success_count} success, {error_count} errors, {not_found_count} not found")
    
    if error_count > 0:
        print("\n🔧 Troubleshooting tips:")
        print("1. Check if corrector names in files match expected format")
        print("2. Verify file integrity (try unzipping manually)")
        print("3. Check Coffea version compatibility with JEC file format")
        print("4. Look for any special characters or encoding issues in file names")

if __name__ == "__main__":
    main()
