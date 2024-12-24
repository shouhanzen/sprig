from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer
from textual.binding import Binding
from .terminal import TerminalEmulator
from .logging_config import setup_logging
import argparse
from .ai_completer import AICompleter

logger = setup_logging()

class SprigApp(App[None]):
    CSS = """
    #terminal-container {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+c,ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear", "Clear", show=True),
    ]

    def __init__(self, model_name: str = "anthropic-sonnet"):
        super().__init__()
        self.terminal = TerminalEmulator(model_name=model_name)
        logger.info("SprigApp initialized")

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="terminal-container"):
            yield self.terminal
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        logger.debug("App mounted")
        self.terminal.focus()

    def on_ready(self) -> None:
        """Handle app ready."""
        logger.debug("App ready")
        self.terminal.focus()

    def action_clear(self):
        logger.debug("Clear action triggered")
        self.terminal.clear()

def main():
    parser = argparse.ArgumentParser(description="Sprig Terminal Emulator")
    parser.add_argument(
        "--model", 
        choices=list(AICompleter.MODELS.keys()),
        default="anthropic-sonnet",
        help="AI model to use for command completion"
    )
    args = parser.parse_args()
    
    app = SprigApp(model_name=args.model)
    app.run()

if __name__ == "__main__":
    main()
