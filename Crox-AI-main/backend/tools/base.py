from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ValidationError

from models.schemas import ToolResult


class Tool(ABC):
    """Base class every tool must implement.

    Gemini never executes code directly -- it only ever selects `name` and
    produces `arguments`, which the executor validates against `input_model`
    before `run()` is called. This is the single choke point that keeps
    Gemini's output from becoming arbitrary code execution.
    """

    name: str
    description: str
    input_model: type[BaseModel]

    def validate_arguments(self, arguments: dict[str, Any]) -> BaseModel:
        try:
            return self.input_model(**arguments)
        except ValidationError as exc:
            raise ToolArgumentError(str(exc)) from exc

    @abstractmethod
    async def run(self, arguments: BaseModel) -> ToolResult:
        ...

    def spec(self) -> dict[str, Any]:
        """Compact description handed to Gemini so it knows what it can call."""
        return {
            "name": self.name,
            "description": self.description,
            "arguments_schema": self.input_model.model_json_schema(),
        }


class ToolArgumentError(ValueError):
    pass
