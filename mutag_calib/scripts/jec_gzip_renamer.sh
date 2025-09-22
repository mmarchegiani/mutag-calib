#!/usr/bin/env bash
# jec_gzip_subfolders.sh
# Compress JEC/JUNC .txt files in each "SummerXX*" subfolder
# Usage:
#   ./jec_gzip_subfolders.sh <PARENT_DIR> [--remove]
# Example:
#   ./jec_gzip_subfolders.sh mutag_calib/configs/params/jec --remove

set -euo pipefail

PARENT="${1:-}"
REMOVE_ORIG="no"

# check args
if [[ -z "$PARENT" ]]; then
  echo "Usage: $0 <PARENT_DIR> [--remove]" >&2
  exit 1
fi

if [[ "${2:-}" == "--remove" ]]; then
  REMOVE_ORIG="yes"
fi

# ensure parent exists
if [[ ! -d "$PARENT" ]]; then
  echo "Error: directory '$PARENT' not found." >&2
  exit 1
fi

# loop over subfolders inside parent
for SUBDIR in "$PARENT"/*/; do
  [[ -d "$SUBDIR" ]] || continue
  echo "Processing folder: $SUBDIR"

  shopt -s nullglob
  for file in "$SUBDIR"/*.txt; do
    [[ -f "$file" ]] || continue

    filename="$(basename -- "$file")"
    base="${filename%.txt}"

    # classify file
    if [[ "$filename" =~ [Uu]ncertainty ]]; then
      suffix="junc"
    else
      suffix="jec"
    fi

    out="${base}.${suffix}.txt.gz"
    outpath="${SUBDIR}${out}"

    if [[ -e "$outpath" ]]; then
      echo "  Skip (already exists): $outpath"
      continue
    fi

    if gzip -c -n -- "$file" > "$outpath"; then
      echo "  Created: $outpath"
      if [[ "$REMOVE_ORIG" == "yes" ]]; then
        rm -- "$file"
      fi
    else
      echo "  Error compressing: $file" >&2
      rm -f -- "$outpath" 2>/dev/null || true
    fi
  done
done

