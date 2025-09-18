#!/bin/bash

# Script to analyze trigger prescale factors
# Usage: ./run_prescale_analysis.sh [year] [trigger_group]

set -e

YEAR=${1:-"all"}
TRIGGER_GROUP=${2:-"all"}
OUTPUT_DIR="prescale_analysis_$(date +%Y%m%d_%H%M%S)"

echo "Running prescale analysis..."
echo "Year: $YEAR"
echo "Trigger group: $TRIGGER_GROUP"
echo "Output directory: $OUTPUT_DIR"

# Build command
CMD="python mutag_calib/scripts/analyze_prescales.py --output-dir $OUTPUT_DIR"

if [ "$YEAR" != "all" ]; then
    CMD="$CMD --year $YEAR"
fi

if [ "$TRIGGER_GROUP" != "all" ]; then
    CMD="$CMD --trigger-group $TRIGGER_GROUP"
fi

# Run the analysis
echo "Running command: $CMD"
$CMD

echo ""
echo "Analysis completed!"
echo "Results saved in: $OUTPUT_DIR"
echo ""
echo "Generated files:"
echo "  - prescale_raw_data.csv: All prescale entries"
echo "  - averages_by_hlt_path.csv: Average prescales by HLT path"
echo "  - averages_by_run.csv: Average prescales by run number"
echo "  - averages_by_run_and_path.csv: Average prescales by run and HLT path"
echo "  - overall_statistics.json: Overall statistics"
