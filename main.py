from anyio import Path
import click
from config.loader import load_config
import sys
from ui.tui import TUI, get_console
from agent.events import AgentEventType
from config.config import Config
from agent.agent import Agent
import asyncio
import click



console = get_console()

class CLI:
     def __init__(self ,config:Config) -> None:
         self.agent: Agent | None = None
         self.tui = TUI(config, console)
         self.config = config

     async def run_single(self,message:str)-> str | None:
         async with Agent(self.config) as agent:
               self.agent = agent
               return await self.process_message(message)

     async def run_interactive(self)-> None:
        self.tui.print_welcome("ClaudeKode", lines=[
            "Welcome to ClaudeKode",
            f"model: {self.config.model_name}",
            "Type /exit to quit",
            
        ])

        async with Agent(self.config) as agent:
               self.agent = agent

               while True:
                  try:
                    user_input = console.input("\n[user] > [/user] ").strip()
                    if not user_input:
                         continue
                    if user_input.lower() == "/exit":
                         break
                    await self.process_message(user_input)
                  except KeyboardInterrupt:
                        console.print(f"\n[dim]Use /exit to quit[/dim]")
                  except EOFError:
                        break  
        console.print("\n[dim]Goodbye![/dim]")

     def _get_tool_kind(self, tool_name:str) -> str | None:
         tool_kind = None
         tool = self.agent.session.tool_registry.get(tool_name)
         if tool:
              tool_kind = tool.kind.value
         else:
              tool_kind = None
         return tool_kind
    
     async def process_message(self, message:str):
           if not self.agent:
                return
           assistant_streaming = False     
           final_response:str | None = None

           
           async for event in self.agent.run(message):
                # print(event)
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
                    tool_name = event.data.get("name", "unknown")
                    tool_kind = self._get_tool_kind(tool_name)
                    self.tui.tool_call_start(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("arguments", {}),
                )
                elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                    tool_name = event.data.get("name", "unknown")
                    call_id = event.data.get("call_id")
                   
                    tool_kind = self._get_tool_kind(tool_name)
                    self.tui.tool_call_complete(
                    call_id,
                    tool_name,
                    tool_kind,
                    event.data.get("success", False),
                    event.data.get("output", ""),
                    event.data.get("error"),
                    event.data.get("metadata"),
                    event.data.get("diff"),
                    event.data.get("truncated", False),
                    event.data.get('exit_code')
                    )
                   
           return final_response

async def run(messages: dict[str,any]):
     pass

@click.command()
@click.argument("prompt", required=False)
@click.option('--cwd', '-c', type=click.Path(exists=True, file_okay=False, path_type=Path), help='Current working directory')
def main(prompt: str | None, cwd:Path | None):
   
    try:
        config = load_config(cwd=cwd)
    except Exception as e:
         console.print(f"configuration Error:{e}[/error]")

    errors = config.validate()
    if errors:
         for error in errors:
             console.print(f"[error]{error}[/error]")
         sys.exit(1)        
    # messages = [{'role': 'user','content': prompt or "What's up"}]
    cli = CLI(config=config)
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
             sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())         
        
   
main()
