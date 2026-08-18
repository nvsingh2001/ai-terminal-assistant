from dataclasses import dataclass
from typing import Any

from cli_agent.commands.base import CommandContext
from cli_agent.commands.clear_cmd import ClearCommand
from cli_agent.commands.dispatcher import CommandDispatcher
from cli_agent.commands.exit_cmd import ExitCommand
from cli_agent.commands.forget_cmd import ForgetCommand
from cli_agent.commands.help_cmd import HelpCommand
from cli_agent.commands.memory_cmd import MemoryCommand
from cli_agent.commands.model_cmd import ModelCommand
from cli_agent.commands.remember_cmd import RememberCommand
from cli_agent.commands.skills_cmd import SkillsCommand
from cli_agent.commands.verbose_cmd import VerboseCommand
from cli_agent.core.config_manager import ConfigManager, config_manager
from cli_agent.core.engine.langgraph_engine import LangGraphAgentEngine
from cli_agent.core.interfaces.engine import IAgentEngine
from cli_agent.memory.manager import TriTierMemoryManager, tri_tier_memory
from cli_agent.services.memory_manager import ConversationMemory, session_memory
from cli_agent.skills.registry import SkillRegistry, skill_registry


@dataclass
class ServiceContainer:
    """
    Dependency Injection Container.
    Assembles and manages life cycles of core services, engines, long-term memory, and command dispatchers.
    """

    config_manager: ConfigManager
    skill_registry: SkillRegistry
    memory_store: ConversationMemory
    tri_tier_memory: TriTierMemoryManager
    engine: IAgentEngine
    dispatcher: CommandDispatcher

    @classmethod
    def create_default(cls, console: Any, prompt_session: Any) -> "ServiceContainer":
        """Factory method to instantiate and wire all dependencies."""
        cfg = config_manager
        skills = skill_registry
        mem = session_memory
        lt_mem = tri_tier_memory

        # Instantiate LangGraphAgentEngine with configured verbose mode & long-term memory
        engine = LangGraphAgentEngine(
            model_name=cfg.config.model_name,
            skill_registry=skills,
            memory_store=mem,
            long_term_memory=lt_mem,
            verbose=cfg.config.verbose,
        )

        # Create Command Context
        ctx = CommandContext(
            prompt_session=prompt_session,
            config_manager=cfg,
            skill_registry=skills,
            memory_store=mem,
            console=console,
            engine=engine,
            tri_tier_memory=lt_mem,
        )

        # Instantiate and register Command Dispatcher
        dispatcher = CommandDispatcher(ctx)
        dispatcher.register(ModelCommand())
        dispatcher.register(SkillsCommand())
        dispatcher.register(MemoryCommand())
        dispatcher.register(RememberCommand())
        dispatcher.register(ForgetCommand())
        dispatcher.register(VerboseCommand())
        dispatcher.register(ClearCommand())
        dispatcher.register(HelpCommand())
        dispatcher.register(ExitCommand())

        return cls(
            config_manager=cfg,
            skill_registry=skills,
            memory_store=mem,
            tri_tier_memory=lt_mem,
            engine=engine,
            dispatcher=dispatcher,
        )
