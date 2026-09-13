from abc import ABC, abstractmethod
from app.models.schemas import ProviderHealth, StatementExtraction


class ModelClient(ABC):
    @abstractmethod
    async def health(self) -> ProviderHealth: ...

    @abstractmethod
    async def extract(self, page_text: list[tuple[int, str]]) -> StatementExtraction: ...
