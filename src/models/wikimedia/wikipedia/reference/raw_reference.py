"""
Copyright Dennis Priskorn where not stated otherwise
"""
import logging
from typing import TYPE_CHECKING, List, Union

import mwparserfromhell  # type: ignore
from mwparserfromhell.nodes import Tag  # type: ignore
from mwparserfromhell.wikicode import Wikicode  # type: ignore

import config
from src.models.exceptions import MissingInformationError
from src.models.wikibase import Wikibase
from src.models.wikimedia.wikipedia.reference.template import WikipediaTemplate
from src.wcd_base_model import WcdBaseModel

if TYPE_CHECKING:
    from src.models.wikimedia.wikipedia.reference.generic import WikipediaReference

logger = logging.getLogger(__name__)


# TODO this does not scale at all if we want multi-wiki support :/
# TODO convert to abstract class and make an 2 implementations
#  WikipediaRawCitationReference and WikipediaRawGeneralReference
class WikipediaRawReference(WcdBaseModel):
    """This class handles determining the type of reference and parse the templates from the raw reference

    This contains code from pywikibot 7.2.0 textlib.py to avoid forking the whole thing
    """

    # TODO rewrite to accept Tag or Wikicode
    wikicode: Union[Tag, Wikicode]  # output from mwparserfromhell
    templates: List[WikipediaTemplate] = []
    plain_text_in_reference: bool = False
    citation_template_found: bool = False
    cs1_template_found: bool = False
    citeq_template_found: bool = False
    isbn_template_found: bool = False
    url_template_found: bool = False
    bare_url_template_found: bool = False
    multiple_templates_found: bool = False
    testing: bool = False
    wikibase: Wikibase
    extraction_done: bool = False
    is_named_reference: bool = False
    is_general_reference: bool = False
    # TODO add new optional attribute wikicode: Optional[Wikicode]
    #  which contains the parsed output of the general reference line

    class Config:
        arbitrary_types_allowed = True

    @property
    def is_citation_reference(self):
        if self.is_general_reference:
            return False
        else:
            return True

    @property
    def get_wikicode_as_string(self):
        return str(self.wikicode)

    @property
    def first_template_name(self) -> str:
        """Helper method. We use this information in the graph to know which
        template the information in the reference came from"""
        if self.templates:
            return str(self.templates[0].name)
        else:
            return ""

    @property
    def number_of_templates(self) -> int:
        return len(self.templates)

    def __extract_templates_and_parameters_from_raw_reference__(self) -> None:
        """Helper method"""
        logger.debug("__extract_templates_and_parameters_from_raw_reference__: running")
        self.__extract_raw_templates__()
        self.__extract_and_clean_template_parameters__()

    def __extract_raw_templates__(self) -> None:
        """Extract the templates from self.wikicode"""
        logger.debug("__extract_raw_templates__: running")
        if not self.wikicode:
            raise MissingInformationError("self.wikicode was None")
        if isinstance(self.wikicode, str):
            raise MissingInformationError("self.wikicode was str")
        # Skip named references like "<ref name="INE"/>"
        wikicode_string = str(self.wikicode)
        if self.is_citation_reference and "</ref>" not in wikicode_string:
            logger.info(f"Skipping named reference with no content {wikicode_string}")
            self.is_named_reference = True
        else:
            logger.debug(f"Extracting templates from: {self.wikicode}")
            if isinstance(self.wikicode, Tag):
                # contents is needed here to get a Wikicode object
                raw_templates = self.wikicode.contents.ifilter_templates(
                    matches=lambda x: not x.name.lstrip().startswith("#"),
                    recursive=True,
                )
            else:
                raw_templates = self.wikicode.ifilter_templates(
                    matches=lambda x: not x.name.lstrip().startswith("#"),
                    recursive=True,
                )
            count = 0
            for raw_template in raw_templates:
                count += 1
                self.templates.append(WikipediaTemplate(raw_template=raw_template))
            if count == 0:
                logger.debug(f"Found no templates in {self.wikicode}")

    def __extract_and_clean_template_parameters__(self) -> None:
        """We only extract and clean if exactly one template is found"""
        logger.debug("__extract_and_clean_template_parameters__: running")
        if self.number_of_templates == 1:
            [template.extract_and_prepare_parameters() for template in self.templates]

    def extract_and_determine_reference_type(self) -> None:
        """Helper method"""
        self.__extract_templates_and_parameters_from_raw_reference__()
        self.__determine_reference_type__()
        self.extraction_done = True

    def get_finished_wikipedia_reference_object(self) -> "WikipediaReference":
        """Make a WikipediaReference based on the extracted information"""
        logger.debug("get_finished_wikipedia_reference_object: running")
        if not self.extraction_done:
            self.extract_and_determine_reference_type()
        from src.models.wikimedia.wikipedia.reference.generic import WikipediaReference

        if self.number_of_templates:
            reference = WikipediaReference(**self.templates[0].parameters)
        else:
            reference = WikipediaReference()
        # propagate attributes
        reference.raw_reference = self
        reference.cache = self.cache
        reference.wikibase = self.wikibase
        reference.finish_parsing_and_generate_hash(testing=self.testing)
        return reference

    def __determine_reference_type__(self):
        """We want to determine which type of reference this is

        Design limit: we only support one template for now"""
        if self.number_of_templates:
            logger.info(
                f"Found {self.number_of_templates} template(s) in {self.wikicode}"
            )
            if self.number_of_templates == 1:
                if self.__detect_any_plain_text__():
                    # We have a clean template reference like {{citeq|Q1}}
                    self.plain_text_in_reference = False
                else:
                    self.plain_text_in_reference = True
                if self.__detect_citation_template__():
                    self.citation_template_found = True
                else:
                    self.citation_template_found = False
                if self.__detect_cs1_template__():
                    self.cs1_template_found = True
                else:
                    self.cs1_template_found = False
                if self.__detect_citeq_template__():
                    self.citeq_template_found = True
                else:
                    self.citeq_template_found = False
                if self.__detect_isbn_template__():
                    self.isbn_template_found = True
                else:
                    self.isbn_template_found = False
                if self.__detect_url_template__():
                    self.url_template_found = True
                else:
                    self.url_template_found = False
                if self.__detect_bare_url_template__():
                    self.bare_url_template_found = True
                else:
                    self.bare_url_template_found = False
            else:
                self.multiple_templates_found = True
                message = (
                    f"We found {self.number_of_templates} templates in "
                    f"{self.wikicode} -> templates: {self.templates} which is currently not supported"
                )
                logger.error(message)
                self.__log_to_file__(
                    message=message, file_name="multiple_template_error.log"
                )

    def __detect_any_plain_text__(self) -> bool:
        """A clean template reference has no text outside the {{ and }}"""
        if not self.templates[0].raw_template:
            raise MissingInformationError("self.templates[0].raw_template was None")
        if str(self.templates[0].raw_template).startswith("{{") and self.templates[
            0
        ].raw_template.endswith("}}"):
            return True
        else:
            return False

    def __detect_citation_template__(self) -> bool:
        if self.templates[0].name in config.citation_template:
            return True
        else:
            return False

    def __detect_cs1_template__(self) -> bool:
        if self.templates[0].name in config.cs1_templates:
            return True
        else:
            return False

    def __detect_citeq_template__(self):
        if self.templates[0].name in config.citeq_templates:
            return True
        else:
            return False

    def __detect_isbn_template__(self):
        if self.templates[0].name in config.isbn_template:
            return True
        else:
            return False

    def __detect_url_template__(self):
        if self.templates[0].name in config.url_template:
            return True
        else:
            return False

    def __detect_bare_url_template__(self):
        if config.bare_url_regex in self.templates[0].name:
            return True
        else:
            return False