import os
from typing import Literal, Optional

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError, ResourceError
from api_requests import RequestAPI, validate_url_with_ssrf_guard
from utils import sanitize_search_text
import httpx
from schemas import Work, Author, Institution, PageResult, ListResult
import logging
from dotenv import load_dotenv, find_dotenv


# Initialize env variables
if not os.getenv("OPENALEX_MAILTO"):
    load_dotenv(find_dotenv(usecwd=True))
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "placeholder_email@gmail.com")


# Initialize Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Define the FastMCP server
mcp = FastMCP(
    name="ScholarScope Tools",
    instructions="""
        When retrieving paper content, always use the 'preferred_fulltext_url' field
        and access it via the fetch_fulltext tool for full text retrieval.
        Only use other links if 'preferred_fulltext_url' is missing, invalid, or fallback is required.
    """
)


@mcp.tool
async def search_papers(
        query: str,
        search_by: Literal["default", "title", "title_and_abstract"] = "default",
        sort_by: Literal["relevance_score", "cited_by_count", "publication_date"] = "relevance_score",
        institution_name: Optional[str] = None,
        author_id: Optional[str] = None,
        page: int = 1,
) -> PageResult:
    """
    Searches for academic papers using the OpenAlex API.

    Args:
        query: The search term or keywords to look for in the papers.
        search_by: The field to search in ("default", "title", or "title_and_abstract").
        sort_by: The sorting criteria ("relevance_score", "cited_by_count", or "publication_date").
        institution_name: An optional institution or affiliation name to filter search results.
        author_id: An optional OpenAlex Author ID to filter search results. e.g., "https://openalex.org/A123456789"
        page: The page number of the results to retrieve (default: 1).

    Returns:
        A JSON object containing a list of searched papers+ids, or an error message if the search fails.
    """
    query = sanitize_search_text(query)
    institution_name = sanitize_search_text(institution_name)

    params = {
        "filter": f"{search_by}.search:\"{query}\"",
        "sort": f"{sort_by}:desc",
        "page": page,
        "per_page": 10,
    }
    if institution_name:
        params["filter"] += f",raw_affiliation_strings.search:\"{institution_name}\""
    if author_id:
        params["filter"] += f",authorships.author.id:{author_id}"

    # Fetches search results from the OpenAlex API
    async with RequestAPI("https://api.openalex.org", default_params={"mailto": OPENALEX_MAILTO}) as api:
        logger.info(f"Searching for papers using: query={query}, search_by={search_by}, sort_by={sort_by}, page={page}")
        try:
            result = await api.aget("/works", params=params)

            # Returns a message for when the search results are empty
            if result is None or len(result.get("results", []) or []) == 0:
                error_message = "No works found with the query."
                logger.info(error_message)
                raise ToolError(error_message)

            # Successfully returns the searched papers
            works = Work.from_list(result.get("results", []) or [])
            success_message = f"Found {len(works)} papers."
            logger.info(success_message)

            total_count = (result.get("meta", {}) or {}).get("count")
            if total_count and total_count > params["per_page"] * params["page"]:
                has_next = True
            else:
                has_next = None
            return PageResult(
                data=Work.list_to_json(works),
                total_count=total_count,
                per_page=params["per_page"],
                page=params["page"],
                has_next=has_next
            )
        except httpx.HTTPStatusError as e:
            error_message = f"Request failed with status: {e.response.status_code}"
            logger.error(error_message)
            raise ToolError(error_message)
        except httpx.RequestError as e:
            error_message = f"Network error: {str(e)}"
            logger.error(error_message)
            raise ToolError(error_message)


