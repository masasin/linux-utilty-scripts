#!/bin/bash

input="$1"
suffix="${2:-letter}"

# Check if input file is provided and exists
if [[ -z "$input" || ! -f "$input" ]]; then
  echo "Usage: $0 filename.pdf [suffix]"
  exit 1
fi

# Get the base name (without .pdf)
basename="${input%.pdf}"

# Set the output filename
output="${basename}_${suffix}.pdf"

# Run pdftk to extract the first page
pdftk "$input" cat 1 output "$output"

echo "$output"
