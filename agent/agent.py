from __future__ import annotations 
from client.response import ToolResultMessage
from pathlib import Path
from client.response import ToolCall
from tools.registry import create_default_registry
from context.manager import ContextManager
from agent.events import AgentEventType
from client.llm_client import LLMClient
from agent.events import AgentEvent
from client.response import StreamEventType
from typing import AsyncGenerator



class Agent:
     def __init__(self) -> None:
          self.client = LLMClient()
          self.context_manager = ContextManager()
          self.tool_registry = create_default_registry()

     async def run(self, message:str):
        yield AgentEvent.agent_start(message)
        self.context_manager.add_user_message(message)
        # add user context message for the context
        final_response:str | None = None
        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
              final_response  = event.data.get("content")
         
        yield AgentEvent.agent_end(final_response)
     
     async def _agentic_loop(self)->AsyncGenerator[AgentEvent, None]:
        response_text = ""
        tools_schema = self.tool_registry.get_schemas()
        tool_calls:list[ToolCall] = []
        async for event in self.client.chat_completion(self.context_manager.get_messages(), tools=tools_schema if tools_schema else None, stream=True):
          #   print(event)
            if event.type == StreamEventType.TEXT_DELTA:
                if event.text_delta: 
                    content = event.text_delta.content
                    response_text += content
                    yield AgentEvent.text_delta(content)
          #   elif event.type == StreamEventType.TOOL_CALL_START:
          #        yield AgentEvent.tool_call_start(event.tool_call_delta.call_id, event.tool_call_delta.name)
          #   elif event.type == StreamEventType.TOOL_CALL_DELTA:
          #        yield AgentEvent.tool_call_delta(event.tool_call_delta.call_id, event.tool_call_delta.arguments)
            elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                  if event.tool_call:
                     tool_calls.append(event.tool_call) 
            elif event.type == StreamEventType.ERROR:
                 yield AgentEvent.agent_error(event.error or "Unknown error occured")
        
        self.context_manager.add_assistant_message(response_text or None)
        if response_text: 
            yield AgentEvent.text_complete(response_text)
        
        tool_call_results: list[ToolResultMessage] = []
        for tool_call in tool_calls:
            yield AgentEvent.tool_call_start(tool_call.call_id, tool_call.name, tool_call.arguments)

            result = await self.tool_registry.invoke(tool_call.name, tool_call.arguments, Path.cwd())
            yield AgentEvent.tool_call_complete(tool_call.call_id, tool_call.name, result)
            tool_call_results.append(ToolResultMessage(tool_call_id=tool_call.call_id, content=result.to_model_output(), is_error=not result.success))

        for tool_result in tool_call_results:
             self.context_manager.add_tool_result(tool_result.tool_call_id, tool_result.content) 


            
     async def __aenter__(self)->Agent:
          return self
     async def __aexit__(self, exc_type, exc_val, exc_tb) ->None:
          if self.client:
            await self.client.close()
            self.client = None