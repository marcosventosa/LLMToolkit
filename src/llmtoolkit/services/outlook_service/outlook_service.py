import logging
import os
import threading
from typing import List, Optional

import msal
import requests
from pydantic import BaseModel, Field

from llmtoolkit.llm_interface.utils import expose_for_llm

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class EmailMessageModel(BaseModel):
    subject: str = Field(..., description="The subject of the email.")
    body: str = Field(..., description="The plain text body of the email.")
    to_recipients: List[str] = Field(..., description="A list of email addresses to send the email to.")
    cc_recipients: Optional[List[str]] = Field(None, description="A list of email addresses to CC.")
    bcc_recipients: Optional[List[str]] = Field(None, description="A list of email addresses to BCC.")

class ReadInboxModel(BaseModel):
    top: int = Field(10, description="The maximum number of emails to retrieve. Default is 10.")
    folder: str = Field('Inbox', description="The mail folder to read emails from (e.g., 'Inbox', 'Sent Items').")
    search_query: Optional[str] = Field(None, description="An OData query to filter emails (e.g., 'isRead eq false').")

class OutlookService:
    def __init__(self, client_id: str, tenant_id: str):
        """Initializes the OutlookService with Microsoft Graph API credentials."""
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.scope = ['User.Read', 'Mail.ReadWrite', 'Mail.Send']
        self.cache_lock = threading.Lock()
        self.cache = self._load_token_cache()
        self.access_token = self._authenticate()

    def _load_token_cache(self):
        """Loads the token cache from a file if it exists."""
        cache = msal.SerializableTokenCache()
        if os.path.exists("token_cache.bin"):
            with self.cache_lock:
                with open("token_cache.bin", "r") as f:
                    cache.deserialize(f.read())
        return cache

    def _save_token_cache(self):
        """Saves the token cache to a file."""
        if self.cache.has_state_changed:
            with self.cache_lock:
                with open("token_cache.bin", "w") as f:
                    f.write(self.cache.serialize())

    def _authenticate(self) -> str:
        """Authenticates with Microsoft Graph API using Device Code Flow and returns an access token."""
        app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            token_cache=self.cache  # Pass in the cache
        )

        result = None
        accounts = app.get_accounts()
        if accounts:
            # Attempt to acquire token silently
            result = app.acquire_token_silent(self.scope, account=accounts[0])

        if not result:
            # Use device code flow
            flow = app.initiate_device_flow(scopes=self.scope)
            if 'user_code' not in flow:
                raise Exception("Failed to initiate device flow. Check your client ID and tenant ID.")

            print(f"To authenticate, visit {flow['verification_uri']} and enter the code {flow['user_code']}.")

            # Wait for user to authenticate
            result = app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            # Save the cache before returning
            self._save_token_cache()
            return result["access_token"]
        else:
            error_message = result.get('error_description') or result.get('error')
            logger.error(f"Authentication failed: {error_message}")
            raise Exception(f"Authentication failed: {error_message}")

    def get_agent_system_message(self) -> str:
        """Returns the system message for the Outlook Assistant."""
        system_message = """You are an assistant capable of managing Outlook emails on behalf of the user.

**Your Objectives:**

1. **Understand User Requests:** Carefully interpret user instructions related to sending emails, reading emails, or managing the mailbox.

2. **Select Appropriate Functionality:** Choose the most suitable function to fulfill the user's request:
   - `send_email`: To compose and send an email.
   - `read_inbox`: To read emails from a mail folder.
   - `list_mail_folders`: To list the mail folders in the user's mailbox.

3. **Utilize Provided Functions:** Use the functions effectively by supplying the appropriate parameters based on the user's request.

4. **Provide Clear Responses:** Present information in a clear and concise manner, ensuring that any sensitive data is handled appropriately.

5. **Handle Errors Gracefully:** If an error occurs or more information is needed, communicate this politely to the user.

**Instructions:**

- Use the parameter descriptions to include necessary details in your function calls.
- If additional information is needed to perform a function, ask the user for clarification.
- Do not include unnecessary information or perform actions outside of the provided functionalities.
- Focus on being accurate, helpful, and efficient in assisting the user with email management.

By following these objectives and instructions, you will effectively assist users in managing their Outlook emails.
"""
        return system_message

    #@expose_for_llm
    def send_email(self, data: EmailMessageModel) -> str:
        """Sends an email message on behalf of the user."""
        try:
            endpoint = 'https://graph.microsoft.com/v1.0/me/sendMail'
            headers = {'Authorization': f'Bearer {self.access_token}', 'Content-Type': 'application/json'}
            email_data = {
                "message": {
                    "subject": data.subject,
                    "body": {
                        "contentType": "Text",
                        "content": data.body
                    },
                    "toRecipients": [{"emailAddress": {"address": addr}} for addr in data.to_recipients],
                    "ccRecipients": [{"emailAddress": {"address": addr}} for addr in data.cc_recipients or []],
                    "bccRecipients": [{"emailAddress": {"address": addr}} for addr in data.bcc_recipients or []],
                },
                "saveToSentItems": "true"
            }

            response = requests.post(endpoint, headers=headers, json=email_data)
            if response.status_code == 202:
                return "Email sent successfully."
            else:
                logger.error(f"Failed to send email: {response.text}")
                return f"An error occurred while sending the email: {response.text}"
        except Exception as e:
            logger.error(f"Exception in send_email: {str(e)}")
            return f"An error occurred: {str(e)}"

    @expose_for_llm
    def read_inbox(self, data: ReadInboxModel) -> str:
        """Retrieves emails from a specified mail folder.

        Returns:
            str: Formatted string containing the email details.
        """
        try:
            # Construct the endpoint URL
            endpoint = f'https://graph.microsoft.com/v1.0/me/mailFolders/{data.folder}/messages?$top={data.top}'

            # Add search query if provided
            if data.search_query:
                endpoint += f"&$filter={data.search_query}"

            #endpoint += '&$select=from,subject,receivedDateTime,bodyPreview'

            headers = {'Authorization': f'Bearer {self.access_token}'}

            response = requests.get(endpoint, headers=headers)
            if response.status_code == 200:
                messages = response.json().get('value', [])
                if not messages:
                    return f"No emails found in the {data.folder} folder."
                formatted_messages = ''
                for msg in messages:
                    formatted_messages += (
                        f"From: {msg.get('from', {}).get('emailAddress', {}).get('name', 'Unknown')}\n"
                        f"Subject: {msg.get('subject', 'No Subject')}\n"
                        f"Received: {msg.get('receivedDateTime', '')}\n"
                        f"Body Preview: {msg.get('bodyPreview', '')}\n\n"
                    )
                return formatted_messages
            else:
                logger.error(f"Failed to retrieve emails: {response.text}")
                return f"An error occurred while retrieving emails: {response.text}"
        except Exception as e:
            logger.error(f"Exception in read_inbox: {str(e)}")
            return f"An error occurred: {str(e)}"

    @expose_for_llm
    def list_mail_folders(self) -> str:
        """Lists the mail folders in the user's mailbox."""
        try:
            endpoint = 'https://graph.microsoft.com/v1.0/me/mailFolders?$select=displayName,totalItemCount,unreadItemCount'
            headers = {'Authorization': f'Bearer {self.access_token}'}

            response = requests.get(endpoint, headers=headers)
            if response.status_code == 200:
                folders = response.json().get('value', [])
                if not folders:
                    return "No mail folders found."
                formatted_folders = ''
                for folder in folders:
                    formatted_folders += (
                        f"Folder Name: {folder.get('displayName', 'Unknown')}\n"
                        f"Total Items: {folder.get('totalItemCount', 0)}\n"
                        f"Unread Items: {folder.get('unreadItemCount', 0)}\n\n"
                    )
                return formatted_folders
            else:
                logger.error(f"Failed to retrieve mail folders: {response.text}")
                return f"An error occurred while retrieving mail folders: {response.text}"
        except Exception as e:
            logger.error(f"Exception in list_mail_folders: {str(e)}")
            return f"An error occurred: {str(e)}"
