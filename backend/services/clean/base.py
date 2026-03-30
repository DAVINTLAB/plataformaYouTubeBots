from abc import ABC, abstractmethod

from models.collection import Comment


class SelectorBase(ABC):
    """Interface para critérios de seleção de usuários suspeitos (OCP).

    Cada implementação recebe comentários agrupados por usuário e retorna
    o conjunto de author_channel_ids selecionados.
    """

    @abstractmethod
    def select(self, user_comments: dict[str, list[Comment]]) -> set[str]: ...
