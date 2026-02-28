from config.config import Config
from client.response import parse_tool_call_arguments
from client.response import ToolCallDelta, ToolCall
from openai import APIConnectionError, APIError
from typing import AsyncGenerator
from client.response import StreamEventType
from client.response import StreamEvent
from client.response import TokenUsage
from client.response import TextDelta
from typing import Any
from openai import AsyncOpenAI, RateLimitError
import asyncio


class LLMClient:
    def __init__(self, config:Config) -> None:
        self._client: AsyncOpenAI | None = None
        self._max_retries:int = 8
        self.config = config
        # print(config)
    
    def get_client(self) ->AsyncOpenAI:
        if self._client is None:
            # print(self.config)
            # print(f"DEBUG api_key={self.config.api_key!r}")
            # print(f"DEBUG base_url={self.config.base_url!r}")
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return self._client
    
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    def _build_tools(self,tools: list[dict[str, Any]] | None = None):
        return [
             {
                'type': 'function',
                'function': {
                     'name':tool['name'],
                     'description':tool.get('description',''),
                     'parameters':tool.get('parameters',{
                        'type':'object',
                        'properties':{},
                     }) 
                }
             }

             for tool in tools
        ]

    async def chat_completion(self, 
                              messages: list[dict[str, Any]], 
                              tools: list[dict[str, Any]] | None = None,
                              stream:bool = True) -> AsyncGenerator[StreamEvent, None]:

        client = self.get_client();
        kwargs = {
                "model": self.config.model_name,  # Automatically selects best available model
                "messages": messages,
                "stream": stream,
        }   

        if tools:
             kwargs["tools"] = self._build_tools(tools)
             kwargs["tool_choice"] = "auto"


        for attempt in range(self._max_retries + 1):
            try:
                if stream: 
                    async for event in self._stream_response(client, kwargs):
                        yield event
                else:
                    event = await self._non_stream_response(client, kwargs)
                    yield event
                return

            except RateLimitError as e:
                if attempt <  self._max_retries:
                    delay =  (2 ** attempt)
                    print(f"Rate limit hit. Retrying in {delay} seconds... (attempt {attempt + 1}/{self._max_retries})")
                    await asyncio.sleep(delay)
                else:
                     yield StreamEvent(
                         type=StreamEventType.ERROR,
                         error="Max retries exceeded",
                     )
                     return
            except APIConnectionError as e: 
                if attempt <  self._max_retries:
                    delay =  (2 ** attempt)
                    print(f"API Connection Error. Retrying in {delay} seconds... (attempt {attempt + 1}/{self._max_retries})")
                    await asyncio.sleep(delay)
                else:
                     yield StreamEvent(
                         type=StreamEventType.ERROR,
                         error="Connection Error",
                     )
                     return
            except APIError as e: 
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error="API Error",
                )
                return


            
    
    async def _stream_response(self,client:AsyncOpenAI, kwargs: dict[str,Any])->AsyncGenerator[StreamEvent, None]:
          
          response = await client.chat.completions.create(**kwargs)
          usage: TokenUsage | None = None
          finish_reason: str | None = None
          tool_calls: dict[int, dict[str, Any]] = {}


          async for chunk in response:
             if hasattr(chunk, 'usage') and chunk.usage:
                usage=TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=chunk.usage.prompt_tokens_details.cached_tokens
                )
             if not chunk.choices:
                 continue
            
             choice = chunk.choices[0]
             delta = choice.delta

             if choice.finish_reason: 
                 finish_reason = choice.finish_reason
             
             if delta.content:
                 yield StreamEvent(
                     type=StreamEventType.TEXT_DELTA,
                     text_delta=TextDelta(delta.content),
                 ) 
             if delta.tool_calls:
                 for tool_call_delta in delta.tool_calls:
                     idx = tool_call_delta.index
                     if idx not in tool_calls:
                        tool_calls[idx] = {
                            'id': tool_call_delta.id or "",
                            'name': '',
                            'arguments': '',
                        }
                     if tool_call_delta.function: 
                            if tool_call_delta.function.name:
                                 tool_calls[idx]['name'] = tool_call_delta.function.name
                                 yield StreamEvent(
                                     type=StreamEventType.TOOL_CALL_START,
                                     tool_call_delta=ToolCallDelta(
                                         call_id=tool_calls[idx]['id'],
                                         name=tool_calls[idx]['name'],
                                     ),
                                 )
                            if tool_call_delta.function.arguments:
                                  tool_calls[idx]['arguments'] += tool_call_delta.function.arguments
                                  yield StreamEvent(
                                      type=StreamEventType.TOOL_CALL_DELTA,
                                      tool_call_delta=ToolCallDelta(
                                          call_id=tool_calls[idx]['id'],
                                          name= tool_calls[idx]['name'],
                                          arguments=tool_calls[idx]['arguments'],
                                      ),
                                  )    

          for idx, tc in tool_calls.items():
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call=ToolCall(
                    call_id=tc['id'],
                    name=tc['name'],
                    arguments=parse_tool_call_arguments(tc['arguments']),
                ),
            )
          yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            text_delta=None,
            finish_reason=finish_reason,
            usage=usage
        )
         
               

    async def _non_stream_response(self, client:AsyncOpenAI, kwargs: dict[str,Any]) -> StreamEvent:
        max_retries = 3
        base_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message = choice.message

                text_delta=None
                usage= None

                if message.content:
                   text_delta = TextDelta(content=message.content)
                
                tool_calls: list[ToolCall] = []
                if message.tool_calls:
                    for tc in message.tool_calls:
                        tool_calls.append(
                            ToolCall(
                                call_id=tc.id,
                                name=tc.function.name,
                                arguments=parse_tool_call_arguments(tc.function.arguments),
                            )
                        )

                if response.usage:
                    usage = TokenUsage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        cached_tokens=response.usage.prompt_tokens_details.cached_tokens
                    )
                else:
                     usage = None

                return StreamEvent(
                    type=StreamEventType.MESSAGE_COMPLETE,
                    text_delta=text_delta,
                    finish_reason=choice.finish_reason,
                    usage=usage
                )
            except RateLimitError as e:
                if attempt == max_retries - 1:
                    # Last attempt, re-raise the error
                    raise
                # Exponential backoff: 2s, 4s, 8s...
                delay = base_delay * (2 ** attempt)
                print(f"Rate limit hit. Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)

                