@mcp.tool
async def search_authors(
        query: str,
        sort_by: Literal["relevance_score", "cited_by_count"] = "relevance_score",
        institution_id: Optional[str] = None,
        page: int = 1,
) -> PageResult:
    """
    Searches for authors using the OpenAlex API.

    Args:
        query: The search name to look for the authors.
        sort_by: The sorting criteria ("relevance_score" or "cited_by_count").
        institution_id: An optional institution id to filter search results. e.g., "https://openalex.org/I123456789"
        page: The page number of the results to retrieve (default: 1).

    Returns:
        A JSON object containing a list of authors+ids, or an error message if the search fails.
    """
    query = sanitize_search_text(query)

    params = {
        "filter": f"default.search:\"{query}\"",
        "sort": f"{sort_by}:desc",
        "page": page,
        "per_page": 10,
    }
    if institution_id:
        params["filter"] += f",affiliations.institution.id:\"{institution_id}\""

    # Fetches search results from the OpenAlex API
    async with RequestAPI("https://api.openalex.org", default_params={"mailto": OPENALEX_MAILTO}) as api:
        logger.info(f"Searching for authors using: query={query}, sort_by={sort_by}, page={page}, institution_id={institution_id}")
        try:
            result = await api.aget("/authors", params=params)

            # Returns a message for when the search results are empty
            if result is None or len(result.get("results", []) or []) == 0:
                error_message = "No authors found with the query."
                logger.info(error_message)
                raise ToolError(error_message)

            # Successfully returns the searched authors
            authors = Author.from_list(result.get("results", []) or [])
            success_message = f"Found {len(authors)} authors."
            logger.info(success_message)

            total_count = (result.get("meta", {}) or {}).get("count")
            if total_count and total_count > params["per_page"] * params["page"]:
                has_next = True
            else:
                has_next = None
            return PageResult(
                data=Author.list_to_json(authors),
                total_count=total_count,
                per_page=params["per_page"],
                page=params["page"],
                has_next=has_next
            )
        except httpx.HTTPStatusError as e:
            error_message = f"Request failed with status: {e.response.status_code}"
            logger.error(error_message)
            raise ToolError(error_message)
        except httpx.RequestError as e:
            error_message = f"Network error: {str(e)}"
            logger.error(error_message)
            raise ToolError(error_message)


@mcp.tool
async def search_institutions(
        query: str,
        sort_by: Literal["relevance_score", "cited_by_count"] = "relevance_score",
        page: int = 1,
) -> PageResult:
    """
    Searches for institutions using the OpenAlex API.

    Args:
        query: The search name to look for the institutions.
        sort_by: The sorting criteria ("relevance_score" or "cited_by_count").
        page: The page number of the results to retrieve (default: 1).

    Returns:
        A JSON object containing a list of institutions+ids, or an error message if the search fails.
    """
    query = sanitize_search_text(query)

    params = {
        "filter": f"default.search:\"{query}\"",
        "sort": f"{sort_by}:desc",
        "page": page,
        "per_page": 10,
    }

    # Fetches search results from the OpenAlex API
    async with RequestAPI("https://api.openalex.org", default_params={"mailto": OPENALEX_MAILTO}) as api:
        logger.info(f"Searching for authors using: query={query}, sort_by={sort_by}, page={page}")
        try:
            result = await api.aget("/institutions", params=params)

            # Returns a message for when the search results are empty
            if result is None or len(result.get("results", []) or []) == 0:
                error_message = "No institutions found with the query."
                logger.info(error_message)
                raise ToolError(error_message)

            # Successfully returns the searched papers
            institutions = Institution.from_list(result.get("results", []) or [])
            success_message = f"Found {len(institutions)} institution(s)."
            logger.info(success_message)

            total_count = (result.get("meta", {}) or {}).get("count")
            if total_count and total_count > params["per_page"] * params["page"]:
                has_next = True
            else:
                has_next = None
            return PageResult(
                data=Institution.list_to_json(institutions),
                total_count=total_count,
                per_page=params["per_page"],
                page=params["page"],
                has_next=has_next
            )
        except httpx.HTTPStatusError as e:
            error_message = f"Request failed with status: {e.response.status_code}"
            logger.error(error_message)
            raise ToolError(error_message)
        except httpx.RequestError as e:
            error_message = f"Network error: {str(e)}"
            logger.error(error_message)
            raise ToolError(error_message)


