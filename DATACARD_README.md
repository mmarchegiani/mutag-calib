# Datacard Creation for MuTag Calibration

This script creates combine datacards from pocketcoffea output for the muon-tagging calibration analysis.

## Overview

The script `create_datacards.py` generates combine datacards following the structure defined in the fit templates configuration. It creates separate datacards for each combination of:
- **pt bins**: As defined in the calibration parameters
- **tagger working points**: For each tagger (e.g., particleNet_XbbVsQCD) and working point (L, M, T, XT, XXT)
- **pass/fail regions**: For each working point

## Process Definitions

The script automatically categorizes samples into processes based on their names:

### MC Processes:
- **light**: Samples ending with `_l` (light flavor jets)
- **c**: Samples ending with `_c` or `_cc` (charm jets) 
- **b**: Samples ending with `_b` or `_bb` (bottom jets) - treated as signal

### Data Process:
- **data_obs**: Samples starting with `DATA_`

## Usage

### Basic Usage:
```bash
python mutag_calib/scripts/create_datacards.py <input_coffea_file> [options]
```

### Using the helper script:
```bash
./run_create_datacards.sh <input_coffea_file> [output_directory]
```

### Command Line Options:
- `--output-dir, -o`: Output directory for datacards (default: `datacards`)
- `--variable`: Variable to use for the fit (default: `FatJetGood_msoftdrop`)
- `--years`: Years to include in the analysis (default: all Run3 years)

### Example:
```bash
# Create datacards from coffea output
python mutag_calib/scripts/create_datacards.py output.coffea --output-dir my_datacards

# Or using the helper script
./run_create_datacards.sh output.coffea my_datacards
```

## Output Structure

The script creates the following directory structure:

```
datacards/
├── combined_datacard.txt                    # Combined datacard for all categories
├── Pt-300toInf_msd40particleNet_XbbVsQCDpassLwp/
│   ├── datacard_Pt-300toInf_msd40particleNet_XbbVsQCDpassLwp.txt
│   └── templates_Pt-300toInf_msd40particleNet_XbbVsQCDpassLwp.root
├── Pt-300toInf_msd40particleNet_XbbVsQCDfailLwp/
│   ├── datacard_Pt-300toInf_msd40particleNet_XbbVsQCDfailLwp.txt
│   └── templates_Pt-300toInf_msd40particleNet_XbbVsQCDfailLwp.root
└── ... (for each pt bin and tagger working point combination)
```

Each category folder contains:
- `datacard_<category>.txt`: Individual datacard for the category
- `templates_<category>.root`: ROOT file with histograms for the fit

## Systematic Uncertainties

The script includes basic systematic uncertainties:
- **Luminosity**: 2.5% log-normal uncertainty on all MC processes
- **Pileup**: 1% log-normal uncertainty on all MC processes  
- **Light jet normalization**: 10% uncertainty on light flavor jets
- **Charm jet normalization**: 15% uncertainty on charm jets

You can modify the `define_systematics()` function to add more systematic uncertainties as needed.

## Configuration

The script automatically loads the same configuration parameters used in `fit_templates_Run3.py`:
- Taggers from `mutag_calibration.yaml`
- pt binning and working points for each year
- Mass cut value (msd = 40 GeV)

## Requirements

- pocket_coffea
- coffea
- ROOT (for histogram output)

Make sure you have the pocket_coffea environment activated before running the script.

## Notes

- The script follows the same category structure as defined in lines 97-108 of `fit_templates_Run3.py`
- Each pt bin and tagger working point combination gets its own folder with individual datacards
- The combined datacard can be used with the CMS Combine tool for the final fit
- Sample categorization is automatic based on naming conventions
