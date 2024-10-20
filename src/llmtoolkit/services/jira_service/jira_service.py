import logging
from typing import Any, Dict, Optional

from jira import JIRA, resources
from pydantic import BaseModel, Field

from llmtoolkit.llm_interface.utils import expose_for_llm

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


# TODO: Give it the ability to add more fields if needed
class CreateIssueModel(BaseModel):
    summary: str = Field(..., description="Summary of the issue.")
    project_key: str = Field(..., description="Key of the Jira project (e.g., 'PROJ').")
    issue_type: str = Field("Task", description="Type of the issue (e.g., 'Task', 'Bug'...).")
    description: Optional[str] = Field(None, description="Detailed description of the issue.")

class AddCommentModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue (e.g., 'PROJ-123').")
    comment_body: str = Field(..., description="Content of the comment to add.")

class ChangeIssuePriorityModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue (e.g., 'PROJ-123').")
    priority_name: str = Field(..., description="New priority level (e.g., 'High', 'Medium'...).")

class TransitionIssueModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue (e.g., 'PROJ-123').")
    transition_name: str = Field(..., description="Name of the transition to apply (e.g., 'Done', 'In Progress'...).")

class SearchModel(BaseModel):
    jql: str = Field(..., description="Jira Query Language (JQL) string to search issues.")
    start_at: int = Field(0, description="Index of the first issue to return")
    max_results: int = Field(0, description="Maximum number of issues to return. Defaults to all issues.")
    need_all_fields: bool = Field(False, description="If True, all fields will be returned. If False, only relevant fields will be returned. Only use while searching for a single issue.")

class AssignIssueModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue (e.g., 'PROJ-123').")
    assignee_name: str = Field(..., description="Username of the assignee. Use '-1' to unassign.")

class AddLabelToIssueModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue (e.g., 'PROJ-123').")
    label: str = Field(..., description="Label to add to the issue.")

class UpdateFieldToIssueModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue (e.g., 'PROJ-123').")
    field_name: str = Field(..., description="Name of the field to add")
    field_value: str = Field(..., description="Value of the field to add")

class UpdateDescriptionIssueModel(BaseModel):
    issue_key: str = Field(..., description="Key of the Jira issue (e.g., 'PROJ-123').")
    description: str = Field(..., description="New description of the issue.")

class JiraService:
    def __init__(self, server, username, api_token):
        """Initializes the connection to the Jira server."""
        self.jira = JIRA(server=server, basic_auth=(username, api_token))

    def _get_initial_context(self) -> str:
        """Returns initial context including user, projects, issue types, and priorities."""
        user = self.jira.myself()
        projects = self.get_projects()
        issue_types = self.get_issue_types()
        priorities = self.get_priorities()
        context = f"""**User Information:**\n{user}\n\n**Projects:**\n{projects}\n\n\
            **Issue Types:**\n{issue_types}\n\n**Priorities:**\n{priorities}"""
        return context

    def get_agent_system_message(self) -> str:
        """Returns the system message for the Jira Agent."""
        jira_agent_system_message = f"""You are a Jira Assistant designed to help users manage Jira projects efficiently.

**Your Objectives:**

1. **Understand User Requests:** Carefully interpret user instructions related to managing Jira issues, such as creating issues, adding comments, or updating issue fields.

2. **Provide Clear Responses:** Present the results or information in a clear and concise manner.

3. **Handle Errors Gracefully:** If an error occurs or more information is needed, communicate this politely to the user.

**Instructions:**

- If additional information is needed to perform a function, ask the user for clarification.
- Do not include unnecessary information or perform actions outside of the provided functionalities.
- Focus on being accurate, helpful, and efficient in assisting the user with Jira tasks.

**Context Information**
{self._get_initial_context()}
"""
        return jira_agent_system_message

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

    #function to get user from the credentials
    @expose_for_llm
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
        """Search for issues in Jira using JQL language and return the issues information.

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
        """Creates a new issue in Jira with a clear and detailed summary and description.

        To create a good Jira issue, ensure that:

        - The **summary** provides a concise statement of the problem or task.
        - The **description** includes all necessary information to complete the work, such as:
            - **Context and Background:** Briefly explain the context or background of the issue.
            - **Detailed Description:** Elaborate on the problem or task, providing specifics.
            - **Expected Result:** Describe what should happen.
            - **Actual Result:** Describe what is currently happening.
            - **Impact or Justification:** Explain how this issue affects users or the project.
            - **Attachments or References:** Include any relevant information, logs, or links.

        A well-crafted issue should be organized and clear, enabling team members to understand the work that needs to be done without ambiguity.

        Returns:
            str: Key of the created issue.
        """
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
        """Updates a specific field of a Jira issue."""
        issue = self.jira.issue(data.issue_key)
        # TODO: Check if the field exists, if not it will raise an exception
        #issue.fields.__dict__[data.field_name] = data.field_value
        issue.update(fields={data.field_name: {"name": data.field_value}})
        return f"Field '{data.field_name}' added to issue {data.issue_key}."

    @expose_for_llm
    def update_issue_description(self, data: UpdateDescriptionIssueModel) -> str:
        """Updates the description of a Jira issue."""
        issue = self.jira.issue(data.issue_key)
        issue.update(fields={"description": data.description})
        return f"Description of issue {data.issue_key} updated."

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
    def change_issue_priority(self, data: ChangeIssuePriorityModel) -> str:
        """Changes the priority of an issue."""
        issue = self.jira.issue(data.issue_key)
        issue.update(fields={"priority": {"name": data.priority_name}})
        return f"Priority of issue {data.issue_key} changed to '{data.priority_name}'."


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