@mcp.tool
async def papers_by_author(
        author_id: str,
        sort_by: Literal["cited_by_count", "publication_date"] = "cited_by_count",
        page: int = 1,
) -> PageResult:
    """
    Searches for academic papers by a particular author using the OpenAlex API.

    Args:
        author_id: An OpenAlex Author ID of target author. e.g., "https://openalex.org/A123456789"
        sort_by: The sorting criteria ("cited_by_count", or "publication_date").
        page: The page number of the results to retrieve (default: 1).

    Returns:
        A JSON object containing a list of papers+ids by the specified author, or an error message if the search fails.
    """
    params = {
        "filter": f"authorships.author.id:{author_id}",
        "sort": f"{sort_by}:desc",
        "page": page,
        "per_page": 10,
    }

    # Fetches search results from the OpenAlex API
    async with RequestAPI("https://api.openalex.org", default_params={"mailto": OPENALEX_MAILTO}) as api:
        logger.info(f"Searching for papers using: author_id={author_id}, sort_by={sort_by}, page={page}")
        try:
            result = await api.aget("/works", params=params)

            # Returns a message for when the search results are empty
            if result is None or len(result.get("results", []) or []) == 0:
                error_message = f"No works found for author_id={author_id}."
                logger.info(error_message)
                raise ToolError(error_message)

            # Successfully returns the searched papers
            works = Work.from_list(result.get("results", []) or [])
            success_message = f"Found {len(works)} papers by author_id={author_id}."
            logger.info(success_message)

            total_count = (result.get("meta", {}) or {}).get("count")
            if total_count and total_count > params["per_page"] * params["page"]:
                has_next = True
            else:
                has_next = None
            return PageResult(
                data=Work.list_to_json(works),
                total_count=total_count,
                per_page=params["per_page"],
                page=params["page"],
                has_next=has_next
            )
        except httpx.HTTPStatusError as e:
            error_message = f"Request failed with status: {e.response.status_code}"
            logger.error(error_message)
            raise ToolError(error_message)
        except httpx.RequestError as e:
            error_message = f"Network error: {str(e)}"
            logger.error(error_message)
            raise ToolError(error_message)


@mcp.tool
async def referenced_works_in_paper(
        paper_id: str,
) -> ListResult:
    """
    Gets referenced works used in the specified paper using the OpenAlex API.
    Note: May return empty if the paper's full text is inaccessible.

    Args:
        paper_id: An OpenAlex Work ID of the target paper. e.g., "https://openalex.org/W123456789"

    Returns:
        A JSON object containing a list of paper ids used in the work, or an error message if the fetch fails.
    """

    # Fetches search results from the OpenAlex API
    async with RequestAPI("https://api.openalex.org", default_params={"mailto": OPENALEX_MAILTO}) as api:
        logger.info(f"Fetching referenced works for paper_id={paper_id}")
        try:
            result = await api.aget(f"/works/{paper_id}")

            # Returns a message for when the search results are empty
            if result is None or len(result.get("referenced_works", []) or []) == 0:
                error_message = f"No referenced works found for paper_id={paper_id}."
                logger.info(error_message)
                raise ToolError(error_message)

            # Successfully returns the searched papers
            works = result.get("referenced_works", []) or []
            success_message = f"Retrieved {len(works)} referenced works for paper_id={paper_id}."
            logger.info(success_message)
            return ListResult(data=works, count=len(works))
        except httpx.HTTPStatusError as e:
            error_message = f"Request failed with status: {e.response.status_code}"
            logger.error(error_message)
            raise ToolError(error_message)
        except httpx.RequestError as e:
            error_message = f"Network error: {str(e)}"
            logger.error(error_message)
            raise ToolError(error_message)


@mcp.tool
async def related_works_of_paper(
        paper_id: str,
) -> ListResult:
    """
    Gets related works used to the specified paper using the OpenAlex API.
    Note: May return empty if the paper's full text is inaccessible.

    Args:
        paper_id: An OpenAlex Work ID of the target paper. e.g., "https://openalex.org/W123456789"

    Returns:
        A JSON object containing a list of paper ids related to the work, or an error message if the fetch fails.
    """

    # Fetches search results from the OpenAlex API
    async with RequestAPI("https://api.openalex.org", default_params={"mailto": OPENALEX_MAILTO}) as api:
        logger.info(f"Fetching related_works works for paper_id={paper_id}")
        try:
            result = await api.aget(f"/works/{paper_id}")

            # Returns a message for when the search results are empty
            if result is None or len(result.get("related_works", []) or []) == 0:
                error_message = f"No related_works works found for paper_id={paper_id}."
                logger.info(error_message)
                raise ToolError(error_message)

            # Successfully returns the searched papers
            works = result.get("related_works", []) or []
            success_message = f"Retrieved {len(works)} related_works works for paper_id={paper_id}."
            logger.info(success_message)
            return ListResult(data=works, count=len(works))
        except httpx.HTTPStatusError as e:
            error_message = f"Request failed with status: {e.response.status_code}"
            logger.error(error_message)
            raise ToolError(error_message)
        except httpx.RequestError as e:
            error_message = f"Network error: {str(e)}"
            logger.error(error_message)
            raise ToolError(error_message)


