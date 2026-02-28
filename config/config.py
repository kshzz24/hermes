
from enum import Enum
from typing import Any
from pathlib import Path
from pydantic import BaseModel, Field
import os

class ModelConfig(BaseModel):
     name:str = Field(default="z-ai/glm-4.5-air:free")
     temperature: float = Field(default=1, ge=0.0, le=2.0)
     context_window: int = 256_000

     
class ShellEnvironmentPolicy(BaseModel):
    ignore_default_excludes: bool = False
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["*KEY*", "*TOKEN*", "*SECRET*"]
    )
    set_vars: dict[str, str] = Field(default_factory=dict)


class ApprovalPolicy(str, Enum):
    ON_REQUEST = "on-request"
    ON_FAILURE = "on-failure"
    AUTO = "auto"
    AUTO_EDIT = "auto-edut"
    NEVER = "never"
    YOLO = "yolo"

class HookTrigger(str, Enum):
    BEFORE_AGENT = "before_agent"
    AFTER_AGENT = "after_agent"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    ON_ERROR = "on_error"
class Config(BaseModel): 
     model: ModelConfig = Field(default_factory=ModelConfig)
     cwd:Path = Field(default_factory=Path.cwd)
     shell_environment:ShellEnvironmentPolicy = Field(default_factory=ShellEnvironmentPolicy)
     max_turns:int = 100
     allowed_tools: list[str] | None = Field(
        None,
        description="If set, only these tools will be available to the agent",
    )
     max_tool_output_tokens:int = 50_000
     developers_instructions: str | None = None
     user_instructions: str | None = None
     debug:bool = False
     
     @property
     def api_key(self) -> str | None:
        return os.environ.get("API_KEY")

     @property
     def base_url(self) -> str | None:
            return os.environ.get("BASE_URL", "https://openrouter.ai/api/v1")

     @property
     def model_name(self) -> str:
            return self.model.name

     @model_name.setter
     def model_name(self, value: str) -> None:
            self.model.name = value

     @property
     def temperature(self) -> float:
            return self.model.temperature

     @model_name.setter
     def temperature(self, value: str) -> None:
            self.model.temperature = value

     def validate(self) -> list[str]:
            errors: list[str] = []

            if not self.api_key:
                errors.append("No API key found. Set API_KEY environment variable")

            if not self.cwd.exists():
                errors.append(f"Working directory does not exist: {self.cwd}")

            return errors

     def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")      