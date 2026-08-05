from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel

class ArticlePayload(BaseModel):
    title: str
    markdownContent: str
    htmlContent: str
    tags: List[str]
    isDraft: Optional[bool] = False
    existingPostId: Optional[str] = None

class PublishResult(BaseModel):
    platform: str
    postId: str
    url: str
    publishedAt: str

class BlogPublisher(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def publish(self, article: ArticlePayload, dry_run: bool) -> PublishResult:
        pass

    @abstractmethod
    def validate_auth(self) -> bool:
        pass
