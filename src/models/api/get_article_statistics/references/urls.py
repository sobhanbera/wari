from typing import Optional

from pydantic import BaseModel

from src.models.api.get_article_statistics.references.urls_aggregates import (
    UrlsAggregates,
)


class Urls(BaseModel):
    """The purpose of this class is to model the statistics
    the user wants from the get_article_statistics endpoint

    We use BaseModel to avoid the cache attribute"""

    agg: Optional[UrlsAggregates] = None
    urls_found: bool = False
    # The details are now found on each reference instead
    # details: List[WikipediaUrl] = []

    class Config:
        extra = "forbid"
