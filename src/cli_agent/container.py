from dataclasses import dataclass
from typing import Any

from cli_agent.core.config_manager import ConfigManager, config_manager
from cli_agent.skills.registry import SkillRegistry, skill_registry
from cli_agent.services.memory_manager import ConversationMemory, session_memory
from cli_agent.core.engine.pydantic_engine import PydanticAgentEngine
from cli_agent.commands.base import CommandContext
from cli_agent.commands.dispatcher import CommandDispatcher
from cli_agent.commands.model_cmd import ModelCommand
from cli_agent.commands.skills_cmd import SkillsCommand
from cli_agent.commands.clear_cmd import ClearCommand
from cli_agent.commands.help_cmd import HelpCommand
from cli_agent.commands.exit_cmd import ExitCommand
from cli_agent.commands.verbose_cmd import VerboseCommand

@dataclass
class ServiceContainer:
    """
    Dependency Injection Container.
    Assembles and manages life cycles of core services, engines, and command dispatchers.
    """
    config_manager: ConfigManager
    skill_registry: SkillRegistry
    memory_store: ConversationMemory
    engine: PydanticAgentEngine
    dispatcher: CommandDispatcher

    @classmethod
    def create_default(cls, console: Any, prompt_session: Any) -> "ServiceContainer":
        """Factory method to instantiate and wire all dependencies."""
        cfg = config_manager
        skills = skill_registry
        mem = session_memory

        # Instantiate PydanticAgentEngine with configured verbose mode
        engine = PydanticAgentEngine(
            model_name=cfg.config.model_name,
            skill_registry=skills,
            memory_store=mem,
            verbose=cfg.config.verbose
        )

        # Create Command Context
        ctx = CommandContext(
            prompt_session=prompt_session,
            config_manager=cfg,
            skill_registry=skills,
            memory_store=mem,
            console=console,
            engine=engine
        )

        # Instantiate and register Command Dispatcher
        dispatcher = CommandDispatcher(ctx)
        dispatcher.register(ModelCommand())
        dispatcher.register(SkillsCommand())
        dispatcher.register(VerboseCommand())
        dispatcher.register(ClearCommand())
        dispatcher.register(HelpCommand())
        dispatcher.register(ExitCommand())

        return cls(
            config_manager=cfg,
            skill_registry=skills,
            memory_store=mem,
            engine=engine,
            dispatcher=dispatcher
        )
