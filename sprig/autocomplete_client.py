from typing import List, Optional
import asyncio
import logging
from .ai_completer import AICompleter
from .logging_config import setup_logging

logger = setup_logging()

class AutocompleteClient:
    """Handles autocomplete functionality with task management and cancellation."""
    
    def __init__(self, terminal, model_name: str = "anthropic-sonnet"):
        """Initialize the autocomplete client."""
        logger.info(f"Initializing AutocompleteClient with model: {model_name}")
        self.ai_completer = AICompleter(model_name)
        self._current_task = None
        self._last_input = ""
        self._suggestion = ""
        self._suggestion_callback = None
        self.terminal = terminal
        
    @property
    def suggestion(self) -> str:
        """Get the current suggestion."""
        return self._suggestion
        
    def cancel_pending(self) -> None:
        """Cancel any pending autocomplete task."""
        if self._current_task and not self._current_task.done():
            logger.debug("Cancelling pending autocomplete task")
            self._current_task.cancel()
            self._current_task = None
            logger.debug("Task cancelled")
        else:
            logger.debug("No pending task to cancel")
        
    def set_suggestion_callback(self, callback) -> None:
        """Set the callback to be invoked when a suggestion is received."""
        self._suggestion_callback = callback
        
    async def get_suggestion(self, current_input: str, lines: list[str]) -> Optional[str]:
        """Get an autocomplete suggestion for the current input."""
        try:
            logger.debug(f"Getting suggestion for input: {current_input}")
            
            async for suggestion in self.ai_completer.get_completion(
                current_input,
                lines
            ):
                if suggestion:
                    # Only update suggestion and notify callback if task hasn't been cancelled
                    if not (self._current_task and self._current_task.cancelled()):
                        self._suggestion = suggestion
                        if self._suggestion_callback:
                            self._suggestion_callback(suggestion)
                        return suggestion
                    else:
                        logger.debug("Task was cancelled, discarding suggestion")
                        return None
            
            return None
        except Exception as e:
            logger.error(f"Error getting suggestion: {str(e)}", exc_info=True)
            self._suggestion = ""
            return None
            
    def check_for_autocomplete(self) -> None:
        """Check if input has changed and request autocomplete if needed."""
        current_input = '> ' + self.terminal.current_input
        lines = self.terminal.output_lines
        current_input = current_input.strip()
        
        if current_input == self._last_input:
            return
        
        # Log the state
        logger.debug(f"Checking autocomplete - Current input: '{current_input}', Last input: '{self._last_input}'")
            
            
        logger.debug("Input changed, requesting autocomplete")
        self._last_input = current_input
        
        # Cancel any existing task
        if self._current_task and not self._current_task.done():
            logger.debug("Cancelling existing task before starting new one")
            self.cancel_pending()
            
        # Create new task and store reference
        logger.debug("Creating new autocomplete task")
        self._current_task = asyncio.create_task(self.get_suggestion(current_input, lines))