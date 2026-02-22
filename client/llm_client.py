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
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._max_retries:int = 3
     
    
    def get_client(self) ->AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key='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',
                base_url='https://openrouter.ai/api/v1',
            )
        return self._client
    
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def chat_completion(self, 
                              messages: list[dict[str, Any]], 
                              stream:bool = True) -> AsyncGenerator[StreamEvent, None]:

        client = self.get_client();
        kwargs = {
                "model": "z-ai/glm-4.5-air:free",  # Automatically selects best available model
                "messages": messages,
                "stream": stream,
        }                      
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

                if message.content:
                   text_delta = TextDelta(content=message.content)

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