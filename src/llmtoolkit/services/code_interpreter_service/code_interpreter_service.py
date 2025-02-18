import ast
from datetime import datetime
import logging
import os
import sys
from io import StringIO
import io
import base64
from typing import Optional, Tuple
from pydantic import BaseModel, Field
import contextlib
from llmtoolkit.llm_interface.utils import expose_for_llm

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class CodeInterpreterModel(BaseModel):
    code: str = Field(..., description="Python code to execute, only printed output will be captured")
    timeout: Optional[int] = Field(5, description="Maximum execution time in seconds")

class CodeInterpreterResult(BaseModel):
    output: str = Field(..., description="Text output from code execution")
    image: Optional[str] = Field(None, description="Base64 encoded image if a plot was generated")


class CodeInterpreterService:
    def __init__(self):
        """Initializes the Code Execution Service."""
        # Only restrict the most dangerous operations
        self.forbidden_builtins = {
            'eval', 'exec', 'compile'
        }

        # Only restrict system-level operations
        self.forbidden_modules = {
            'subprocess', 'socket'
        }

        # Initialize the global variables
        self.global_vars = self._setup_global_vars()

    def _setup_global_vars(self):
        """Sets up the global variables with basic built-ins."""
        global_vars = {
            '__builtins__': dict(__builtins__),  # Allow all built-ins except forbidden ones
        }

        # Remove forbidden built-ins
        for func in self.forbidden_builtins:
            global_vars['__builtins__'].pop(func, None)

        return global_vars

    def get_agent_system_message(self) -> str:
        """Returns the system message for the Code Execution Agent."""
        code_execution_system_message = """You are a Code Execution Assistant designed to help users execute Python code.

**Your Objectives:**

1. **Execute Code:** Run Python code while maintaining basic security measures.
2. **Provide Clear Output:** Show both the execution results and any plots generated.
3. **Support Various Libraries:** Allow the use of most Python libraries.

**Instructions:**

- Most Python libraries can be imported and used.
- Matplotlib plots will be automatically captured and displayed.
- Basic security measures prevent potentially harmful system operations.
- Standard output and errors will be captured and returned.

**Example Usage:**
```python
# You can import most libraries
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# ... or any other library that's installed

# Create and display plots
plt.plot([1, 2, 3], [1, 2, 3])
plt.show()

# Use any data science tools
import seaborn as sns
sns.set_theme()
"""
        return code_execution_system_message
    def _check_ast_security(self, tree: ast.AST) -> bool:
        """Performs basic security checks on the AST.
        Only blocks the most dangerous operations.
        """
        for node in ast.walk(tree):
            # Check for forbidden imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = node.names[0].name.split('.')[0]
                if module_name in self.forbidden_modules:
                    raise SecurityError(f"Import of module '{module_name}' is not allowed for security reasons")

            # Check for calls to forbidden built-ins
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.forbidden_builtins:
                        raise SecurityError(f"Use of built-in '{node.func.id}' is not allowed for security reasons")

        return True

    def _capture_plot(self) -> Optional[str]:
        """Captures matplotlib plots and converts them to base64 string. Also save plot to file.

        Returns None if no plot was generated.
        """
        try:
            import matplotlib.pyplot as plt
            if plt.get_fignums():  # Check if there are any figures
                # Create timestamp for unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"plot_{timestamp}.png"
                
                # Create plots directory if it doesn't exist
                plots_dir = "plots"
                os.makedirs(plots_dir, exist_ok=True)
                file_path = os.path.join(plots_dir, filename)
            
                # Save to file
                plt.savefig(file_path, bbox_inches='tight')

                # # Also capture to base64
                # buf = io.BytesIO()
                # plt.savefig(buf, format='png', bbox_inches='tight')
                # buf.seek(0)
                # plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
                plt.close('all')  # Close all figures
                return file_path
            return None
        except Exception as e:
            logger.warning(f"Failed to capture plot: {str(e)}")
            return None

    @contextlib.contextmanager
    def _capture_output(self):
        """Captures stdout and stderr."""
        new_out, new_err = StringIO(), StringIO()
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = new_out, new_err
            yield sys.stdout, sys.stderr
        finally:
            sys.stdout, sys.stderr = old_out, old_err

    @expose_for_llm
    def execute_code(self, data: CodeInterpreterModel) -> str:
        """Executes Python code and returns the printed outputs.
        
        Features:
        - Allows most library imports
        - Captures standard output and errors
        - Captures matplotlib plots
        - Basic security measures
        
        Returns:
            A string containing the execution output, error message, and any generated plots.
        """
        try:
            # Allow matplotlib to work in non-interactive mode
            import matplotlib
            matplotlib.use('Agg')
            # Parse the code into an AST
            tree = ast.parse(data.code)
            
            # Basic security check
            self._check_ast_security(tree)
            
            # Prepare the execution environment
            local_vars = {}
            
            # Execute the code with output capture
            with self._capture_output() as (out, err):
                exec(compile(tree, '<string>', 'exec'), self.global_vars, local_vars)
                
                # Capture any plots
                image_path = self._capture_plot()
                
            # Get the output
            output = out.getvalue()
            error_output = err.getvalue()
            
            # Format the text output
            result = "Code Execution Results:\n"
            result += "-" * 20 + "\n"
            if output:
                result += "Output:\n"
                result += output + "\n"
            if error_output:
                result += "Errors:\n"
                result += error_output + "\n"
            if not output and not error_output:
                result += "No output produced\n"
            
            # Add image data to the output if present
            if image_path:
                result += f"[IMAGE_PATH]:{image_path}"
            
            return result

        except SyntaxError as e:
            return f"Syntax Error: {str(e)}"
        except SecurityError as e:
            return f"Security Error: {str(e)}"
        except Exception as e:
            return f"Execution Error: {str(e)}"

class SecurityError(Exception):
    """Custom exception for security violations."""
    pass
