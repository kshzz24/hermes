from tools.builtin import get_all_builtin_tools
from tools.base import ToolInvocation
from tools.base import ToolResult
from typing import Any
from pathlib import Path
import logging
from tools.base import Tool
logger = logging.getLogger(__name__)

class ToolRegistry: 
    def __init__(self):
        self._tools: dict[str, Tool] = {} 

    def register(self, tool: Tool)-> None:
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def unregister(self, name: str)-> bool:
        if name not in self._tools:
            logger.error(f"Tool {name} not found")
            return False
        del self._tools[name]
        logger.debug(f"Unregistered tool: {name}")
        return True
    
    def get(self, name:str) -> Tool | None:
        if name not in self._tools: 
            logger.debug(f"Tool {name} not found")
            return None
        return self._tools.get(name)
    
    def get_tools(self) -> list[Tool]:
        tools:list[Tool] = []
        for tool in self._tools.values():
            tools.append(tool)
        return tools
    
    def get_schemas(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self.get_tools()]

    def get_all(self) -> list[Tool]:
        return list(self._tools.values())

    async def invoke(self, name:str, params:dict[str, Any], cwd:Path) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult.error_result(f"Tool {name} not found", metadata={'tool_name': name})
        
        errors = tool.validate_params(params)
        if errors:
            return ToolResult.error_result(f"Validation errors: {', '.join(errors)}")
        
        invocation = ToolInvocation(cwd=cwd, params=params)
        try:
          result = await tool.execute(invocation)   
        except Exception as e:
             logger.exception(f"Tool {name} raised unexpected error")
             return ToolResult.error_result(f"Tool {name} raised unexpected error: {str(e)}", metadata={'tool_name': name})
        return result
              



def create_default_registry() -> ToolRegistry:
     registry = ToolRegistry()
     BUILTIN_TOOLS = get_all_builtin_tools()
     for tool in BUILTIN_TOOLS:
          registry.register(tool())

     return registry