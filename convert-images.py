#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "textual",
#   "textual-fspicker"
# ]
# ///

import shlex
import subprocess
from collections import deque
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, Vertical
from textual.events import Paste
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Label, RichLog, Select
from textual_fspicker import SelectDirectory


class ImageConversionApp(App):
    """A TUI for converting image files using ImageMagick."""

    CSS = """
    Screen {
        align: center middle;
    }

    #main_container {
        width: 80;
        border: heavy $primary;
        padding: 1;
        background: $surface;
    }

    #drop_zone {
        height: 5;
        border: dashed $secondary;
        text-align: center;
        padding-top: 1;
    }

    #format_select {
        width: 100%;
        margin-bottom: 1;
    }

    #execute_button {
        width: 100%;
    }

    #log_output {
        border: round $primary-lighten-2;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit App"),
        ("d", "toggle_dark_mode", "Toggle dark mode"),
    ]
    output_dir = reactive(Path.cwd(), init=False)

    def __init__(self) -> None:
        super().__init__()
        self.dropped_files: set[str] = set()
        self._themes = deque(["textual-dark", "textual-light"])

    def on_mount(self):
        self.title  = "Image Converter"
        self.theme = self._themes[0]

    def compose(self) -> ComposeResult:
        """Create and arrange the widgets for the application."""
        yield Header(show_clock=True)
        with Vertical(id="main_container"):
            yield Label("Drag and drop image files here", id="drop_zone")
            yield Select[str](
                [
                    ("PNG", "png"),
                    ("JPEG", "jpg"),
                    ("WebP", "webp"),
                    ("GIF", "gif"),
                ],
                prompt="Select Output Format",
                value="png",
                id="format_select",
            )

            yield Label(
                f"Output directory: {self.output_dir}",
                id="output_dir_str",
            )

            with HorizontalGroup(id="output_row"):
                yield Button(
                    "Select Output folder", id="select_output_button", variant="default"
                )

                yield Button(
                    "Execute Conversion",
                    variant="primary",
                    id="execute_button",
                    disabled=True,
                )
            yield RichLog(id="log_output", markup=True, wrap=True)
        yield Footer()

    @on(Paste)
    def process_dropped_files(self, event: Paste) -> None:
        """Handles the Paste event, processing dropped file paths."""
        log = self.query_one(RichLog)
        button = self.query_one("#execute_button", Button)

        added_files = set()

        lines = shlex.split(event.text)
        for line in lines:
            if not line:
                continue

            path = Path(line)
            if path.is_file():
                added_files.add(str(path))
            else:
                log.write(f"- [yellow]Ignoring invalid path:[/] {path}")

        if not added_files:
            return

        self.dropped_files |= added_files
        log.clear()
        log.write("\n[bold green]Files detected:[/]")
        for path_str in self.dropped_files:
            log.write(f"- {Path(path_str).name}")

        if self.dropped_files:
            button.disabled = False

    @work
    @on(Button.Pressed, "#select_output_button")
    async def select_output_button(self) -> None:
        """Selects output dir."""
        selected_path: Path | None = await self.push_screen_wait(
            SelectDirectory(
                title="Choose your desired directory",
                location=self.output_dir,
            )
        )

        if selected_path:
            self.output_dir = selected_path
            print(f"User selected: {selected_path}")
        else:
            self.notify("Folder selection cancelled.")

    @on(Button.Pressed, "#execute_button")
    def execute_button(self) -> None:
        """Handles the event when the 'Execute Conversion' button is pressed."""
        log = self.query_one(RichLog)
        format_select = self.query_one("#format_select", Select)
        button = self.query_one("#execute_button", Button)

        output_format = format_select.value
        if not self.dropped_files or output_format is None:
            log.write("[bold red]Error:[/] No files or no format selected.")
            return

        log.write(f"\n[bold]Starting conversion to {output_format.upper()}...[/]")

        for file_path_str in self.dropped_files:
            input_path = Path(file_path_str)
            output_filename = f"{input_path.stem}.{output_format}"
            output_path = self.output_dir / output_filename

            command = ["convert", str(input_path), str(output_path)]

            try:
                subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                log.write(
                    f"- [green]SUCCESS:[/] Converted {input_path.name} to {output_path.name}"
                )
            except FileNotFoundError:
                log.write(
                    "[bold red]FATAL ERROR:[/] The 'convert' command was not found."
                )
                log.write(
                    "Please ensure ImageMagick is installed and in your system's PATH."
                )
                return
            except subprocess.CalledProcessError as e:
                log.write(
                    f"- [bold red]FAILURE:[/] Could not convert {input_path.name}"
                )
                log.write(f"  [red]Stderr:[/] {e.stderr.strip()}")

        self.dropped_files.clear()
        button.disabled = True
        log.write("\n[bold]Conversion process finished.[/]")

    def watch_output_dir(self, old_dir: Path, new_dir: Path):
        self.query_one("#output_dir_str", Label).update(
            f"Output directory: {self.output_dir}"
        )

    def action_toggle_dark_mode(self):
        self._themes.rotate()
        self.theme = self._themes[0]


if __name__ == "__main__":
    app = ImageConversionApp()
    app.run()
