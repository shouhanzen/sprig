import subprocess
import threading
import queue
import logging
import asyncio
from typing import Callable, Optional
import os
from .logging_config import setup_shell_logging

logger = setup_shell_logging()

class Shell:
    def __init__(self):
        logger.info("Shell initialized")
        self.process: Optional[subprocess.Popen] = None
        self.output_queue = queue.Queue()
        self.output_thread: Optional[threading.Thread] = None
        self.output_callback: Optional[Callable] = None
        self._event_loop = None

    def start(self, callback: Callable):
        """Start the shell process."""
        if self.process:
            return

        self.output_callback = callback
        self._event_loop = asyncio.get_event_loop()
        # Start cmd.exe with "cmd" as the first argument to ensure echo is enabled
        shell = os.environ.get('COMSPEC', 'cmd.exe')
        self.process = subprocess.Popen(
            [shell],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            universal_newlines=True,
            shell=True,
            env=os.environ
        )
        
        logger.info("Shell process started")
        
        # Start thread to read output
        self.output_thread = threading.Thread(target=self.read_output, daemon=True)
        self.output_thread.start()

    def read_output(self):
        """Read output from the shell process."""
        if not self.process:
            return

        buffer = ""
        try:
            while True:
                char = self.process.stdout.read(1)
                if not char:
                    break
                    
                buffer += char
                if char == '\n':
                    if buffer.strip():  # Only log non-empty lines
                        future = asyncio.run_coroutine_threadsafe(
                            self.output_callback(buffer.strip()),
                            self._event_loop
                        )
                        try:
                            # Wait for the callback to complete with a timeout
                            future.result(timeout=1.0)
                        except Exception as e:
                            logger.exception("Error in output callback")
                    buffer = ""
                    
        except Exception as e:
            logger.error(f"Error reading from shell: {str(e)}", exc_info=True)

    def write(self, text: str):
        """Write text to the shell process."""
        if self.process and self.process.stdin:
            try:
                logger.debug(f"Writing to shell: {text!r}")
                self.process.stdin.write(text)
                self.process.stdin.flush()
            except Exception as e:
                logger.error(f"Error writing to shell: {str(e)}")

    def send_interrupt(self):
        """Send interrupt signal to the shell process."""
        if self.process:
            logger.info("Sending interrupt signal")
            self.write("\x03\n")  # Ctrl+C

    def clear(self):
        """Clear the shell screen."""
        self.write("cls\n")

    def terminate(self):
        """Terminate the shell process."""
        if self.process:
            self.process.terminate()
            self.process = None
            self._event_loop = None
