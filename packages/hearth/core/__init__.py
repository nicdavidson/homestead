"""
Hearth Core - Infrastructure for self-improving AI entities
"""

from .config import Config, get_config
from .state import StateDB, get_state
from .costs import CostTracker, BudgetStatus
from .identity import Identity
from .sessions import SessionManager, SubagentSession, get_session_manager
from .tasks import TaskManager, get_task_manager
from .proposals import ProposalManager, get_proposal_manager
from .nightshift import NightshiftManager, get_nightshift_manager
from .reflections import ReflectionManager, NamingCeremony, get_reflection_manager, get_naming_ceremony
from .projects import ProjectManager, get_project_manager
from .skills import SkillManager, get_skill_manager
from .api import create_api, run_api_server
from . import tools
# router.py deprecated - using tool-based agent spawning instead

# Alias for backward compatibility
State = StateDB

__all__ = [
    "Config", "get_config",
    "State", "StateDB", "get_state",
    "CostTracker", "BudgetStatus",
    "Identity",
    "SessionManager", "SubagentSession", "get_session_manager",
    "TaskManager", "get_task_manager",
    "ProposalManager", "get_proposal_manager",
    "NightshiftManager", "get_nightshift_manager",
    "ReflectionManager", "NamingCeremony", "get_reflection_manager", "get_naming_ceremony",
    "ProjectManager", "get_project_manager",
    "SkillManager", "get_skill_manager",
    "create_api", "run_api_server",
    "tools",
]
