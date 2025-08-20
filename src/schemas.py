from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class Institution(BaseModel):
    model_config = ConfigDict(
        frozen=False,  # set True for immutability
        validate_assignment=True,  # runtime type safety on attribute set
        str_strip_whitespace=True,  # trims incoming strings
    )

    name: str
    id: Optional[str] = None

    @classmethod
    def from_json(cls, json_obj: Dict[str, Any]) -> "Institution":
        inst_name = ""
        inst_id = None

        if "institution" in json_obj:
            institution = json_obj.get("institution", {}) or {}
            inst_name = institution.get("display_name", "") or ""
            inst_id = institution.get("id")
        elif "raw_affiliation_string" in json_obj:
            inst_name = json_obj.get("raw_affiliation_string", "") or ""
            ids = json_obj.get("institution_ids")
            if ids and len(ids) >= 1:
                inst_id = ids[0]
        elif "id" in json_obj:
            inst_name = json_obj.get("display_name", "")
            inst_id = json_obj.get("id")

        return cls(name=inst_name, id=inst_id)

    @classmethod
    def from_list(cls, json_list: List[dict]) -> List["Institution"]:
        return [cls.from_json(item) for item in json_list]

    @staticmethod
    def list_to_json(institutions: List["Institution"]) -> List[dict]:
        return [institution.model_dump(exclude_none=True) for institution in institutions]

    def __str__(self) -> str:
        return self.model_dump_json(exclude_none=True)


class Author(BaseModel):
    model_config = ConfigDict(
        frozen=False,               # set True for immutability
        validate_assignment=True,   # runtime type safety on attribute set
        str_strip_whitespace=True,  # trims incoming strings
    )

    name: str
    id: Optional[str] = None
    institutions: List[Institution] = Field(default_factory=list)

    @classmethod
    def from_json(cls, json_obj: Dict[str, Any]) -> "Author":
        # Get author name and id
        author_info = json_obj.get("author", {}) or {}
        author_id = author_info.get("id") or json_obj.get("id")
        author_name = author_info.get("display_name") or json_obj.get("display_name") or ""

        # Get institutions from affiliations
        author_institutions = Institution.from_list(json_obj.get("affiliations", []) or [])

        return cls(name=author_name, id=author_id, institutions=author_institutions)

    @classmethod
    def from_list(cls, json_list: List[dict]) -> List["Author"]:
        return [cls.from_json(item) for item in json_list]

    @staticmethod
    def list_to_json(authors: List["Author"]) -> List[dict]:
        return [author.model_dump(exclude_none=True) for author in authors]

    def __str__(self) -> str:
        return self.model_dump_json(exclude_none=True)


class Work(BaseModel):
    model_config = ConfigDict(
        frozen=False,  # set True for immutability
        validate_assignment=True,  # runtime type safety on attribute set
        str_strip_whitespace=True,  # trims incoming strings
    )

    title: str = None
    ids: Dict[str, str] = Field(default_factory=dict)
    cited_by_count: Optional[int] = None
    authors: List[Author] = Field(default_factory=list)
    publication_date: Optional[str] = None
    preferred_fulltext_url: Optional[str] = None

    @classmethod
    def from_json(cls, json_obj: Dict[str, Any]) -> "Work":
        # Gets title and page urls
        title = json_obj.get("title") or json_obj.get("display_name") or ""

        # Prioritize Open Access url
        preferred_fulltext_url = (json_obj.get("best_oa_location", {}) or {}).get("pdf_url")
        if preferred_fulltext_url is None:
            preferred_fulltext_url = (json_obj.get("best_oa_location", {}) or {}).get("landing_page_url")
        if preferred_fulltext_url is None:
            preferred_fulltext_url = (json_obj.get("primary_location", {}) or {}).get("pdf_url")
        if preferred_fulltext_url is None:
            preferred_fulltext_url = (json_obj.get("primary_location", {}) or {}).get("landing_page_url")

        # Gets individual authors of the work
        authors = Author.from_list(json_obj.get("authorships", []) or [])
        return cls(
            title=title,
            ids=json_obj.get("ids", {}) or {},
            authors=authors,
            cited_by_count=json_obj.get("cited_by_count"),
            publication_date=json_obj.get("publication_date"),
            preferred_fulltext_url=preferred_fulltext_url
        )

    @classmethod
    def from_list(cls, json_list: List[dict]) -> List["Work"]:
        return [cls.from_json(item) for item in json_list]

    @staticmethod
    def list_to_json(works: List["Work"]) -> List[dict]:
        return [work.model_dump(exclude_none=True) for work in works]

    def __str__(self) -> str:
        return self.model_dump_json(exclude_none=True)


class PageResult(BaseModel):
    data: List[Union[Institution, Author, Work, dict]] = Field(default_factory=list)
    total_count: Optional[int] = None
    per_page: int
    page: int
    has_next: Optional[bool] = None


class ListResult(BaseModel):
    data: List[str] = Field(default_factory=list)
    count: Optional[int] = None

