import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

logger = logging.getLogger("severus.agents")


class AgentResult(BaseModel):
    agent_name: str
    success: bool
    data: Dict[str, Any]
    message: str
    steps_taken: int = 1


class BaseAgent(ABC):
    """
    Abstract Base Agent for Severus AI Assistant Agent Architecture.
    Enforces tool execution bounds, step limits, timeout safeguards,
    and security boundary checks.
    """

    def __init__(self, name: str, description: str, max_steps: int = 5):
        self.name = name
        self.description = description
        self.max_steps = max_steps

    @abstractmethod
    async def execute(self, task_input: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute agent task workflow."""
        pass

    def validate_security_boundary(self, action_type: str, speaker_status: str = "VERIFICATION_UNAVAILABLE") -> bool:
        """
        Security Gate: Validates if an action is allowed for the given speaker_status.
        Computer control and sensitive desktop operations REQUIRE AUTHORIZED_OWNER.
        """
        if action_type in ["computer_control", "execute_desktop", "access_private_memory"]:
            if speaker_status != "AUTHORIZED_OWNER":
                logger.warning(f"Security Gate Blocked: '{action_type}' for speaker_status='{speaker_status}'")
                return False
        return True
