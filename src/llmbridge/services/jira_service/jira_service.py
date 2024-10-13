import logging
from typing import Any, Dict, Optional

from jira import JIRA, resources
from pydantic import BaseModel, Field

from llmbridge.llm_interface.utils import expose_for_llm

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


jira_agent_system_message = """**System Message: Jira Agent LLM**
You are an intelligent assistant designed to help users manage and navigate their Jira projects efficiently. Your primary functions include creating, updating, and retrieving information about issues, projects, and workflows within Jira. Please adhere to the following guidelines while interacting with users:

1. **Understand User Intent**: Carefully analyze user queries to accurately determine their needs. Ask clarifying questions if necessary to ensure you understand the request.

2. **Perform Searches and Actions**: In cases where a task requires additional information, leverage your ability to perform searches and actions. Utilize your comprehensive understanding of Jira to fetch and relay the necessary information or take appropriate actions within the system.

3. **Provide Accurate Information**: Use your knowledge of Jira's functionalities to provide precise and relevant information. Ensure that your responses are up-to-date with the latest Jira features and best practices.

4. **Facilitate Task Management**: Assist users in creating, updating, and managing Jira issues, including tasks, bugs, and stories. Guide them through the process of setting priorities, assigning tasks, and tracking progress.

5. **Enhance Productivity**: Offer tips and best practices for using Jira effectively. Suggest ways to optimize workflows and improve project management efficiency.

6. **Maintain User Privacy**: Respect user privacy and confidentiality. Do not request or store any sensitive information beyond what is necessary to fulfill the user's request.

7. **Be Polite and Professional**: Communicate in a courteous and professional manner. Ensure that your language is clear, concise, and free of jargon unless the user is familiar with technical terms.

By following these guidelines, you will provide valuable assistance to users, helping them to effectively manage their projects and achieve their goals using Jira.
"""

# TODO: Give it the ability to add more fields if needed
class CreateIssueModel(BaseModel):
    summary: str = Field(..., description="Summary of the issue")
    project_key: str = Field(..., description="Key of the Jira project")
    issue_type: str = Field("Task", description="Type of the issue")
    description: Optional[str] = Field(None, description="Description of the issue")

class AddCommentModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue")
    comment_body: str = Field(..., description="Body of the comment")

class TransitionIssueModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue")
    transition_name: str = Field(..., description="Name of the transition")

class SearchModel(BaseModel):
    jql: str = Field(..., description="Jira Query Language query")
    start_at: int = Field(0, description="Index of the first issue to return")
    max_results: int = Field(0, description="Maximum number of issues to return")
    need_all_fields: bool = Field(False, description="If True, all fields will be returned. If False, only relevant fields will be returned. Only use while searching for a single issue.")

class AssignIssueModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue")
    assignee_name: str = Field(..., description="Name of the assignee. -1 will set it to Unnasigned.")

class AddLabelToIssueModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue")
    label: str = Field(..., description="Label to add to the issue")

class UpdateFieldToIssueModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue")
    field_name: str = Field(..., description="Name of the field to add")
    field_value: str = Field(..., description="Value of the field to add")

