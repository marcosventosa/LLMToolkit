# LLMToolkit

An open-source project providing a unified interface to integrate Large Language Models (LLMs) with various services.

## Overview

**LLMToolkit** connects Large Language Models (LLMs) with various services through a unified interface called the **LLMInterface**. The primary focus is on simplifying the integration of new services without directly managing LLM interactions. The `LLMInterface` generates function schemas and handles service calls by leveraging docstrings and Pydantic models from your service methods.

The `LLMInterface` can manage multiple services simultaneously, allowing the LLM to interact with a variety of tools and services within a single framework. This flexibility enables the creation of rich and complex applications that leverage the strengths of different services together.

While the initial example integration is with Jira (the **JiraService**), the architecture is designed to easily accommodate other services such as web searching, code execution, data manipulation, and more.

This README explains how to create new services and integrate them with the `LLMInterface`, making it easy for contributors to extend the project's capabilities.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Creating a New Service](#creating-a-new-service)
  - [Service Implementation Guidelines](#service-implementation-guidelines)
  - [Integrating with LLMInterface](#integrating-with-llminterface)
- [Examples](#examples)
  - [CLI Examples](#cli-examples)
  - [Streamlit Examples](#streamlit-examples)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

## Features

- **Unified LLM Interface**: A core interface that generates service schemas and handles tool calls without directly interacting with the LLM.
- **Multi-Service Management**: Ability to integrate and manage multiple services at the same time.
- **Extensible Service Integrations**: Easily add integrations with services like Jira, web search, code execution, and more.
- **CLI and Web Interface Examples**: Demonstrations of both command-line and web-based applications using the toolkit.

## Installation

### Prerequisites

- **Python**: Version 3.11 or higher.
- **Poetry** (optional): Python dependency management tool. [Installation Guide](https://python-poetry.org/docs/#installation).

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/marcosventosa/LLMToolkit.git
   cd LLMToolkit
   ```

2. **Install Dependencies**

   You can install all dependencies, including the package itself, using either **Poetry** or **pip**.

   **Option 1: Using Poetry**

   ```bash
   poetry install
   ```

   **Option 2: Using pip**

   First, it's recommended to create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

   Then install the package in editable mode with the required dependencies:

   ```bash
   pip install -e . 
   ```

3. **Activate the Virtual Environment**

   - If you used **Poetry**, activate the virtual environment:

     ```bash
     poetry shell
     ```

     This command starts a new shell with the virtual environment activated.

   - If you used **pip** and created a virtual environment manually, ensure it's activated (as shown in Option 2 above).

## Project Structure

```
LLMToolkit/
├── pyproject.toml
├── poetry.lock
├── README.md
├── src/
│   └── llmtoolkit/
│       ├── __init__.py
│       ├── llminterface/
│       │   ├── __init__.py
│       │   ├── llm_interface.py
│       │   ├── utils.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── jira_service/
│       │   │   ├── __init__.py
│       │   │   ├── jira_service.py
│       │   ├── web_search_service/
│       │   │   ├── __init__.py
│       │   │   ├── web_search_service.py
│       │   └── ... (other services) 
├── examples/
    ├── cli/
    │   ├── gmail_agent.py
    │   ├── jira_agent.py
    │   └── ... (other examples) 
    └── streamlit/
        ├── multi_service_agent_api.py
        └── multi_service_agent_client.py
```

- **`src/llmtoolkit/`**: Contains the source code for the project.
  - **`llminterface/`**: Core interface for managing function schemas and handling service calls.
  - **`services/`**: Service integrations, starting with Jira and potentially including others like web search.
- **`examples/`**: Example scripts demonstrating how to use the library.
  - **`cli/`**: Command-line interface examples.
  - **`streamlit/`**: Streamlit web application examples.

## Quick Start

Here's a simple example of how to use LLMToolkit with **multiple services** using the `LLMInterface`. This example includes the Jira service and a hypothetical Web Search service.

### Example: Using the LLMInterface with Multiple Services

```python
# examples/main.py

import os
from dotenv import load_dotenv

from llmtoolkit.llminterface.llm_interface import LLMInterface
from llmtoolkit.services.jira_service.jira_service import JiraService
from llmtoolkit.services.web_search_service.web_search_service import WebSearchService

load_dotenv()

def main():
    # Initialize your services
    jira_service = JiraService(
        server=os.getenv("JIRA_SERVER"),
        username=os.getenv("JIRA_USERNAME"),
        api_token=os.getenv("JIRA_API_TOKEN")
    )

    web_search_service = WebSearchService()

    # Initialize the LLM Interface with multiple services
    llm_interface = LLMInterface([jira_service, web_search_service])

    # Get function schemas from the services
    tools_schemas = llm_interface.get_function_schemas()
    print("Available functions:", [schema["function"]['name'] for schema in tools_schemas])

    # Set up your LLM client (e.g., OpenAI client)
    # Ensure your OpenAI API key is set in the environment variables

    # Prepare messages and interaction loop
    # (Refer to the detailed example in the examples directory for full interaction code)

if __name__ == "__main__":
    main()
```

In this example, the `LLMInterface` is initialized with both the `JiraService` and a hypothetical `WebSearchService`. The LLM will have access to functions from both services and can interact with them as needed during the conversation.

### Running the CLI Example

1. **Set Environment Variables**

   Create a `.env` file in the root directory (or set the environment variables directly).

   **`.env` File:**

   ```
   # Required for the JiraService
   JIRA_SERVER=https://your-domain.atlassian.net
   JIRA_USERNAME=your-email@example.com
   JIRA_API_TOKEN=your-jira-api-token

   # Required for OpenAI client (if using OpenAI APIs)
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_MODEL=gpt-4o  # or your desired model
   ```

2. **Activate the Virtual Environment**

   ```bash
   poetry shell
   ```

3. **Run the Example Script**

   ```bash
   poetry run python examples/cli/jira_agent.py
   ```

### Running the Streamlit Example

The Streamlit example provides a web interface for interacting with the LLMToolkit.

1. **Set Environment Variables**

   Create a `.env` file in the root directory (or set the environment variables directly).

   **`.env` File:**

   ```
   # Required for the JiraService
   JIRA_SERVER=https://your-domain.atlassian.net
   JIRA_USERNAME=your-email@example.com
   JIRA_API_TOKEN=your-jira-api-token

   # Required for OpenAI client (if using OpenAI APIs)
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_MODEL=gpt-4o  # or your desired model

   # Required for Gmail integration
   GMAIL_CREDENTIALS_PATH=json-credential-path # https://developers.google.com/gmail/api/quickstart/python
   ```

2. **Activate the Virtual Environment**

   ```bash
   poetry shell
   ```

3. **Run the FastAPI api**

   ```bash
   poetry run python examples/streamlit/multi_service_agent_api.py
   ```

4. **Run the Streamlit Application**

   ```bash
   streamlit run examples/streamlit/multi_service_agent_client.py
   ```

   This will start the Streamlit app, and you can access it in your web browser at the URL provided in the terminal.


## Creating a New Service

One of the main goals of LLMToolkit is to make it easy to integrate new services. The `LLMInterface` can manage multiple services at the same time, enabling the LLM to interact with all of them seamlessly.

### Service Implementation Guidelines

1. **Create a Service Class**

   - Create a new directory for your service under `src/llmtoolkit/services/`.
   - Implement your service class in a file within this directory.

   **Example Structure:**

   ```
   src/llmtoolkit/services/
   ├── __init__.py
   ├── jira_service/
   │   ├── __init__.py
   │   └── jira_service.py
   ├── web_search_service/
   │   ├── __init__.py
   │   └── web_search_service.py
   └── your_service/
       ├── __init__.py
       └── your_service.py
   ```

2. **Define Input Parameters with Pydantic Models**

   - Use Pydantic `BaseModel` classes to define input parameters for your service methods.
   - Provide descriptions for each field to aid in schema generation.

   ```python
    class CreateIssueModel(BaseModel):
        summary: str = Field(..., description="Summary of the issue")
        project_key: str = Field(..., description="Key of the Jira project")
        issue_type: str = Field("Task", description="Type of the issue")
        description: Optional[str] = Field(None, description="Description of the issue")
    
    class Jira Service
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
   ```

3. **Annotate Methods with `@expose_for_llm`**

   - Use the `@expose_for_llm` decorator on methods you want to expose to the LLM.
   - Methods must return strings since their output is meant to be directly fed into the LLM.
   - Include clear docstrings to describe the method; these will be used to generate function schemas.

4. **Handle Errors**

   - The `LLMInterface` handles exceptions automatically and feeds error information back to the LLM.
   - Ensure your methods raise appropriate exceptions when errors occur.

### Integrating with LLMInterface

1. **Import Your Services and the LLMInterface**

   ```python
   from llmtoolkit.llminterface.llm_interface import LLMInterface
   from llmtoolkit.services.jira_service.jira_service import JiraService
   from llmtoolkit.services.web_search_service.web_search_service import WebSearchService
   # Import any additional services
   ```

2. **Initialize Your Services**

   ```python
   jira_service = JiraService(...)
   web_search_service = WebSearchService(...)
   # Initialize any additional services
   ```

3. **Create the LLMInterface with Your Services**

   ```python
   llm_interface = LLMInterface([jira_service, web_search_service])
   # Add additional services to the list as needed
   ```

4. **Generate Function Schemas**

   - The `LLMInterface` will automatically generate schemas for the exposed methods in your services.
   - These schemas include function names, descriptions, parameters, and return types, which are used to communicate with the LLM.

5. **Use the LLMInterface in LLM Interactions**

   - Your main application is responsible for setting up the LLM client (e.g., OpenAI) and handling the conversation loop.
   - Use the function schemas generated by the `LLMInterface` when configuring your LLM calls.

   ```python
   tools_schemas = llm_interface.get_function_schemas()
   response = openai.ChatCompletion.create(
       model=model,
       messages=messages,
       functions=tools_schemas,
       function_call="auto",
   )
   ```

   - Call `handle_function()` for each tool call

   ```python
   if 'function_call' in assistant_message:
       function_name = assistant_message['function_call']['name']
       arguments = json.loads(assistant_message['function_call']['arguments'])
       result = llm_interface.handle_function(function_name, params=arguments)
       # Add result to conversation messages
   ```

## Contributing

Contributions are welcome! Since the project focuses on enhancing the `LLMInterface` and demonstrating its extensibility, contributions in these areas are highly appreciated.

### How to Contribute

1. **Fork the Repository**

2. **Create a Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**

   - Enhance the `LLMInterface` with additional features or support for more LLM scenarios.
   - Add new service integrations (e.g., web searching, code execution).
   - Add support for more LLM providers.
   - Write examples demonstrating new capabilities.
   - Improve documentation.

4. **Document Your Changes**

   - Update the README and any relevant documentation to reflect your additions.
   - Include code examples if you're adding new services or features.

5. **Commit and Push**

   ```bash
   git commit -m "Add your feature or improvement"
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**

   - Provide a clear description of your changes and the motivation behind them.

## Roadmap

As LLMToolkit continues to develop, we have several plans to enhance its capabilities:

- **Support for Additional LLM Providers**: We plan to integrate support for more LLM providers beyond OpenAI.

- **New Service Integrations**: We aim to add more built-in service integrations, including:

  - **GitHubService**: Interaction with GitHub repositories, issues, and pull requests.
  - **ConfluenceService**: Integration with confluence to manage pages.
  - **CodeExecutionService**: Execute code snippets securely and return results.
  - **DatabaseService**: Interact with databases to query and manipulate data.
  - **OutlookService**: Outlook email and outlook calendar integration.
  - **SlackService**: Integration with Slack for messaging and automation.

- **Enhanced Error Handling and Logging**: Improve the robustness of the framework by adding comprehensive error handling and detailed logging.

- **Improved Documentation and Tutorials**: Provide more guides, tutorials, and examples to help new users and contributors get started.

- **Testing and CI/CD Integration**: Implement unit tests, integration tests, and set up continuous integration workflows to maintain code quality.

We welcome contributions and suggestions from the community to help shape the direction of LLMToolkit. Feel free to open issues or pull requests with your ideas and enhancements.

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

If you have any questions or need further assistance, feel free to [open an issue](https://github.com/marcosventosa/LLMToolkit/issues).

---