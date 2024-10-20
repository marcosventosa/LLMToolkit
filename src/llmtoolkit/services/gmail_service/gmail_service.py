import base64
import json
import logging
import os
import re
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
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
    attachments: Optional[List[str]] = Field(None, description="List of file paths for attachments.")

class DraftEmailModel(EmailMessageModel):
    """Inherits all fields from EmailMessageModel for creating drafts."""

class ReplyEmailModel(BaseModel):
    message_id: str = Field(..., description="The ID of the message to reply to.")
    body: str = Field(..., description="The reply message body.")
    send: bool = Field(False, description="Set to True to send the reply immediately, False to create a draft. Defaults to False.")

class ReadInboxModel(BaseModel):
    max_results: int = Field(10, description="The maximum number of emails to retrieve. Default is 10.")
    query: Optional[str] = Field(None, description="A query string to filter emails (e.g., 'is:unread').")
    label_ids: Optional[List[str]] = Field(None, description="List of label IDs to filter emails (e.g., ['INBOX', 'UNREAD']).")

class SendDraftModel(BaseModel):
    draft_id: str = Field(..., description="The ID of the draft email to send.")

class ForwardEmailModel(BaseModel):
    message_id: str = Field(..., description="The ID of the message to forward.")
    to_recipients: List[str] = Field(..., description="Email addresses to forward the email to.")
    body: Optional[str] = Field("", description="Additional message to include when forwarding.")
    send: bool = Field(False, description="Set to True to send the reply immediately, False to create a draft. Defaults to False.")

class ModifyEmailModel(BaseModel):
    message_id: str = Field(..., description="The ID of the message to modify.")
    mark_as_read: Optional[bool] = Field(None, description="Set to True to mark as read, False to mark as unread.")

