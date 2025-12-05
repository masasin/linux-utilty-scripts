#!/bin/bash

# Arguments:
# $1: The Desktop File ID (Launch ID)
# $2: The Kdotool Search String (optional)

# 1. Check for basic requirements (at least one argument)
if [ -z "$1" ]; then
  echo "Usage: $(basename "$0") <desktop_file_id> [\"<kdotool_search_string>\"]" >&2
  exit 1
fi

LAUNCH_ID="$1"
SEARCH_STRING=""

# 2. Determine Execution Path based on argument count
if [ "$#" -eq 1 ]; then
  # --- Case 1: Compatibility (ror cmd) ---
  # Default: Search by class using the Launch ID.
  SEARCH_STRING="--class $1"
elif [ "$#" -eq 2 ]; then
  # --- Check for Case 2 vs Case 3 ---
  # Check if the second argument contains a complex string (e.g., quotes, flags).
  # Simple check for hyphen or quote presence is the heuristic here.
  if [[ "$2" == -* ]] || [[ "$2" == *\"* ]] || [[ "$2" == *\'* ]]; then
    # --- Case 3: Complex Search (ror cmd "--title Google Gemini") ---
    # Search string is provided fully quoted.
    SEARCH_STRING="$2"
  else
    # --- Case 2: Simple Override (ror cmd custom-class) ---
    # The second argument is a simple class name.
    SEARCH_STRING="--class $2"
  fi
else
  # Handle scenarios with more than 2 arguments (unlikely, but fallback is Case 3)
  echo "Error: Too many arguments. Use single-quoted string for complex search." >&2
  exit 1
fi

# --- DEBUGGING OUTPUT (Final State) ---
echo "Final LAUNCH_ID: $LAUNCH_ID" >>"/tmp/kdo-debug.log"
echo "Final SEARCH_STRING: $SEARCH_STRING" >>"/tmp/kdo-debug.log"
# --- DEBUGGING OUTPUT (End) ---

# 3. Separate the Kdotool Search String into executable components
# We rely on 'read' to safely separate the flag and pattern from the SEARCH_STRING.
read -r SEARCH_FLAG SEARCH_PATTERN <<<"$SEARCH_STRING"

# Sanity check: If pattern is empty, default it to the ID.
if [ -z "$SEARCH_PATTERN" ]; then
  SEARCH_PATTERN="$LAUNCH_ID"
fi

# 4. Execution Logic
# Search for the window
WIN_ID=$(kdotool search "$SEARCH_FLAG" "$SEARCH_PATTERN" 2>>"/tmp/kdo-debug.log" | head -n 1)

if [ -n "$WIN_ID" ]; then
  kdotool windowactivate "$WIN_ID"
else
  # Launch using kstart --application
  kstart --application "$LAUNCH_ID" >/dev/null 2>&1
fi
