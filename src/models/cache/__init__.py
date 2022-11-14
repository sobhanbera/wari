import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from pydantic import validate_arguments

from src.helpers.console import console
from src.models.cache.ssdb_database import SsdbDatabase
from src.models.exceptions import MissingInformationError
from src.models.return_.cache_return import CacheReturn
from src.wcd_base_model import WcdBaseModel

if TYPE_CHECKING:
    from src.models.wikimedia.wikipedia.reference.generic import WikipediaReference

logger = logging.getLogger(__name__)


class Cache(WcdBaseModel):
    ssdb: Optional[SsdbDatabase]

    @validate_arguments
    def add_page(self, wikipedia_article: Any, wcdqid: str):
        logger.debug("add_page: Running")
        if self.ssdb:
            if wikipedia_article.md5hash is not None and wcdqid is not None:
                # if type(reference.wikicitations_qid) is not str:
                #     raise ValueError(f"{reference.wikicitations_qid} is not of type str")
                logger.debug(f"Trying to set the value: {wcdqid}")
                return self.ssdb.set_value(key=wikipedia_article.md5hash, value=wcdqid)
            else:
                raise ValueError("did not get what we need")
        else:
            raise ValueError("self.ssdb was None")

    @validate_arguments
    def add_reference(
        self,
        reference,  # type: WikipediaReference
        wcdqid: str,
    ) -> Any:
        logger.debug("add_reference: Running")
        if self.ssdb:
            if reference.md5hash is not None and wcdqid is not None:
                # if type(reference.wikicitations_qid) is not str:
                #     raise ValueError(f"{reference.wikicitations_qid} is not of type str")
                logger.debug(f"Trying to set the value: {wcdqid}")
                result = self.ssdb.set_value(key=reference.md5hash, value=wcdqid)
                logger.debug(f"Got {result} from SSDB")
                # raise DebugExit()
                return result
            else:
                raise ValueError("did not get what we need")
        else:
            raise ValueError("self.ssdb was None")

    @validate_arguments
    def add_website(
        self,
        reference,  # type: WikipediaReference
        wcdqid: str,
    ):
        logger.debug("add_website: Running")
        if self.ssdb:
            if (
                reference.first_level_domain_of_url_hash is not None
                and wcdqid is not None
            ):
                logger.debug(f"Trying to set the value: {wcdqid}")
                return self.ssdb.set_value(
                    key=reference.first_level_domain_of_url_hash, value=wcdqid
                )
            else:
                raise ValueError("did not get what we need")
        else:
            raise ValueError("self.ssdb was None")

    # TODO refactor into one generic lookup function?
    def check_page_and_get_wikibase_qid(self, wikipedia_article) -> CacheReturn:
        """We get binary from SSDB so we decode it"""
        if self.ssdb:
            if wikipedia_article.md5hash is not None:
                # https://stackoverflow.com/questions/55365543/
                response = self.ssdb.get_value(key=wikipedia_article.md5hash)
                if response is None:
                    return CacheReturn()
                else:
                    return CacheReturn(item_qid=str(response.decode("UTF-8")))
            else:
                raise MissingInformationError("md5hash was None")
        else:
            raise ValueError("self.ssdb was None")

    @validate_arguments
    def check_reference_and_get_wikibase_qid(
        self, reference  # type: WikipediaReference
    ) -> CacheReturn:
        """We get binary from SSDB so we decode it"""
        if self.ssdb:
            if reference.md5hash is not None:
                # https://stackoverflow.com/questions/55365543/
                response = self.ssdb.get_value(key=reference.md5hash)
                if response is None:
                    return CacheReturn()
                else:
                    return CacheReturn(item_qid=str(response.decode("UTF-8")))
            else:
                raise ValueError("md5hash was None")
        else:
            raise ValueError("self.ssdb was None")

    @validate_arguments
    def check_website_and_get_wikibase_qid(
        self, reference  # type: WikipediaReference
    ) -> CacheReturn:
        """We get binary from SSDB so we decode it"""
        if self.ssdb:
            if reference.first_level_domain_of_url_hash is not None:
                # https://stackoverflow.com/questions/55365543/
                response = self.ssdb.get_value(
                    key=reference.first_level_domain_of_url_hash
                )
                if response is None:
                    return CacheReturn()
                else:
                    return CacheReturn(item_qid=str(response.decode("UTF-8")))
            else:
                # Not all references have urls so we fail silently
                return CacheReturn()
        else:
            raise ValueError("self.ssdb was None")

    @validate_arguments
    def connect(self, host: str = "127.0.0.1", port: int = 8888):
        # Connect to the SSDB
        self.ssdb = SsdbDatabase(host=host, port=port)
        # try:
        self.ssdb.connect()
        # except:
        #    logger.error("error connection to SSDB")

    @validate_arguments
    def delete_key(self, key: str):
        if self.ssdb:
            return self.ssdb.delete(key=key)
        else:
            raise ValueError("self.ssdb was None")

    def flush_database(self):
        """Deprecated method"""
        raise DeprecationWarning("This has been deprecated since 2.1.0-alpha3.")
        # if self.ssdb:
        #     result = self.ssdb.flush_database()
        #     logger.debug(f"result from SSDB: {result}")
        #     console.print("Done flushing the SSDB database")
        # else:
        #     raise ValueError("self.ssdb was None")

    def get_cache_information(self):
        if self.ssdb:
            result = self.ssdb.get_info()
            console.print(result)
        else:
            raise ValueError("self.ssdb was None")

    @validate_arguments
    def lookup(self, key: str):
        if self.ssdb:
            return self.ssdb.get_value(key=key)
        else:
            raise ValueError("self.ssdb was None")

    def lookup_title_or_wdqid_last_updated(self, key: str) -> float:
        """This looks up the last update date
        of a given title in a
        given Wikimediasite"""
        if self.ssdb:
            try:
                return float(self.ssdb.get_value(key=key))
            except TypeError:
                return 0.0
        else:
            raise ValueError("self.ssdb was None")

    def set_title_or_wdqid_last_updated(self, key: str) -> Any:
        """This sets the update timestamp of an entity"""
        if self.ssdb:
            return self.ssdb.set_value(
                key=key, value=str(datetime.timestamp(datetime.now()))
            )
        else:
            raise ValueError("self.ssdb was None")