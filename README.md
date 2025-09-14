# Useful utility scripts for Linux

- `run-or-raise`: Switch to an open window, or open the app if it's closed. Useful for keyboard shortcuts.
- `extract-cover`: Extract the first page (e.g., cover letter) from a pdf, and save it as `filename_letter.pdf` or specify another suffix.
- `dcr`: `run` a new docker container if it is not running, or `exec` into the running instance 

## Terminal UIs
- `convert-images`: Convert images from any format to png, jpeg, webp, or gif. Requires ImageMagick to be installed.

## Shell functions

These functions need to be sourced into the `.profile` or `.bashrc` etc.
I am doing it by sourcing from `~/.local/lib/shell-functions.sh` if that exists, so soft-link it there:

```bash
cd ~/.local/lib
ln -s <path/to/this/folder/shell-functions.sh> .

```

- `create_shell_wrapper`: Generate a new shell function from an existing script or function. `eval`s output prefixed with `EVAL::`, or prints it verbatim otherwise.
- `logpath`: Find the logical path of a file, without expanding symlinks. Useful for linking to files in a note taking application.
