from textual.widgets import Static
from textual.containers import ScrollableContainer
from textual.containers import Container
from textual.events import Key
from prompt_toolkit.history import InMemoryHistory
from rich.text import Text
from textual.app import ComposeResult
from .logging_config import setup_logging
from textual.reactive import reactive
import logging
import time
from typing import List
from .shell import Shell
from .autocomplete_client import AutocompleteClient
import asyncio

logger = setup_logging()

class TerminalEmulator(ScrollableContainer, can_focus=True):
    DEFAULT_CSS = """
    TerminalEmulator {
        background: #1e1e1e;
        color: #ffffff;
        padding: 1;
        height: 100%;
        border: solid $primary;
    }
    
    TerminalEmulator:focus {
        border: double $accent;
    }
    """

    current_input = reactive("")
    output_lines: List[str] = reactive([])
    suggestion: str = reactive("")
    cursor_visible = reactive(True)  # Track cursor visibility state

    def __init__(self, model_name: str = "anthropic-sonnet"):
        super().__init__()
        self.history = InMemoryHistory()
        self.cursor_position = 0
        self.command_history = []
        self._last_update_time = time.time()
        self.shell = Shell()
        self.autocomplete = AutocompleteClient(model_name)
        self.content = Static("")
        self._cursor_timer = None
        self._autocomplete_timer = None
        logger.info("Terminal emulator initialized")

    def compose(self) -> ComposeResult:
        """Compose the terminal widget."""
        yield self.content

    def on_mount(self) -> None:
        """Handle widget mount."""
        self.shell.start(self.handle_shell_output)
        self.focus()
        self.update_display()
        self._cursor_timer = self.set_interval(0.5, self._blink_cursor)
        self._autocomplete_timer = self.set_interval(0.2, self._check_for_autocomplete)

    def clear(self) -> None:
        """Clear the terminal output."""
        self.output_lines = []
        self.shell.clear()

    def watch_current_input(self) -> None:
        """Watch for changes in current_input."""
        self.suggestion = ""  # Clear suggestion when input changes
        self._request_display_update()

    def watch_output_lines(self) -> None:
        """Watch for changes in output lines."""
        self._request_display_update()

    def watch_suggestion(self) -> None:
        """Watch for changes in suggestion."""
        self._request_display_update()

    def _request_display_update(self) -> None:
        """Request a throttled display update."""
        current_time = time.time()
        if current_time - self._last_update_time > 0.016:  # ~60fps
            self.update_display()
            self._last_update_time = current_time

    def on_key(self, event: Key) -> None:
        """Handle key events."""
        event.prevent_default()
        event.stop()

        logger.debug(f"Keypress: {event.key}")
        
        if event.key == "ctrl+c":
            self.shell.send_interrupt()
            self.current_input = ""
            self.cursor_position = 0
            self.suggestion = ""
            self.autocomplete.cancel_pending()
        elif event.key == "left":
            if self.cursor_position > 0:
                self.cursor_position -= 1
                self.suggestion = ""
        elif event.key == "right":
            if self.cursor_position < len(self.current_input):
                self.cursor_position += 1
                self.suggestion = ""
        elif event.key == "tab":
            logger.debug("Tab pressed")
            logger.debug(self.suggestion)
            if self.suggestion:  # Accept suggestion if present
                self.current_input += self.suggestion
                self.cursor_position = len(self.current_input)  # Move cursor to end
                self.suggestion = ""
            else:  # Get new suggestion
                logger.debug("Tab pressed, requesting completion")
                self._check_for_autocomplete()
        elif event.key == "enter":
            if self.current_input:
                # Cancel any pending autocomplete
                self.autocomplete.cancel_pending()
                
                self.command_history.append(self.current_input)
                self.autocomplete.add_to_history(self.current_input)
                self.history.append_string(self.current_input)
                # Add command to output immediately for better responsiveness
                self.output_lines.append(f"> {self.current_input}")
                self.shell.write(f"{self.current_input}\n")
                self.current_input = ""
                self.cursor_position = 0
                self.suggestion = ""
                # Force refresh immediately after sending command
                self.update_display()
                self.refresh(layout=True)
        elif event.key == "backspace":
            if self.cursor_position > 0:
                self.current_input = (
                    self.current_input[:self.cursor_position - 1] +
                    self.current_input[self.cursor_position:]
                )
                self.cursor_position -= 1
        elif event.key == "space":  # Handle space key explicitly
            self.current_input = (
                self.current_input[:self.cursor_position] +
                " " +
                self.current_input[self.cursor_position:]
            )
            self.cursor_position += 1
        elif len(event.key) == 1:  # Single character
            self.current_input = (
                self.current_input[:self.cursor_position] +
                event.key +
                self.current_input[self.cursor_position:]
            )
            self.cursor_position += 1

    def _check_for_autocomplete(self) -> None:
        """Check if input has changed and request autocomplete if needed."""

        logger.debug(self.current_input, self.output_lines)

        self.autocomplete.check_for_autocomplete(self.current_input, self.output_lines)
        self.suggestion = self.autocomplete.suggestion

    def _blink_cursor(self) -> None:
        """Toggle the cursor visibility state."""
        self.cursor_visible = not self.cursor_visible
        self.update_display()

    def _get_current_line_with_cursor(self) -> Text:
        """Get the current input line with cursor."""
        before_cursor = self.current_input[:self.cursor_position]
        after_cursor = self.current_input[self.cursor_position + 1:]  # Skip current character
        
        line = Text()
        line.append(before_cursor, style="white")
        
        # Handle the character under cursor
        if self.cursor_position < len(self.current_input):
            # There is a character under cursor - highlight it
            cursor_char = self.current_input[self.cursor_position]
            if self.cursor_visible:
                line.append(cursor_char, style="black on white")
            else:
                line.append(cursor_char, style="white")
        else:
            # At the end of input - show block cursor
            if self.cursor_visible:
                line.append("█", style="white")
            else:
                line.append(" ", style="white")
                
        line.append(after_cursor, style="white")
        return line

    def update_display(self):
        """Update the terminal display."""
        # Create the display text
        content = Text()
        
        # Add output lines (show all lines)
        for line in self.output_lines:
            content.append(line + "\n", style="white")
        
        # Add current input with prompt
        content.append("> ", style="bold green")
        content.append(self._get_current_line_with_cursor())
        
        # Add suggestion if present
        if self.suggestion:
            content.append(self.suggestion, style="grey")
        
        # Update the content widget
        self.content.update(content)
        # Scroll to bottom
        self.scroll_end(animate=False)

    def on_unmount(self) -> None:
        """Clean up when widget is unmounted."""
        if self._cursor_timer:
            self._cursor_timer.stop()
        if self._autocomplete_timer:
            self._autocomplete_timer.stop()
        if self.shell:
            self.shell.terminate()

    async def handle_shell_output(self, line: str):
        """Handle output from the shell."""
        self.output_lines.append(line)
        # Limit output lines
        if len(self.output_lines) > 1000:
            self.output_lines = self.output_lines[-1000:]
        # Force refresh immediately
        self.update_display()
        # Request a layout refresh in case content size changed
        self.refresh(layout=True)
