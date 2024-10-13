# LLMBridge

An open-source project providing a unified interface to integrate Large Language Models (LLMs) with various services.

## Overview

**LLMBridge** connects Large Language Models (LLMs) with various services through a unified interface called the **LLMInterface**. The primary focus is on simplifying the integration of new services without directly managing LLM interactions. The `LLMInterface` generates function schemas and handles service calls by leveraging docstrings and Pydantic models from your service methods.

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
- [Configuration](#configuration)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

## Features

- **Unified LLM Interface**: A core interface that generates service schemas and handles tool calls without directly interacting with the LLM.
- **Multi-Service Management**: Ability to integrate and manage multiple services at the same time.
- **Extensible Service Integrations**: Easily add integrations with services like Jira, web search, code execution, and more.

## Installation

### Prerequisites

- **Python**: Version 3.11 or higher.
- **Poetry**: Python dependency management tool. [Installation Guide](https://python-poetry.org/docs/#installation).

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/marcosventosa/LLMBridge.git
   cd LLMBridge
   ```

2. **Install Dependencies**

   Install all dependencies, including the package itself, using Poetry:

   ```bash
   poetry install
   ```

3. **Activate the Virtual Environment**

   ```bash
   poetry shell
   ```

   This command starts a new shell with the virtual environment activated.

## Project Structure

```
LLMBridge/
├── pyproject.toml
├── poetry.lock
├── README.md
├── src/
│   └── llmbridge/
│       ├── __init__.py
│       ├── llminterface/
│       │   ├── __init__.py
│       │   ├── llm_interface.py
│       │   ├── utils.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── jira_service/
│       │       ├── __init__.py
│       │       ├── jira_service.py
│       │   ├── web_search_service/
│       │       ├── __init__.py
│       │       ├── web_search_service.py
│       │   └── ... (other services)
├── examples/
│   ├── main.py
│   ├── jira_example.py
│   └── ... (other examples)
```

- **`src/llmbridge/`**: Contains the source code for the project.
  - **`llminterface/`**: Core interface for managing function schemas and handling service calls.
  - **`services/`**: Service integrations, starting with Jira and potentially including others like web search.
- **`examples/`**: Example scripts demonstrating how to use the library.

## Quick Start

Here's a simple example of how to use LLMBridge with **multiple services** using the `LLMInterface`. This example includes the Jira service and a hypothetical Web Search service.

### Example: Using the LLMInterface with Multiple Services

```python
# examples/main.py

import os
from dotenv import load_dotenv

from llmbridge.llminterface.llm_interface import LLMInterface
from llmbridge.services.jira_service.jira_service import JiraService
from llmbridge.services.web_search_service.web_search_service import WebSearchService

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

### Running the Example

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
   OPENAI_MODEL=gpt-3.5-turbo  # or your desired model
   ```

2. **Activate the Virtual Environment**

   ```bash
   poetry shell
   ```

3. **Run the Example Script**

   ```bash
   poetry run python examples/jira_agent.py
   ```

## Creating a New Service

One of the main goals of LLMBridge is to make it easy to integrate new services. The `LLMInterface` can manage multiple services at the same time, enabling the LLM to interact with all of them seamlessly.

### Service Implementation Guidelines

1. **Create a Service Class**

   - Create a new directory for your service under `src/llmbridge/services/`.
   - Implement your service class in a file within this directory.

   **Example Structure:**

   ```
   src/llmbridge/services/
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
   from llmbridge.llminterface.llm_interface import LLMInterface
   from llmbridge.services.jira_service.jira_service import JiraService
   from llmbridge.services.web_search_service.web_search_service import WebSearchService
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

## Examples

The `examples/` directory contains scripts demonstrating how to use the `LLMInterface` and integrate services.

- **`jira_example.py`**: Demonstrates usage with the `JiraService`.

## Configuration

### Environment Variables and `.env` File

The examples use environment variables for configuration. You can set these variables in your shell or store them in a `.env` file.

**Example `.env` File:**

```
# For the JiraService
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

# For the LLM client (e.g., OpenAI)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo  # or your desired model
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

As LLMBridge continues to develop, we have several plans to enhance its capabilities:

- **Support for Additional LLM Providers**: We plan to integrate support for more LLM providers beyond OpenAI.

- **New Service Integrations**: We aim to add more built-in service integrations, including:

  - **GitHubService**: Interaction with GitHub repositories, issues, and pull requests.
  - **ConfluenceService**: Integration with confluence to manage pages.
  - **CodeExecutionService**: Execute code snippets securely and return results.
  - **DatabaseService**: Interact with databases to query and manipulate data.
  - **EmailService**: Send and receive emails.
  - **SlackService**: Integration with Slack for messaging and automation.

- **Enhanced Error Handling and Logging**: Improve the robustness of the framework by adding comprehensive error handling and detailed logging.

- **Improved Documentation and Tutorials**: Provide more guides, tutorials, and examples to help new users and contributors get started.

- **Testing and CI/CD Integration**: Implement unit tests, integration tests, and set up continuous integration workflows to maintain code quality.

We welcome contributions and suggestions from the community to help shape the direction of LLMBridge. Feel free to open issues or pull requests with your ideas and enhancements.

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

If you have any questions or need further assistance, feel free to [open an issue](https://github.com/marcosventosa/LLMBridge/issues).

---