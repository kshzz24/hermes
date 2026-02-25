import sys
from rich import get_console
from ui.tui import TUI
from agent.events import AgentEventType

from agent.agent import Agent
import asyncio
import click



console = get_console()

class CLI:
     def __init__(self) -> None:
         self.agent: Agent | None = None
         self.tui = TUI(console)

     async def run_single(self,message:str)-> str | None:
         async with Agent() as agent:
               self.agent = agent
               return await self.process_message(message)
     async def process_message(self, message:str):
           if not self.agent:
                return
           assistant_streaming = False     
           final_response:str | None = None

           
           async for event in self.agent.run(message):
                print(event)
                if event.type == AgentEventType.TEXT_DELTA:
                    content = event.data.get("content","")
                    if not assistant_streaming:
                        self.tui.begin_assistant()
                        assistant_streaming = True
                    self.tui.stream_assistant_delta(content)
                elif event.type == AgentEventType.TEXT_COMPLETE:
                    final_response = event.data.get("content","")
                    if assistant_streaming:
                        self.tui.end_assistant()
                        assistant_streaming = False
                elif event.type == AgentEventType.AGENT_ERROR:
                    error = event.data.get("error", "Unknown error")
                    console.print(f"\n[error] Error: {error}[/error]")
                elif event.type == AgentEventType.TOOL_CALL_START:
                    tool_name = event.data.get("name")
                    tool_kind = None
                    tool = self.agent.tool_registry.get(tool_name)
                    if not tool:
                         return tool_kind

                    tool_kind = tool.kind.value
                    # call_id = event.data.get("call_id")
                    # arguments = event.data.get("arguments")
                    self.tui.tool_call_start(call_id, name, arguments)
                elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                    name = event.data.get("name")
                    call_id = event.data.get("call_id")
                    result = event.data.get("result")
                    self.tui.end_tool_call(call_id, name, result)
                   
           return final_response

async def run(messages: dict[str,any]):
     pass

@click.command()
@click.argument("prompt", required=False)
def main(prompt: str | None):
    cli = CLI()
    # messages = [{'role': 'user','content': prompt or "What's up"}]
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
             sys.exit(1)
        
   
main()
