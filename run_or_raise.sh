#!/bin/bash

# Usage: run-or-raise <launch_command> [classpart]
# Example: run-or-raise firefox
#          run-or-raise brave-browser Brave-browser
#          run-or-raise alacritty

LAUNCH_CMD="$1"
CLASS_PART="${2:-$1}"

if [ -z "$LAUNCH_CMD" ]; then
    echo "Usage: $0 <launch_command> [classpart]"
    exit 1
fi

# Find a window whose class part (after the dot in the third column) matches CLASS_PART, case-insensitively
WIN_ID=$(wmctrl -lx | awk -v class="$CLASS_PART" '
    {
        split($3, a, ".")
        # Convert both to lowercase for case-insensitive match
        lc_class = tolower(class)
        lc_a2 = tolower(a[2])
        if (lc_a2 == lc_class) {
            print $1
            exit
        }
    }
')

if [ -n "$WIN_ID" ]; then
    wmctrl -ia "$WIN_ID"
else
    $LAUNCH_CMD &
fi
