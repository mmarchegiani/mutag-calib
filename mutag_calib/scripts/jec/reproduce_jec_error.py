#!/usr/bin/env python3
"""
Minimal example to reproduce JEC file error with Coffea for multiple files
Mimicking FactorizedJetCorrector logic to debug name and info variables
"""

import coffea
from coffea.jetmet_tools import CorrectedJetsFactory, JECStack
from coffea.lookup_tools import extractor
import gzip
import argparse
import os
import re
from pathlib import Path

def mimic_factorized_jet_corrector_parsing(evaluator_dict):
    """
    Mimic the FactorizedJetCorrector parsing logic to debug name and info variables
    Based on coffea v0.7.30 FactorizedJetCorrector.__init__
    """
    print("\n🔍 Mimicking FactorizedJetCorrector parsing logic...")
    
    # This mimics the logic from FactorizedJetCorrector.__init__
    for name, info in evaluator_dict.items():
        print(f"\n📋 Processing corrector:")
        print(f"   name: '{name}'")
        print(f"   info type: {type(info)}")
        print(f"   info: {info}")
        
        # Try to access the corrector info like FactorizedJetCorrector does
        try:
            if hasattr(info, 'signature'):
                print(f"   info.signature: {info.signature}")
            if hasattr(info, '_formula'):
                print(f"   info._formula: {info._formula}")
            if hasattr(info, '_bin_names'):
                print(f"   info._bin_names: {info._bin_names}")
            
        except Exception as e:
            print(f"   Error accessing info attributes: {e}")
        
        # The actual validation that causes the error
        # Based on typical JEC name validation patterns
        print(f"\n🧪 Testing name validation patterns:")
        
        # Pattern 1: Basic JEC name pattern (typical regex)
        # Usually something like: Campaign_Date_RunPeriod_Version_DataType_CorrectionLevel_JetAlgorithm
        basic_pattern = r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+_V\d+_[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+$'
        basic_match = re.match(basic_pattern, name)
        print(f"   Basic pattern match: {basic_match is not None}")
        if not basic_match:
            print(f"   Basic pattern: {basic_pattern}")
        
        # Pattern 2: More flexible pattern
        flexible_pattern = r'^[A-Za-z0-9_]+$'
        flexible_match = re.match(flexible_pattern, name)
        print(f"   Flexible pattern match: {flexible_match is not None}")
        
        # Pattern 3: Check for common problematic characters
        problematic_chars = re.findall(r'[^A-Za-z0-9_]', name)
        if problematic_chars:
            print(f"   ❌ Problematic characters found: {set(problematic_chars)}")
        else:
            print(f"   ✅ No problematic characters found")
        
        # Pattern 4: Check component count
        components = name.split('_')
        print(f"   Number of underscore-separated components: {len(components)}")
        print(f"   Components: {components}")
        
        # Expected JEC components analysis
        expected_components = [
            "Campaign (e.g., Summer22)",
            "Date (e.g., 22Sep2023)", 
            "Run Period (e.g., RunCD)",
            "Version (e.g., V2)",
            "Data Type (e.g., DATA/MC)",
            "Correction Level (e.g., L1FastJet, L2Relative)",
            "Jet Algorithm (e.g., AK8PFPuppi)"
        ]
        
        print(f"\n   📊 Component analysis:")
        for i, (component, expected) in enumerate(zip(components, expected_components)):
            print(f"     [{i}] '{component}' - {expected}")
        
        if len(components) < 6:
            print(f"   ⚠️  Warning: Expected at least 6 components, got {len(components)}")
        
        # Pattern 5: Version validation (common requirement)
        has_version = any('V' in comp and any(c.isdigit() for c in comp) for comp in components)
        print(f"   Version component present: {has_version}")
        
        # Pattern 6: Check for specific JEC validation that might be failing
        # This is the most likely culprit based on the error message
        print(f"\n   🎯 Likely validation checks:")
        
        # Check if name contains required elements
        required_elements = ['Summer22', 'DATA', 'V2']
        for element in required_elements:
            present = element in name
            print(f"     Contains '{element}': {present}")
        
        # Check correction level
        correction_levels = ['L1FastJet', 'L2Relative', 'L2Residual', 'L3Absolute', 'L2L3Residual', 'Uncertainty', 'UncertaintySources']
        found_levels = [level for level in correction_levels if level in name]
        print(f"     Found correction levels: {found_levels}")
        
        return name, info

def main():
    parser = argparse.ArgumentParser(description='Test JEC files with Coffea and debug name/info variables')
    parser.add_argument('--config-dir', type=str, required=True,
                       help='Path to configuration directory containing jec/Summer22/ subdirectory')
    args = parser.parse_args()
    
    print(f"Coffea version: {coffea.__version__}")
    print(f"Config directory: {args.config_dir}")
    
    # List of JEC files to test
    jec_files = [
        #"jec/Summer22/Summer22_22Sep2023_V2_MC_L1FastJet_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_V2_MC_L2L3Residual_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_V2_MC_L2Relative_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_V2_MC_L2Residual_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_V2_MC_L3Absolute_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_V2_MC_Uncertainty_AK8PFPuppi.junc.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_V2_MC_UncertaintySources_AK8PFPuppi.junc.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L1FastJet_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L2L3Residual_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L2Relative_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L2Residual_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_L3Absolute_AK8PFPuppi.jec.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_Uncertainty_AK8PFPuppi.junc.txt.gz",
        #"jec/Summer22/Summer22_22Sep2023_RunCD_V2_DATA_UncertaintySources_AK8PFPuppi.junc.txt.gz",
        #"jec/test/Summer22_22Sep2023_V2_DATA_L1FastJet_AK8PFPuppi.jec.txt.gz",
        "jec/Summer23/Summer23Prompt23_RunCv123_V3_DATA_L1FastJet_AK8PFPuppi.jec.txt.gz"
    ]
    
    # Convert relative paths to absolute paths
    full_paths = [os.path.join(args.config_dir, jec_file) for jec_file in jec_files]
    
    print(f"\nTesting {len(full_paths)} JEC files...\n")
    
    results = {}
    
    for i, jec_file_path in enumerate(full_paths, 1):
        jec_filename = os.path.basename(jec_file_path)
        print(f"=" * 100)
        print(f"Testing file {i}/{len(full_paths)}: {jec_filename}")
        print(f"Full path: {jec_file_path}")
        
        # Check if file exists
        if not os.path.exists(jec_file_path):
            print(f"❌ File not found: {jec_file_path}")
            results[jec_filename] = "File not found"
            continue
        
        try:
            # Step 1: Create extractor and load the file
            print("\n📝 Step 1: Creating extractor and loading file")
            ext = extractor()
            ext.add_weight_sets([f"* * {jec_file_path}"])
            ext.finalize()
            
            print("✅ Extractor created and finalized successfully")
            
            # Step 2: Get the evaluator dictionary (this is what gets passed to FactorizedJetCorrector)
            print("\n📝 Step 2: Creating evaluator")
            evaluator = ext.make_evaluator()
            print(f"✅ Evaluator created: {type(evaluator)}")
            
            # Step 3: Examine the evaluator contents (this is what FactorizedJetCorrector receives)
            print(f"\n📝 Step 3: Examining evaluator contents")
            if hasattr(evaluator, '_funcs'):
                funcs_dict = evaluator._funcs
                print(f"   _funcs dictionary keys: {list(funcs_dict.keys())}")
                print(f"   Number of functions: {len(funcs_dict)}")
                
                # This is the key step - mimic FactorizedJetCorrector parsing
                mimic_factorized_jet_corrector_parsing(funcs_dict)
                
            else:
                print("   Warning: evaluator doesn't have _funcs attribute")
                print(f"   Available attributes: {[attr for attr in dir(evaluator) if not attr.startswith('_')]}")
            
            # Step 4: Try to create JECStack (this is where the error occurs)
            if jec_file_path.endswith('.jec.txt.gz'):
                print(f"\n📝 Step 4: Attempting to create JECStack (where error occurs)")
                try:
                    jec_stack = JECStack(evaluator)
                    print("✅ JECStack created successfully!")
                    results[jec_filename] = "Success"
                except Exception as jec_error:
                    print(f"❌ JECStack creation failed: {jec_error}")
                    print(f"   Error type: {type(jec_error).__name__}")
                    results[jec_filename] = f"JECStack Error: {jec_error}"
            else:
                print(f"\n📝 Step 4: Skipping JECStack for uncertainty file")
                results[jec_filename] = "Success (uncertainty file)"
            
        except Exception as e:
            print(f"❌ General error: {e}")
            print(f"   Error type: {type(e).__name__}")
            results[jec_filename] = f"Error: {e}"
            
            # Print traceback for debugging
            import traceback
            print(f"   Traceback:")
            traceback.print_exc()
        
        print()  # Add blank line between files
    
    # Summary
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
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
        print("\n🔧 Debugging tips based on name/info analysis:")
        print("1. Check if the corrector names extracted from files match expected regex patterns")
        print("2. Look for non-alphanumeric characters or spaces in corrector names") 
        print("3. Verify that version components (V2, etc.) are properly formatted")
        print("4. Check if correction level names match expected JEC nomenclature")
        print("5. Examine file contents for any encoding or formatting issues")

if __name__ == "__main__":
    main()
