#!/bin/sh

#
# A factory for creating shell wrapper functions that can interact with shell state.
#
# This function is intended to be sourced into a running shell, not executed directly.
#
# It dynamically generates and defines a new shell function. The generated
# function executes a specified command, captures its output, and then either
# 'eval's the output if it's prefixed with 'EVAL::' or prints it.
#
# Usage (after sourcing):
#   create_shell_wrapper <new_function_name> <command_to_execute...>
#
create_shell_wrapper() {
  # 1. Input Validation: Ensure we have at least a name and a command.
  if [ "$#" -lt 2 ]; then
    printf 'Usage: create_shell_wrapper <function_name> <command...>\n' >&2
    return 1
  fi

  local function_name="$1"
  shift # Discard the function name, the rest of the arguments are the command.

  # 2. Securely Quote the Command:
  local command_quoted
  printf -v command_quoted '%q ' "$@"

  # 3. Define the Function Body using a Here Document (heredoc):
  local function_body
  function_body=$(
    cat <<'EOF'
  local output
  local exit_code

  # Execute the command, passing along any arguments given to this wrapper function.
  output=$(__COMMAND_TO_RUN__ "$@")
  exit_code=$?

  if [ $exit_code -ne 0 ]; then
    return $exit_code
  fi

  if [[ "$output" == EVAL::* ]]; then
    local commands="${output#EVAL::}"
    eval "$commands"
  elif [ -n "$output" ]; then
    printf '%s\n' "$output"
  fi
  
  return $?
EOF
  )

  # 4. Inject the Quoted Command into the Template:
  function_body="${function_body/__COMMAND_TO_RUN__/$command_quoted}"

  # 5. Create the Final Function:
  eval "${function_name}() { ${function_body}; }"
}

# Prints the logical path to a file/directory without expanding symlinks.
function logpath() {
  printf '%s/%s\n' "$PWD" "$1"
}
