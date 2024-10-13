import inspect
from typing import Any, Callable, Dict, List, Union, get_args, get_origin

from docstring_parser import parse
from pydantic import BaseModel

TYPE_MAPPING: Dict[str, str] = {
    'str': 'string',
    'int': 'integer',
    'float': 'number',
    'bool': 'boolean',
    'list': 'array',
    'dict': 'object',
    'NoneType': 'null',
}

def generate_function_schemas(cls: object) -> List[Dict[str, Any]]:
    schemas: List[Dict[str, Any]] = []
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if getattr(method, 'expose_for_llm', False):
            schema = generate_schema_for_method(name, method)
            schemas.append(schema)
    return schemas

def generate_schema_for_method(name: str, method: Callable) -> Dict[str, Any]:
    signature = inspect.signature(method)
    validate_return_type(name, signature)
    docstring = parse(method.__doc__)

    function_schema: Dict[str, Any] = {
        "name": name,
        "description": docstring.description or "",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }

    for param_name, param in signature.parameters.items():
        if param_name != 'self':
            process_parameter(param, function_schema)

    return {
        "type": "function",
        "function": function_schema
    }

# All functions exposed to LLM should return a string
def validate_return_type(name: str, signature: inspect.Signature) -> None:
    output_type = signature.return_annotation
    if output_type != str:
        raise ValueError(f"Function {name} should return a string, but it returns {output_type}")

def process_parameter(param: inspect.Parameter, function_schema: Dict[str, Any]) -> None:
    if isinstance(param.annotation, type) and issubclass(param.annotation, BaseModel):
        model = param.annotation
        for field_name, field in model.model_fields.items():
            add_field_to_schema(field_name, field, function_schema)

def add_field_to_schema(field_name: str, field: Any, function_schema: Dict[str, Any]) -> None:
    type_name = get_json_schema_type(field.annotation)
    function_schema["parameters"]["properties"][field_name] = {
        "type": type_name,
        "description": field.description or f"Parameter: {field_name}"
    }
    if field.is_required():
        function_schema["parameters"]["required"].append(field_name)

def get_json_schema_type(python_type: Any) -> Union[str, Dict[str, Any]]:
    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is None:
        return TYPE_MAPPING.get(python_type.__name__, 'string')
    elif origin in (list, tuple):
        item_type = get_json_schema_type(args[0]) if args else 'string'
        return {
            "type": "array",
            "items": {
                "type": item_type
            }
        }
    elif origin is dict:
        return "object"
    elif origin is Union:
        non_none_args = [arg for arg in args if arg.__name__ != 'NoneType']
        if len(non_none_args) > 1:
            print(f"Warning: Multiple types in Union type {python_type}")
        return get_json_schema_type(non_none_args[0])
    else:
        return 'string'
