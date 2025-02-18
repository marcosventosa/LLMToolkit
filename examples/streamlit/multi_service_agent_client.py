from dataclasses import dataclass
import os
from typing import List, Dict
import streamlit as st
import requests
import re

# Constants
API_URL = os.getenv("API_URL", "http://localhost:8002")
DEFAULT_TIMEOUT = 300
SYSTEM_ROLE = "system"
USER_ROLE = "user"
TOOL_ROLE = "tool"
ASSISTANT_ROLE = "assistant"

@dataclass
class MessageElement:
    type: str  # 'text' or 'image'
    content: str
    image_data: bytes = None
    caption: str = None

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

    def get_plot(self, image_path: str) -> bytes:
        response = requests.get(
            f"{self.base_url}/{image_path}",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.content


def init_session_state() -> None:
    """Initialize the session state if it doesn't exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def get_messages() -> List[Dict]:
    """Get the current message history."""
    return st.session_state.messages


def add_message(role: str, content: str) -> None:
    """Add a message to the chat history."""
    st.session_state.messages.append({"role": role, "content": content})


def process_message_content(content: str, api_client: APIClient) -> List[MessageElement]:
    """Process message content and return a list of text and image elements."""
    elements = []
    last_end = 0
    # Updated pattern to match <[PLOT][description]:path>
    image_pattern = r'<\[PLOT\]\[(.*?)\]:([^>]+)>'
    
    for match in re.finditer(image_pattern, content):
        # Add text before the image
        if match.start() > last_end:
            elements.append(MessageElement(
                type='text',
                content=content[last_end:match.start()]
            ))
        
        # Handle image
        description = match.group(1)
        image_path = match.group(2)
        try:
            image_data = api_client.get_plot(image_path)
            elements.append(MessageElement(
                type='image',
                content=image_path,
                image_data=image_data,
                caption=description
            ))
        except requests.RequestException as e:
            elements.append(MessageElement(
                type='text',
                content=f"[Failed to load image: {image_path}]"
            ))
            
        last_end = match.end()
    
    # Add remaining text
    if last_end < len(content):
        elements.append(MessageElement(
            type='text',
            content=content[last_end:]
        ))
    
    return elements


def send_message(api_client: APIClient, prompt: str) -> bool:
    """Send a message to the API and update the chat history."""
    if not prompt.strip():
        st.warning("Please enter a non-empty message")
        return False

    try:
        with st.spinner("Processing your message..."):
            add_message(USER_ROLE, prompt)
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



def display_chat_history(api_client: APIClient) -> None:
    """Display the chat history in the Streamlit interface."""
    for message in get_messages():
        if message.get("role") in [USER_ROLE, ASSISTANT_ROLE] and message.get("content"):
            with st.chat_message(message["role"]):
                elements = process_message_content(message["content"], api_client)
                for element in elements:
                    if element.type == 'text':
                        st.markdown(element.content)
                    elif element.type == 'image':
                        st.image(
                            element.image_data, 
                            caption=element.caption, 
                            use_container_width=True
                        )
def main() -> None:
    """Main application function."""
    st.title("LLM Agent")
    
    init_session_state()
    api_client = APIClient(API_URL)
    
    if not get_messages():
        try:
            with st.spinner("Starting conversation..."):
                st.session_state.messages = api_client.start_conversation()
        except requests.RequestException as e:
            st.error(f"Failed to start conversation: {str(e)}")
            return

    # Display chat history (excluding the last message if it's being processed)
    messages_to_display = get_messages()[:-1] if st.session_state.get('processing', False) else get_messages()
    for message in messages_to_display:
        if message.get("role") in [USER_ROLE, ASSISTANT_ROLE] and message.get("content"):
            with st.chat_message(message["role"]):
                elements = process_message_content(message["content"], api_client)
                for element in elements:
                    if element.type == 'text':
                        st.markdown(element.content)
                    elif element.type == 'image':
                        st.image(
                            element.image_data, 
                            caption=element.caption, 
                            use_container_width=True
                        )

    if prompt := st.chat_input("Ask something..."):
        st.session_state.processing = True
        with st.chat_message(USER_ROLE):
            st.markdown(prompt)

        success = send_message(api_client, prompt)

        if success and get_messages():
            with st.chat_message(ASSISTANT_ROLE):
                elements = process_message_content(get_messages()[-1]["content"], api_client)
                for element in elements:
                    if element.type == 'text':
                        st.markdown(element.content)
                    elif element.type == 'image':
                        st.image(
                            element.image_data, 
                            caption=element.caption, 
                            use_container_width=True
                        )
        
        st.session_state.processing = False
        st.rerun()


if __name__ == "__main__":
    main()