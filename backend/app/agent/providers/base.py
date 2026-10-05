from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable

class LLMProvider(ABC):
    @abstractmethod
    def investigate(self, repo_path: str, repo_name: str, bug_report: str, tools: List[Callable]) -> Dict[str, Any]:
        """
        Run the investigation loop using the specified deterministic tools.
        Returns the structured investigation result.
        """
        pass
