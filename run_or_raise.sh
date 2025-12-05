#!/bin/bash

# Usage: run-or-raise <launch_command> [classpart]
# Example: run-or-raise firefox
#          run-or-raise brave-browser Brave-browser
#          run-or-raise alacritty

# $1: The launch command (now REQUIRED to be the Desktop File ID, e.g., 'brave-browser')
# $2: The class to search (defaults to $1)
LAUNCH_CMD="$1"
CLASS_PART="${2:-$1}"

if [ -z "$LAUNCH_CMD" ]; then
  echo "Usage: $0 <desktop_file_id> [classpart]"
  exit 1
fi

# 1. Search for the window ID using the class property.
WIN_ID=$(kdotool search --class "$CLASS_PART" 2>/dev/null | head -n 1)

if [ -n "$WIN_ID" ]; then
  # 2. Activate the found window.
  kdotool windowactivate "$WIN_ID"
else
  # 3. Launch the application using the KDE application launcher.
  # --application is the correct syntax confirmed by your analysis and the KDE bug tracker.
  kstart --application "$LAUNCH_CMD"
fi
