#!/bin/bash

# Usage: run-or-raise <launch_command> [classpart]
# Example: run-or-raise firefox
#          run-or-raise brave-browser Brave-browser
#          run-or-raise alacritty

#!/bin/bash

LAUNCH_CMD="$1"
CLASS_PART="${2:-$1}"

if [ -z "$LAUNCH_CMD" ]; then
  echo "Usage: $0 <launch_command> [classpart]"
  exit 1
fi

WIN_ID=$(wmctrl -lx | awk -v class="$CLASS_PART" '
    {
        split($3, a, ".")
        lc_class = tolower(class)
        lc_a1 = tolower(a[1])
        lc_a2 = tolower(a[2])
        if (lc_a1 == lc_class || lc_a2 == lc_class) {
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
