import json
import os

import openai
import tiktoken
from dotenv import load_dotenv

from llmtoolkit.llm_interface.llm_interface import LLMInterface
from llmtoolkit.services.jira_service.jira_service import JiraService

load_dotenv()

def count_tokens(text):
    """Simplified aproach to count the number of tokens in a given text."""
    if text:
        encoding = tiktoken.encoding_for_model(os.getenv("OPENAI_MODEL"))
        return len(encoding.encode(text))
    else:
        return 0

if __name__ == "__main__":
    jira_service = JiraService(server=os.getenv("JIRA_DOMAIN"),
                                username=os.getenv("JIRA_USERNAME"),
                                api_token=os.getenv("JIRA_API_TOKEN"))
    llm_service_interface = LLMInterface([jira_service])
    tools_schemas = llm_service_interface.get_function_schemas()
    print("Available functions:", [schema["function"]['name'] for schema in tools_schemas])

    client = openai.OpenAI()
    model = os.getenv("OPENAI_MODEL")

    jira_agent_system_message = jira_service.get_jira_agent_system_message()

    messages = []
    start_message = "Hello! I'm your Jira Assistant, here to help you manage your projects and tasks efficiently. How can I assist you today?"
    messages.append({"role": "system", "content": jira_agent_system_message})
    messages.append({"role": "assistant", "content": start_message})
    print(f"Assistant: {start_message}\n")

    total_input_tokens = count_tokens(jira_agent_system_message) + count_tokens(start_message)
    total_output_tokens = count_tokens(start_message)
    total_tool_tokens = 0

    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})
        total_input_tokens += count_tokens(user_input)

        keep_calling_tools = True
        call_counter = 0
        while keep_calling_tools and call_counter < 5:
            call_counter += 1
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools_schemas,
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message
            messages.append(assistant_message)
            total_output_tokens += count_tokens(assistant_message.content)

            if assistant_message.tool_calls:
                keep_calling_tools = True
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    try:
                        result = llm_service_interface.handle_function(function_name, params=arguments)
                    except Exception as e:
                        result = f"An error occurred: {str(e)}"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": result
                    })
                    total_tool_tokens += count_tokens(result)
            else:
                keep_calling_tools = False

        print(f"Assistant: {assistant_message.content}\n")

    print("\nConversation ended. Total tokens used:")
    print(f"Total input tokens: {total_input_tokens}")
    print(f"Total output tokens: {total_output_tokens}")
    print(f"Total tool tokens: {total_tool_tokens}")
    print(f"Total tokens: {total_input_tokens + total_output_tokens + total_tool_tokens}")
