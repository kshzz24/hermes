from agent.events import AgentEventType

from agent.agent import Agent
import asyncio
import click


class CLI:
     def __init__(self) -> None:
         self.agent: Agent | None = None
     async def run_single(self,message:str):
         async with Agent() as agent:
               self.agent = agent
               self.process_message(message)
     async def process_message(self, message:str):
           if not self.agent:
                return
           async for event in self.agent.run(message):
                if event.type == AgentEventType.TEXT_DELTA:
                    content = event.data.get("content","")

async def run(messages: dict[str,any]):
     pass

@click.command()
@click.argument("prompt", required=False)
def main(prompt: str | None):
    cli = CLI()
    # messages = [{'role': 'user','content': prompt or "What's up"}]
    if prompt:
         asyncio.run(cli.run_single(prompt))
    asyncio.run(run(messages))
   
main()
