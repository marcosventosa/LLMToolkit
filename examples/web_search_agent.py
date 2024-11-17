import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import openai
import tiktoken
from dotenv import load_dotenv

from llmtoolkit.llm_interface.llm_interface import LLMInterface
from llmtoolkit.services.web_search_service.web_search_service import WebSearchService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExitCommands(str, Enum):
    """Valid exit commands for the chat interface."""
    EXIT = "exit"
    QUIT = "quit"

@dataclass
class TokenCount:
    """Track token usage throughout the conversation."""
    input_tokens: int = 0
    output_tokens: int = 0
    tool_tokens: int = 0

    @property
    def total(self) -> int:
        """Calculate total tokens used."""
        return self.input_tokens + self.output_tokens + self.tool_tokens

    def __str__(self) -> str:
        """Format token counts for display."""
        return (
            f"\nToken Usage Summary:\n"
            f"Input tokens: {self.input_tokens}\n"
            f"Output tokens: {self.output_tokens}\n"
            f"Tool tokens: {self.tool_tokens}\n"
            f"Total tokens: {self.total}"
        )

class WebSearchAgent:
    """Main agent class for handling web search interactions."""

    def __init__(self):
        """Initialize the Web Search Agent with necessary services and configurations."""
        load_dotenv()

        self.model = os.getenv("OPENAI_MODEL")
        if not self.model:
            raise ValueError("OPENAI_MODEL environment variable not set")

        self.web_search_service = WebSearchService()
        self.llm_service_interface = LLMInterface([self.web_search_service])
        self.tools_schemas = self.llm_service_interface.get_function_schemas()
        self.client = openai.OpenAI()
        self.system_prompt = self.web_search_service.get_agent_system_message()
        self.token_counter = TokenCount()
        self.messages: List[Dict] = []

        # Initialize tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
        except Exception as e:
            logger.error(f"Failed to initialize tokenizer: {e}")
            raise

    def count_tokens(self, text: Optional[str]) -> int:
        """Count tokens in the given text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens in the text
        """
        if not text:
            return 0
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            return 0

    async def process_tool_calls(self, assistant_message: Any) -> None:
        """Process tool calls from the assistant's message.

        Args:
            assistant_message: Message from the assistant containing tool calls
        """
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
                result = self.llm_service_interface.handle_function(function_name, params=arguments)
            except Exception as e:
                logger.error(f"Error processing tool call: {e}")
                result = f"Error: {str(e)}"

            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": result
            }
            self.messages.append(tool_message)
            self.token_counter.tool_tokens += self.count_tokens(result)

    async def process_message(self, user_input: str) -> str:
        """Process a user message and generate a response.

        Args:
            user_input: User's message

        Returns:
            Assistant's response
        """
        self.messages.append({"role": "user", "content": user_input})
        self.token_counter.input_tokens += self.count_tokens(user_input)

        call_counter = 0
        while call_counter < 5:
            call_counter += 1
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools_schemas,
                    tool_choice="auto",
                )

                assistant_message = response.choices[0].message
                self.messages.append(assistant_message)
                self.token_counter.output_tokens += self.count_tokens(assistant_message.content)

                if not assistant_message.tool_calls:
                    return assistant_message.content

                await self.process_tool_calls(assistant_message)

            except Exception as e:
                logger.error(f"Error in message processing: {e}")
                return f"I encountered an error: {str(e)}"

        return assistant_message.content  # Return the last response if max calls reached

    async def run(self):
        """Run the chat interface."""
        # Initialize conversation
        start_message = "Hello! I'm your Web Search Assistant, here to help you find information on the web. How can I assist you today?"
        self.messages.append({"role": "system", "content": self.system_prompt})
        self.messages.append({"role": "assistant", "content": start_message})

        self.token_counter.input_tokens += self.count_tokens(self.system_prompt)
        self.token_counter.output_tokens += self.count_tokens(start_message)

        print(f"Assistant: {start_message}\n")

        # Main conversation loop
        while True:
            user_input = input("You: ").strip()

            if user_input.lower() in [e.value for e in ExitCommands]:
                print("Goodbye!")
                break

            if not user_input:
                print("Please enter a message.")
                continue

            response = await self.process_message(user_input)
            print(f"Assistant: {response}\n")

        print(self.token_counter)

async def main():
    """Main entry point for the application."""
    try:
        agent = WebSearchAgent()
        await agent.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
