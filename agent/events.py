from __future__ import annotations
from tools.base import ToolResult
from client.response import TokenUsage
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentEventType(str, Enum):
     # agent lifecycle related
     AGENT_START = "agent_start"
     AGENT_END = "agent_end"
     AGENT_COMPLETE = "agent_complete"
     AGENT_ERROR = "agent_error"

     #text streaming related    
     TEXT_DELTA = "text_delta"
     TEXT_COMPLETE="text_complete"

     #tool related
     TOOL_CALL_START = "tool_call_start"
     TOOL_CALL_DELTA = "tool_call_delta"
     TOOL_CALL_COMPLETE = "tool_call_complete"


@dataclass
class AgentEvent:
     type: AgentEventType
     data: dict[str, Any] = field(default_factory=dict)
     @classmethod
     def agent_start(cls, message: str)-> AgentEvent:
          return cls(
               type=AgentEventType.AGENT_START,
               data={"message": message},
          )
     
     @classmethod
     def agent_end(cls, response: str | None = None, usage: TokenUsage | None = None)-> AgentEvent:
          return cls(
               type=AgentEventType.AGENT_END,
               data={"response": response,"usage": usage.__dict__ if usage else None},
          )
     
     @classmethod
     def agent_complete(cls)-> AgentEvent:
          return cls(
               type=AgentEventType.AGENT_COMPLETE,
               data={"message": "Agent complete"},
          )
     
     @classmethod
     def agent_error(cls, error: str, details: dict[str, any] | None = None)-> AgentEvent:
          return cls(
               type=AgentEventType.AGENT_ERROR,
               data={"error": error,"details": details or {}},
          )
     @classmethod
     def tool_call_start(cls, call_id: str, name: str, arguments:dict[str, Any])-> AgentEvent:
          return cls(
               type=AgentEventType.TOOL_CALL_START,
               data={"call_id": call_id, "name": name, "arguments": arguments},
          )
     @classmethod
     def tool_call_delta(cls, call_id: str, arguments:str)-> AgentEvent:
          return cls(
               type=AgentEventType.TOOL_CALL_DELTA,
               data={"call_id": call_id, "arguments": arguments},
          )
     @classmethod
     def tool_call_complete(cls, call_id: str, name: str, result:ToolResult)-> AgentEvent:
          return cls(
               type=AgentEventType.TOOL_CALL_COMPLETE,
               data={"call_id": call_id, "name": name, "success": result.success, "output": result.output, "error": result.error, "metadata": result.metadata},
          )
     @classmethod
     def text_complete(cls, content: str)-> AgentEvent:
          return cls(
               type=AgentEventType.TEXT_COMPLETE,
               data={"content": content},
          )