@mcp.tool
async def works_citing_paper(
        paper_id: str,
        sort_by: Literal["cited_by_count", "publication_date"] = "cited_by_count",
        page: int = 1,
) -> PageResult:
    """
    Retrieves works that cite a given paper from the OpenAlex API.

    Args:
        paper_id: An OpenAlex Work ID of target paper. e.g., "https://openalex.org/W123456789"
        sort_by: The sorting criteria ("cited_by_count", or "publication_date").
        page: The page number of the results to retrieve (default: 1).

    Returns:
        A JSON object containing a list of papers+ids citing the specific paper, or an error message if the retrieval fails.
    """
    params = {
        "filter": f"cites:{paper_id}",
        "sort": f"{sort_by}:desc",
        "page": page,
        "per_page": 10,
    }

    # Fetches search results from the OpenAlex API
    async with RequestAPI("https://api.openalex.org", default_params={"mailto": OPENALEX_MAILTO}) as api:
        logger.info(f"Searching for works citing paper using: paper_id={paper_id}, sort_by={sort_by}, page={page}")
        try:
            result = await api.aget("/works", params=params)

            # Returns a message for when the search results are empty
            if result is None or len(result.get("results", []) or []) == 0:
                error_message = f"No cites found for paper_id={paper_id}."
                logger.info(error_message)
                raise ToolError(error_message)

            # Successfully returns the searched papers
            works = Work.from_list(result.get("results", []) or [])
            success_message = f"Found {len(works)} cites to paper_id={paper_id}."
            logger.info(success_message)

            total_count = (result.get("meta", {}) or {}).get("count")
            if total_count and total_count > params["per_page"] * params["page"]:
                has_next = True
            else:
                has_next = None
            return PageResult(
                data=Work.list_to_json(works),
                total_count=total_count,
                per_page=params["per_page"],
                page=params["page"],
                has_next=has_next
            )
        except httpx.HTTPStatusError as e:
            error_message = f"Request failed with status: {e.response.status_code}"
            logger.error(error_message)
            raise ToolError(error_message)
        except httpx.RequestError as e:
            error_message = f"Network error: {str(e)}"
            logger.error(error_message)
            raise ToolError(error_message)


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
async def fetch_fulltext(preferred_fulltext_url: str, ctx: Context) -> str:
    """
    Retrieves the contents of a paper or work from its preferred full-text URL and returns
    the response body as plain text.

    Note:
        In some cases, the target content may be paywalled, require authentication, or
        otherwise restrict access. In such situations, the returned output may consist
        of partial content, metadata, or an access notice rather than the complete text.

    Args:
        preferred_fulltext_url: Preferred full-text URL of the paper or work.

    Returns:
        Plaintext representation of the retrieved content. This may be the complete text,
        or a limited excerpt if access to the full resource is restricted.
    """
    # Strip Jina prefix if already present
    jina_prefix = "https://r.jina.ai/"
    if preferred_fulltext_url.startswith(jina_prefix):
        preferred_fulltext_url = preferred_fulltext_url[len(jina_prefix):]
        logger.debug(f"Removed Jina prefix, normalized URL: {preferred_fulltext_url}")

    # Validates to prevent malicious/malformed urls
    if not validate_url_with_ssrf_guard(preferred_fulltext_url):
        error_message = f"Invalid or Disallowed URL: {preferred_fulltext_url}"
        logger.error(error_message)
        await ctx.error(error_message)
        raise ResourceError(error_message)

    async with RequestAPI(jina_prefix[:-1]) as api:
        logger.info(f"Fetching page: url={preferred_fulltext_url}")
        await ctx.info(f"Fetching full-text from the url...")
        try:
            # Fetch contents of the page (wrapped with jina for easy LLM reading)
            result = await api.aget(f"/{preferred_fulltext_url}")
            if result is None:
                error_message = "Response is empty content. Try again later."
                logger.info(error_message)
                await ctx.error(error_message)
                raise ToolError(error_message)

            return result
        except httpx.HTTPStatusError as e:
            error_message = f"Request failed with status: {e.response.status_code}"
            logger.error(error_message)
            await ctx.error(error_message)
            raise ResourceError(error_message)
        except httpx.RequestError as e:
            error_message = f"Network error: {str(e)}"
            logger.error(error_message)
            await ctx.error(error_message)
            raise ResourceError(error_message)


if __name__ == "__main__":
    mcp.run(transport="stdio")
