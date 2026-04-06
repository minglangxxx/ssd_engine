from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    return_code: int
    success: bool


class Executor(ABC):
    @abstractmethod
    def run(self, command: str, timeout: int = 300) -> CommandResult:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
