import os
import httpx
from dotenv import load_dotenv
from typing import List, Optional, Dict
import logging
import json
from .logging_config import setup_logging

load_dotenv()
logger = setup_logging()

class AICompleter:
    MODELS = {
        "anthropic-sonnet": {
            "id": "anthropic/claude-3.5-sonnet:beta",
            "description": "Anthropic Sonnet - Short responses, good for command completion"
        },
        "gpt-4o-mini": {
            "id": "openai/gpt-4o-mini",
            "description": "GPT-4o Mini - Fast and efficient for command completion"
        },
    }
    
    def __init__(self, model_name: str = "anthropic-sonnet"):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY environment variable is missing")
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
        if model_name not in self.MODELS:
            logger.error(f"Invalid model name: {model_name}")
            model_name = "anthropic-sonnet"  # Default to anthropic-sonnet
            
        self.model = self.MODELS[model_name]
        logger.info(f"AICompleter initialized with model: {model_name}")
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_completion(self, current_input: str, terminal_lines: List[str]):
        """Get AI-powered completion suggestions for the current input."""
        try:
            prompt = self._create_prompt(current_input, terminal_lines)
            logger.debug(f"Generated prompt: {prompt}")
            
            logger.debug(f"Making streaming request to {self.base_url} with model {self.model['id']}")
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model["id"],
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a helpful terminal assistant. Complete the user's command based on common terminal commands and their history. Provide only the completion, no explanation."
                            },
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 50,
                        "temperature": 0.3,
                        "stream": True
                    },
                    timeout=5.0
                ) as response:
                    logger.debug(f"Got initial response with status {response.status_code}")
                    if response.status_code != 200:
                        logger.error(f"API request failed with status {response.status_code}: {response.text}")
                        return

                    full_response = ""
                    chunk_count = 0
                    async for line in response.aiter_lines():
                        if not line or line.strip() == "":
                            continue
                        if line.startswith("data: "):
                            chunk_count += 1
                            line_content = line[6:].strip()  # Skip "data: " prefix
                            
                            # Handle stream completion message
                            if line_content == "[DONE]":
                                logger.debug("Received [DONE] message from stream")
                                break
                                
                            logger.debug(f"Processing chunk {chunk_count}: {line_content}")
                            try:
                                data = json.loads(line_content)
                                if data.get("choices") and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        content = delta["content"]
                                        full_response += content
                                        logger.debug(f"Current full response: {full_response}")

                                        suggestion = full_response.strip()
                                        if suggestion:
                                            logger.debug(f"Yielding suggestion: {suggestion}")
                                            yield suggestion
                            except json.JSONDecodeError as e:
                                if line_content != "[DONE]":  # Don't log error for expected [DONE] message
                                    logger.error(f"JSON decode error on chunk: {line_content} - {str(e)}")
                                continue
                            except Exception as e:
                                logger.error(f"Error processing stream chunk: {str(e)}")
                                continue

                    logger.debug(f"Stream completed. Processed {chunk_count} chunks")

        except httpx.ConnectTimeout:
            logger.error("Connection timeout while connecting to OpenRouter API")
            return
        except httpx.ReadTimeout:
            logger.error("Read timeout while streaming from OpenRouter API")
            return
        except Exception as e:
            logger.exception(f"Error getting completion: {str(e)}")
            return

    def _create_prompt(self, current_input: str, terminal_lines: List[str]) -> str:

        terminal_body = "\n".join(terminal_lines)

        """Create a prompt for the AI model."""
        logger.debug(f"Using terminal contents: {terminal_lines}")
        
        return f"""Terminal history:
{terminal_body}

Current input: {current_input}

Complete this command. Only return the completion part, nothing else. Do not explain. Do not wrap in quotes."""
