# Useful utility scripts for Linux

- `run-or-raise`: Switch to an open window, or open the app if it's closed. Useful for keyboard shortcuts.
- `extract-cover`: Extract the first page (e.g., cover letter) from a pdf, and save it as `filename_letter.pdf` or specify another suffix.
- `dcr`: `run` a new docker container if it is not running, or `exec` into the running instance 

## Shell functions

These functions need to be sourced into the `.profile` or `.bashrc` etc.

- `create_shell_wrapper`: Generate a new shell function from an existing script or function. `eval`s output prefixed with `EVAL::`, or prints it verbatim otherwise.
- `logpath`: Find the logical path of a file, without expanding symlinks. Useful for linking to files in a note taking application.
