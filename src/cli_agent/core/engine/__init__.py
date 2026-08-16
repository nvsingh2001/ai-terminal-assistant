from cli_agent.core.interfaces.engine import IAgentEngine
from cli_agent.core.engine.pydantic_engine import PydanticAgentEngine

# Set DirectAgentEngine alias for backwards compatibility
DirectAgentEngine = PydanticAgentEngine

__all__ = [
    "IAgentEngine",
    "PydanticAgentEngine",
    "DirectAgentEngine"
]
