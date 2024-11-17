import os
from typing import List, Dict
import streamlit as st
import requests

# Constants
API_URL = os.getenv("API_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 30
SYSTEM_ROLE = "system"
USER_ROLE = "user"
TOOL_ROLE = "tool"
ASSISTANT_ROLE = "assistant"

class APIClient:
    """Client for handling API communications."""
    def __init__(self, base_url: str):
        self.base_url = base_url

    def start_conversation(self) -> List[Dict]:
        response = requests.post(
            f"{self.base_url}/start_conversation",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()["messages"]

    def send_message(self, messages: List[Dict]) -> tuple[List[Dict], str, str]:
        response = requests.post(
            f"{self.base_url}/send_message",
            json={"messages": messages},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()["messages"], response.json().get("status"), response.json().get("error")


def init_session_state() -> None:
    """Initialize the session state if it doesn't exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def get_messages() -> List[Dict]:
    """Get the current message history.

    Returns:
        List[Dict]: The current message history
    """
    return st.session_state.messages


def add_message(role: str, content: str) -> None:
    """Add a message to the chat history.

    Args:
        role (str): The role of the message sender
        content (str): The message content
    """
    st.session_state.messages.append({"role": role, "content": content})


def send_message(api_client: APIClient, prompt: str) -> bool:
    """Send a message to the API and update the chat history.

    Args:
        api_client (APIClient): The API client instance
        prompt (str): The user's input message

    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    if not prompt.strip():
        st.warning("Please enter a non-empty message")
        return False

    try:
        with st.spinner("Processing your message..."):
            # Add user message to chat history
            add_message(USER_ROLE, prompt)

            # Send the entire message history to the server
            assistant_messages, status, error = api_client.send_message(get_messages())
            if status != "success":
                st.error(f"Failed to send message: {error}")
                return False
            st.session_state.messages.extend(assistant_messages)
            return True

    except requests.Timeout:
        st.error("Request timed out. Please try again.")
        return False
    except requests.RequestException as e:
        st.error(f"Failed to send message: {str(e)}")
        return False
    except KeyError:
        st.error("Invalid response format from server")
        return False


def display_chat_history() -> None:
    """Display the chat history in the Streamlit interface."""
    for message in get_messages():
        if message.get("role") in [USER_ROLE, ASSISTANT_ROLE] and message.get("content"):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])


def main() -> None:
    """Main application function."""
    # Set up the Streamlit app
    st.title("Web Search Agent")
    
    # Initialize session state and API client
    init_session_state()
    api_client = APIClient(API_URL)
    
    # Start a conversation if there are no messages
    if not get_messages():
        try:
            with st.spinner("Starting conversation..."):
                st.session_state.messages = api_client.start_conversation()
        except requests.RequestException as e:
            st.error(f"Failed to start conversation: {str(e)}")
            return

    # Display chat history
    display_chat_history()

    # Handle user input
    if prompt := st.chat_input("Ask something..."):
        with st.chat_message(USER_ROLE):
            st.markdown(prompt)
        
        success = send_message(api_client, prompt)
        
        # Display latest assistant response
        if success and get_messages():
            with st.chat_message(ASSISTANT_ROLE):
                st.markdown(get_messages()[-1]["content"])


if __name__ == "__main__":
    main()