import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi.responses import FileResponse
import openai
import tiktoken
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from llmtoolkit.llm_interface.llm_interface import LLMInterface
from llmtoolkit.services.code_interpreter_service.code_interpreter_service import CodeInterpreterService
from llmtoolkit.services.esios_service.esios_service import EsiosService
from llmtoolkit.services.gmail_service.gmail_service import GmailService
from llmtoolkit.services.jira_service.jira_service import JiraService
from llmtoolkit.services.web_search_service.web_search_service import WebSearchService

# Load environment variables
load_dotenv()

# Constants
MAX_TOOL_CALLS = 5
MODEL_NAME = os.getenv("OPENAI_MODEL")
DEFAULT_ASSISTANT_MESSAGE = "Hello! I am your assistant, here to help you with Jira tasks, web searches and email management. How can I assist you today?"


class Config:
    """Application configuration."""
    CORS_ORIGINS = ["*"]  # Configure as needed
    CORS_CREDENTIALS = True
    CORS_METHODS = ["*"]
    CORS_HEADERS = ["*"]

class UserInput(BaseModel):
    """Input model for user messages."""
    messages: List

class APIResponse(BaseModel):
    """Standard API response model."""
    messages: List
    status: str = "success"
    error: Optional[str] = None

class LlmAgent:
    """Main agent class handling web search and LLM interactions."""

    def __init__(self):
        """Initialize the Web Search Agent with necessary services."""
        # Initialize services
        jira_service = JiraService(
            server=os.getenv("JIRA_DOMAIN"),
            username=os.getenv("JIRA_USERNAME"),
            api_token=os.getenv("JIRA_API_TOKEN")
        )
        web_search_service = WebSearchService()
        gmail_service = GmailService(credentials_path=os.getenv("GMAIL_CREDENTIALS_PATH"))
        esios_service = EsiosService(api_token=os.getenv("ESIOS_API_TOKEN"))
        code_interpreter_service = CodeInterpreterService()
        self.llm_service_interface = LLMInterface([web_search_service, jira_service, gmail_service, esios_service])
        #self.llm_service_interface = LLMInterface([esios_service,code_interpreter_service ])
        self.tools_schemas = self.llm_service_interface.get_function_schemas()
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Get agent system messages
        jira_agent_system_message = jira_service.get_agent_system_message()
        web_search_agent_system_message = web_search_service.get_agent_system_message()
        gmail_agent_system_message = gmail_service.get_agent_system_message()
        esios_agent_system_message = esios_service.get_agent_system_message()
        code_interpreter_system_message = code_interpreter_service.get_agent_system_message()

        self.system_message = (
            "You are an assistant capable of helping users with Jira tasks and performing web searches.\n\n"
            #"You are an assistant capable of helping users with ESIOS questions.\n\n"
            f"{jira_agent_system_message}\n\n"
            f"{web_search_agent_system_message}\n\n"
            f"{gmail_agent_system_message}\n\n"
            #f"{esios_agent_system_message}\n\n"
            #f"{code_interpreter_system_message}\n\n"
            #f"To PLOT an image, include the path of the image such as this <[PLOT][caption]:image path> in your message. EJ: <[PLOT][Solar energy generation for 2024]:plots/plot_20241202_23713.png>\n"
            #f"It needs to be <[PLOT][caption]:image path> or the image will not be displayed."
        )

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a given text.

        Args:
            text (str): Text to count tokens for

        Returns:
            int: Number of tokens
        """
        if not text:
            return 0
        try:
            encoding = tiktoken.encoding_for_model(MODEL_NAME)
            return len(encoding.encode(text))
        except Exception as e:
            print(f"Error counting tokens: {e}")
            return 0

    def convert_message_to_dict(self, message: Any) -> Dict:
        """Convert an OpenAI message object to a dictionary."""
        if isinstance(message, dict):
            return message

        message_dict = {
            "role": message.role,
            "content": message.content
        }

        # Handle tool calls if present
        if hasattr(message, 'tool_calls') and message.tool_calls:
            message_dict['tool_calls'] = [
                {
                    "id": tool_call.id,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    },
                    "type": tool_call.type
                }
                for tool_call in message.tool_calls
            ]

        return message_dict

    async def process_tool_calls(self, messages: List[Dict], assistant_message: Any) -> tuple[List, List]:
        """Process tool calls from assistant message.

        Args:
            messages (List[Dict]): Current message history
            assistant_message: Assistant's response message

        Returns:
            tuple[List, List]: Updated messages and response messages
        """
        response_messages = []

        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
                result = self.llm_service_interface.handle_function(function_name, params=arguments)
            except Exception as e:
                result = f"Error processing tool call: {str(e)}"
                print(f"Tool call error: {e}")

            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": str(result)
            }
            messages.append(tool_message)
            response_messages.append(tool_message)

        return messages, response_messages

    async def process_message(self, messages: List[Dict]) -> List[Dict]:
        """Process a message through the LLM and handle any tool calls.

        Args:
            messages (List[Dict]): Message history

        Returns:
            List[Dict]: New messages to add to the conversation
        """
        response_messages = []
        call_counter = 0

        while call_counter < MAX_TOOL_CALLS:
            try:
                response = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    tools=self.tools_schemas,
                    tool_choice="auto",
                )

                assistant_message = response.choices[0].message
                messages.append(assistant_message)
                response_messages.append(self.convert_message_to_dict(assistant_message))
                #response_messages.append(assistant_message)

                if not assistant_message.tool_calls:
                    break

                messages, new_responses = await self.process_tool_calls(messages, assistant_message)
                response_messages.extend(new_responses)

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}") from e

            call_counter += 1

        return response_messages

# Initialize FastAPI app and agent
app = FastAPI(title="Web Search Agent API", version="1.0.0")
agent = LlmAgent()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=Config.CORS_CREDENTIALS,
    allow_methods=Config.CORS_METHODS,
    allow_headers=Config.CORS_HEADERS,
)

@app.post("/start_conversation", response_model=APIResponse)
async def start_conversation():
    """Initialize a new conversation."""
    try:
        messages = [
            {"role": "system", "content": agent.system_message},
            {"role": "assistant", "content": DEFAULT_ASSISTANT_MESSAGE}
        ]
        print("CONVERSATION STARTED")
        return APIResponse(messages=messages)
    except Exception as e:
        return APIResponse(messages=[], status="error", error=str(e))

@app.post("/send_message", response_model=APIResponse)
async def send_message(user_input: UserInput):
    """Process a message from the user.

    Args:
        user_input (UserInput): User's input message and conversation history

    Returns:
        APIResponse: Response containing new messages
    """
    try:
        response_messages = await agent.process_message(user_input.messages)
        return APIResponse(messages=response_messages)
    except Exception as e:
        return APIResponse(messages=[], status="error", error=str(e))

@app.get("/plots/{image_name}")
async def get_image(image_name: str):
    """Serve a specific image file."""
    image_path = Path("plots") / image_name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
