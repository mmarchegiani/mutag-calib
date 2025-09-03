#!/bin/bash

# Script to run the datacard creation
# Usage: ./run_create_datacards.sh <input_coffea_file> [output_directory]

set -e

# Check if input file is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_coffea_file> [output_directory]"
    echo "Example: $0 output.coffea datacards_output"
    exit 1
fi

INPUT_FILE=$1
OUTPUT_DIR=${2:-"datacards"}

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' does not exist"
    exit 1
fi

echo "Creating datacards from $INPUT_FILE"
echo "Output directory: $OUTPUT_DIR"

# Run the datacard creation script
python mutag_calib/scripts/create_datacards.py "$INPUT_FILE" --output-dir "$OUTPUT_DIR"

echo "Datacard creation completed!"
echo ""
echo "Generated structure:"
echo "  $OUTPUT_DIR/"
echo "  ├── combined_datacard.txt"
echo "  └── <category_folders>/"
echo "      ├── datacard_<category>.txt"
echo "      └── templates_<category>.root"
