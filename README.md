# Useful utility scripts for Linux

- `run-or-raise`: Switch to an open window, or open the app if it's closed. Useful for keyboard shortcuts.
- `extract-cover`: Extract the first page (e.g., cover letter) from a pdf, and save it as `filename_letter.pdf` or specify another suffix.
- `dcr`: `run` a new docker container if it is not running, or `exec` into the running instance 
- `bt-switch`: Switch Bluetooth devices between computers connected via SSH, such as on a local network or a Tailnet.

  This needs to go in your `~/.config/bt_switch/config.toml`:

```toml
[devices.device-slug]
mac = "00:00:00:00:00:00"
name = "Device Name"

[hosts.host-1]
address = "host-1"
user = "username1"
protocol = "ssh"

[hosts.host-2]
address = "host-2"
user = "username2"
protocol = "ssh"

[defaults.host-1]
default_device = "device-slug"
default_target = "host-2"

[defaults.host-2]
default_device = "device-slug"
default_target = "host-1"
```


## Terminal UIs
- `convert-images`: Convert images from any format to png, jpeg, webp, or gif. Requires ImageMagick to be installed.

## URI Protocols
- `obsidian-silent`: Takes basic Obsidian `advanced-uri` commands and applies them via the Local REST API to avoid having Obsidian steal focus.

  Add a desktop file pointing to `obsidian-silent`, then register it with `update-desktop-database ~/.local/share/applications`

```toml
[Desktop Entry]
Name=Obsidian Silent
Exec=/home/<username>/.local/bin/obsidian-silent %u
Type=Application
Terminal=false
MimeType=x-scheme-handler/obsidian-silent;
NoDisplay=true
```

## Shell functions

These functions need to be sourced into the `.profile` or `.bashrc` etc.
I am doing it by sourcing from `~/.local/lib/shell-functions.sh` if that exists, so soft-link it there:

```bash
cd ~/.local/lib
ln -s <path/to/this/folder/shell-functions.sh> .

```

- `create_shell_wrapper`: Generate a new shell function from an existing script or function. `eval`s output prefixed with `EVAL::`, or prints it verbatim otherwise.
- `logpath`: Find the logical path of a file, without expanding symlinks. Useful for linking to files in a note taking application.