class GmailService:
 
    TOKEN_PATH = "creds/gmail_token.json"

    def __init__(self, credentials_path: str):
        """Initializes the GmailService with OAuth 2.0 credentials."""
        self.credentials_path = credentials_path
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/gmail.modify',
        ]
        self.creds = self._authenticate()
        self.service = build('gmail', 'v1', credentials=self.creds)

    def _authenticate(self) -> Credentials:
        """Authenticates with Gmail API and returns the credentials."""
        creds = None
        # Load existing credentials
        if os.path.exists(self.TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(self.TOKEN_PATH, self.scopes)
        # If credentials are invalid or don't exist, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.scopes)
                creds = flow.run_local_server(port=0)
            # Save the credentials for future use
            with open(self.TOKEN_PATH, 'w') as token_file:
                token_file.write(creds.to_json())
        return creds

    def get_agent_system_message(self) -> str:
        """Returns the system message for the Gmail Assistant."""
        system_message = """You are an assistant capable of managing Gmail emails on behalf of the user.

**Your Objectives:**

1. **Understand User Requests:** Carefully interpret user instructions related to sending emails, drafting emails, replying, forwarding, reading emails, or managing the mailbox.

2. **Provide Clear Responses:** Present information in a clear and concise manner, ensuring that any sensitive data is handled appropriately.

3. **Handle Errors Gracefully:** If an error occurs or more information is needed, communicate this politely to the user.

**Instructions:**

- If additional information is needed to perform a function, ask the user for clarification.
- Do not include unnecessary information or perform actions outside of the provided functionalities.
- Focus on being accurate, helpful, and efficient in assisting the user with email management.
"""
        return system_message

    @expose_for_llm
    def send_email(self, data: EmailMessageModel) -> str:
        """Sends an email message on behalf of the user."""
        message = self._create_message(
            to_recipients=data.to_recipients,
            subject=data.subject,
            body=data.body,
            cc_recipients=data.cc_recipients,
            bcc_recipients=data.bcc_recipients,
            attachments=data.attachments,
        )
        sent_message = self.service.users().messages().send(userId='me', body=message).execute()
        return f"Email sent successfully. Message ID: {sent_message['id']}"

    @expose_for_llm
    def create_draft(self, data: DraftEmailModel) -> str:
        """Creates an email draft."""
        message = self._create_message(
            to_recipients=data.to_recipients,
            subject=data.subject,
            body=data.body,
            cc_recipients=data.cc_recipients,
            bcc_recipients=data.bcc_recipients,
            attachments=data.attachments,
        )
        draft = {'message': message}
        created_draft = self.service.users().drafts().create(userId='me', body=draft).execute()
        return f"Draft created successfully. Draft ID: {created_draft['id']}"

    def _create_message(self, to_recipients, subject, body, cc_recipients=None, bcc_recipients=None, attachments=None):
        """Creates a MIME message for an email."""
        message = MIMEMultipart()
        message['To'] = ', '.join(to_recipients)
        message['Subject'] = subject
        if cc_recipients:
            message['cc'] = ', '.join(cc_recipients)
        if bcc_recipients:
            message['bcc'] = ', '.join(bcc_recipients)

        # Add the email body
        message.attach(MIMEText(body, 'plain'))

        # Attach files
        if attachments:
            for file_path in attachments:
                part = MIMEBase('application', 'octet-stream')
                with open(file_path, 'rb') as file:
                    part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(file_path)}"')
                message.attach(part)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}

    # TODO: Format date better (E.g., convert to local timezone, Now is "Sun, 20 Oct 2024 04:10:46 -0700")
    @expose_for_llm
    def read_inbox(self, data: ReadInboxModel) -> str:
        """Retrieves emails from the inbox based on the provided parameters."""
        query_params = {
            'userId': 'me',
            'maxResults': data.max_results,
        }
        if data.query:
            query_params['q'] = data.query
        if data.label_ids:
            query_params['labelIds'] = data.label_ids

        messages_result = self.service.users().messages().list(**query_params).execute()
        messages = messages_result.get('messages', [])
        if not messages:
            return "No emails found."
        formatted_messages = ''
        for msg in messages:
            msg_detail = self.service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = {header['name']: header['value'] for header in msg_detail['payload']['headers']}
            formatted_messages += (
                f"Message ID: {msg['id']}\n"
                f"From: {headers.get('From', 'Unknown')}\n"
                f"To: {headers.get('To', 'Unknown')}\n"
                f"Subject: {headers.get('Subject', 'No Subject')}\n"
                f"Date: {headers.get('Date', '')}\n\n"
                f"Body: {msg_detail['snippet']}\n\n"
            )
        return formatted_messages

    @expose_for_llm
    def reply_email(self, data: ReplyEmailModel) -> str:
        """Replies to an existing email."""
        original_message = self.service.users().messages().get(userId='me', id=data.message_id, format='full').execute()
        thread_id = original_message['threadId']
        headers = original_message['payload']['headers']
        subject = ''
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
                if not subject.startswith('Re:'):
                    subject = 'Re: ' + subject
                break
        reply_to = ''
        for header in headers:
            if header['name'] == 'From':
                #find  email with regex
                email_match = re.search(r'[\w\.-]+@[\w\.-]+', header['value'])
                if email_match:
                    email = email_match.group(0)
                else:
                    raise ValueError("No email found in the 'From' header.")
                reply_to = email
                break

        message = MIMEMultipart()
        message['To'] = reply_to
        message['Subject'] = subject
        message['In-Reply-To'] = original_message['id']
        message['References'] = original_message['id']
        message.attach(MIMEText(data.body, 'plain'))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw_message, 'threadId': thread_id}

        if data.send:
            sent_message = self.service.users().messages().send(userId='me', body=body).execute()
            return f"Reply sent successfully. Message ID: {sent_message['id']}"
        else:
            draft = {'message': body}
            created_draft = self.service.users().drafts().create(userId='me', body=draft).execute()
            return f"Reply draft created successfully. Draft ID: {created_draft['id']}"

    @expose_for_llm
    def forward_email(self, data: ForwardEmailModel) -> str:
        """Forwards an existing email."""
        original_message = self.service.users().messages().get(userId='me', id=data.message_id, format='full').execute()
        thread_id = original_message['threadId']
        headers = original_message['payload']['headers']
        subject = ''
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
                if not subject.startswith('Fwd:'):
                    subject = 'Fwd: ' + subject
                break

        message = MIMEMultipart()
        message['To'] = ', '.join(data.to_recipients)
        message['Subject'] = subject
        message.attach(MIMEText(data.body, 'plain'))

        # TODO:Include original message as attachment
        # original_raw = base64.urlsafe_b64decode(json.dumps(original_message))
        # attachment = MIMEBase('message', 'rfc822')
        # attachment.set_payload(original_raw)
        # encoders.encode_base64(attachment)
        # attachment.add_header('Content-Disposition', 'attachment', filename='forwarded_message.eml')
        # message.attach(attachment)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw_message, 'threadId': thread_id}

        if data.send:
            sent_message = self.service.users().messages().send(userId='me', body=body).execute()
            return f"Email forwarded successfully. Message ID: {sent_message['id']}"
        else:
            draft = {'message': body}
            created_draft = self.service.users().drafts().create(userId='me', body=draft).execute()
            return f"Forward draft created successfully. Draft ID: {created_draft['id']}"

    @expose_for_llm
    def send_draft(self, data: SendDraftModel) -> str:
        """Sends a draft email specified by draft_id."""
        sent_message = self.service.users().drafts().send(
            userId='me',
            body={'id': data.draft_id}
        ).execute()
        return f"Draft email sent successfully. Message ID: {sent_message['id']}"

    @expose_for_llm
    def delete_email(self, message_id: str) -> str:
        """Deletes an email."""
        self.service.users().messages().delete(userId='me', id=message_id).execute()
        return f"Email with ID {message_id} deleted successfully."

    @expose_for_llm
    def modify_email(self, data: ModifyEmailModel) -> str:
        """Modifies an email's labels (e.g., mark as read or unread)."""
        mods = {}
        if data.mark_as_read is not None:
            if data.mark_as_read:
                mods['removeLabelIds'] = ['UNREAD']
            else:
                mods['addLabelIds'] = ['UNREAD']

        if not mods:
            return "No modifications specified."

        modified_message = self.service.users().messages().modify(userId='me', id=data.message_id, body=mods).execute()
        status = "marked as read" if data.mark_as_read else "marked as unread"
        return f"Email with ID {data.message_id} has been {status}."

    @expose_for_llm
    def list_labels(self) -> str:
        """Lists the labels in the user's mailbox."""
        results = self.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        if not labels:
            return "No labels found."
        formatted_labels = ''
        for label in labels:
            formatted_labels += f"Label ID: {label['id']}, Name: {label['name']}\n"
        return formatted_labels