class JiraService:
    def __init__(self, server, username, api_token):
        """Initializes the connection to the Jira server."""
        self.jira = JIRA(server=server, basic_auth=(username, api_token))

    def _parse_issue(self, issue: resources.Issue) -> Dict[str, Any]:
        """Parses a Jira issue into a dictionary with only relevant fields."""
        return {
            'key': issue.key,
            'issuetype': issue.fields.issuetype,
            'summary': issue.fields.summary,
            'description': issue.fields.description,
            'status': issue.fields.status,
            'priority': issue.fields.priority,
            'project': issue.fields.project,
            'created': issue.fields.created,
            'assignee': issue.fields.assignee,
            'reporter': issue.fields.reporter,
            'comments': [{
                "body": c.body,
                "author": c.author,
                "created": c.created,
                "updated": c.updated,
                }
                for c in issue.fields.comment.comments],
        }

    # TODO: Find a way to make the output less verbose, maybe could be a good idea to have an exposed function to get \
    # all fields names from an issue and another to get the value of a specific field to avoid returning all fields \
    # in the response. One issue can have 3k tokens in the response while parsing the whole issue.
    def _parse_full_issue(self, issue: resources.Issue) -> dict:
        """Parses a Jira issue into a dictionary with all fields."""
        parsed_issue = {}
        parsed_issue['key'] = issue.key
        parsed_issue.update({field: issue.raw['fields'][field] for field in issue.raw['fields']})
        return parsed_issue

    def _parse_project(self, project: resources.Project) -> dict:
        """Parses a Jira project into a dictionary with only relevant fields."""
        return {
            'key': project.key,
            'name': project.name,
            'projectTypeKey': project.projectTypeKey,
        }

    #function to get user from the credentials
    def get_user(self) -> str:
        """Retrieves the user information in Jira."""
        try:
            user = self.jira.myself()
            return f"User information: {user}"
        except Exception as e:
            logger.error(f"Failed to get user information: {str(e)}")
            return f"Failed to get user information: {str(e)}"

    @expose_for_llm
    def get_projects(self) -> str:
        """Retrieves the list of projects in Jira."""
        try:
            projects = self.jira.projects()
            parsed_pojects = [self._parse_project(project) for project in projects]
            return f"Total projects: {len(parsed_pojects)}\nProjects:\n{str(parsed_pojects)}"
        except Exception as e:
            return f"Failed to get projects: {str(e)}"

    @expose_for_llm
    def search_issues(self, data: SearchModel) -> str:
        """Search for issues in Jira using JQL language and return relevant fields.

        Ej: status = "In Progress" AND assignee = currentUser().
        """
        issues = self.jira.search_issues(data.jql, startAt=data.start_at, maxResults=data.max_results)
        if data.need_all_fields:
            if len(issues) > 1:
                return "Too many issues found. Please search for a single issue to get all fields."
            parsed_issues = [self._parse_full_issue(issue) for issue in issues]
        else:
            parsed_issues = [self._parse_issue(issue) for issue in issues]
        return f"Total issues: {issues.total}\nIssues found:{len(parsed_issues)}\nIssues:\n{str(parsed_issues)}"

    @expose_for_llm
    def create_issue(self, data: CreateIssueModel) -> str:
        """Creates a new issue in Jira."""
        issue_dict = {
            'project': {'key': data.project_key},
            'summary': data.summary,
            'description': data.description or '',
            'issuetype': {'name': data.issue_type},
        }
        issue = self.jira.create_issue(fields=issue_dict)
        return f"Issue {issue.key} created successfully."

    @expose_for_llm
    def add_label_to_issue(self, data: AddLabelToIssueModel) -> str:
        """Adds a tag to a Jira issue."""
        issue = self.jira.issue(data.issue_key)
        issue.fields.labels.append(data.label)
        issue.update(fields={"labels": issue.fields.labels})
        return f"Tag '{data.label}' added to issue {data.issue_key}."

    @expose_for_llm
    def update_field_of_issue(self, data: UpdateFieldToIssueModel) -> str:
        """Adds a field to a Jira issue."""
        issue = self.jira.issue(data.issue_key)
        # TODO: Check if the field exists, if not it will raise an exception
        #issue.fields.__dict__[data.field_name] = data.field_value
        issue.update(fields={data.field_name: {"name": data.field_value}})
        return f"Field '{data.field_name}' added to issue {data.issue_key}."

    @expose_for_llm
    def get_issue_types(self) -> str:
        """Retrieves the list of issue types in Jira."""
        issue_types = self.jira.issue_types()
        #TODO: Add a better way to parse the issue types
        return f"Total issue types: {len(issue_types)}\nIssue types:\n{str(issue_types)}"

    @expose_for_llm
    def assign_issue(self, data: AssignIssueModel) -> str:
        """Assigns an issue to a user."""
        self.jira.assign_issue(data.issue_key, data.assignee_name)
        return f"Issue {data.issue_key} assigned to {data.assignee_name}."

    @expose_for_llm
    def get_priorities(self) -> str:
        """Retrieves the list of priorities in Jira."""
        priorities = self.jira.priorities()
        return f"Total priorities: {len(priorities)}\nPriorities:\n{str(priorities)}"

    @expose_for_llm
    def add_comment(self, data: AddCommentModel) -> str:
        """Adds a comment to a Jira issue."""
        self.jira.add_comment(data.issue_key, data.comment_body)
        return f"Comment added to issue {data.issue_key}."

    @expose_for_llm
    def transition_issue(self, data: TransitionIssueModel) -> str:
        """Transitions a Jira issue to a new status."""
        transitions = self.jira.transitions(data.issue_key)
        transition_id = next(
            (t['id'] for t in transitions if t['name'].lower() == data.transition_name.lower()),
            None
        )
        if transition_id:
            self.jira.transition_issue(data.issue_key, transition_id)
            return f"Issue {data.issue_key} transitioned to '{data.transition_name}'."
        else:
            available_transitions = [t['name'] for t in transitions]
            return f"Transition '{data.transition_name}' not found for issue {data.issue_key}. Available transitions:\
                  {', '.join(available_transitions)}."