import inspect
import logging
from functools import wraps
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ValidationError

from llmbridge.llm_interface.schema_generator import generate_function_schemas

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class LLMInterface:
    """Interface for handling service functions exposed to LLM."""
    # Symbol used to split service name and function name since - is not allowed in class/function names
    SPLIT_SYMBOL:str = "-"

    def __init__(self, services: List[Any]):
        self.services = {service.__class__.__name__: service for service in services}
        self.function_schemas = self._generate_all_schemas()

    def _generate_all_schemas(self) -> List[Dict[str, Any]]:
        all_schemas = []
        for service_name, service in self.services.items():
            schemas = generate_function_schemas(service.__class__)
            for schema in schemas:
                schema["function"]['name'] = self._format_function_name(service_name, schema["function"]['name'])
            all_schemas.extend(schemas)
        return all_schemas

    def _format_function_name(self, service_name: str, function_name: str) -> str:
        return f"{service_name}{self.SPLIT_SYMBOL}{function_name}"

    def get_function_schemas(self) -> List[Dict[str, Any]]:
        return self.function_schemas

    def _handle_service_exception(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                operation = func.__name__.replace('_', ' ')
                error_message = f"Failed to {operation}: {str(e)}"
                logger.error(error_message)
                return error_message
        return wrapper

    def handle_function(self, func_name: str, params: Dict[str, Any] = None) -> Any:
        if params is None:
            params = {}
        try:
            service_name, method_name = self._split_function_name(func_name)
            service = self._get_service(service_name)
            method = self._get_method(service, method_name)
            return self._invoke_method(method, params)
        except Exception as e:
            raise ValueError(f"Failed to handle function {func_name}: {str(e)}") from e

    def _split_function_name(self, func_name: str) -> Tuple[str, str]:
        parts = func_name.split(self.SPLIT_SYMBOL, 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid function name format: {func_name}")
        return parts

    def _get_service(self, service_name: str) -> Any:
        service = self.services.get(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        return service

    def _get_method(self, service: Any, method_name: str) -> Any:
        method = getattr(service, method_name, None)
        if not method or not self._is_method_exposed_for_llm(method):
            raise ValueError(f"Function {method_name} not found or not exposed for LLM use")
        # Wrap method to handle exceptions
        return self._handle_service_exception(method)

    def _is_method_exposed_for_llm(self, method: Any) -> bool:
        return hasattr(method, 'expose_for_llm') and method.expose_for_llm

    def _invoke_method(self, method: Any, params: Dict[str, Any]) -> Any:
        signature = inspect.signature(method)
        if len(signature.parameters) == 0:
            return method()
        else:
            param = next(iter(signature.parameters.values()))
            if isinstance(param.annotation, type) and issubclass(param.annotation, BaseModel):
                try:
                    input_model = param.annotation(**params)
                    return method(input_model)
                except ValidationError as e:
                    raise ValueError(f"Invalid input: {str(e)}") from e
            else:
                raise TypeError(f"Unexpected input type for function {method.__name__}")

