import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field

from llmtoolkit.llm_interface.utils import expose_for_llm

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class SearchQueryModel(BaseModel):
    query: str = Field(..., description="Search query string")
    region: Optional[str] = Field("wt-wt", description="Region code (e.g., 'wt-wt', 'us-en')")
    safesearch: Optional[str] = Field('moderate', description="Level of safe search ('on', 'moderate', 'off')")
    timelimit: Optional[str] = Field(None, description="Time period to filter results ('d', 'w', 'm', 'y')")
    max_results: Optional[int] = Field(10, description="Maximum number of results to return")

class ImageSearchQueryModel(BaseModel):
    query: str = Field(..., description="Image search query string")
    region: Optional[str] = Field("wt-wt", description="Region code (e.g., 'wt-wt', 'us-en')")
    safesearch: Optional[str] = Field('moderate', description="Level of safe search ('on', 'moderate', 'off')")
    timelimit: Optional[str] = Field(None, description="Time period to filter results ('Day', 'Week', 'Month', 'Year')")
    size: Optional[str] = Field(None, description="Image size filter ('Small', 'Medium', 'Large', 'Wallpaper')")
    color: Optional[str] = Field(None, description="Image color filter (e.g., 'color', 'Monochrome', 'Red')")
    type_image: Optional[str] = Field(None, description="Image type filter ('photo', 'clipart', 'gif', 'transparent', 'line')")
    layout: Optional[str] = Field(None, description="Image layout filter ('Square', 'Tall', 'Wide')")
    license_image: Optional[str] = Field(None, description="License filter ('any', 'Public', 'Share', 'ShareCommercially', 'Modify', 'ModifyCommercially')")
    max_results: Optional[int] = Field(10, description="Maximum number of results to return")

class NewsSearchQueryModel(BaseModel):
    query: str = Field(..., description="News search query string")
    region: Optional[str] = Field("wt-wt", description="Region code (e.g., 'wt-wt', 'us-en')")
    safesearch: Optional[str] = Field('moderate', description="Level of safe search ('on', 'moderate', 'off')")
    timelimit: Optional[str] = Field(None, description="Time period to filter results ('d', 'w', 'm')")
    max_results: Optional[int] = Field(10, description="Maximum number of results to return")

class WebScrapeModel(BaseModel):
    url: str = Field(..., description="URL to scrape")

class WebSearchService:

    DEFAULT_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'es-ES,es;q=0.9',
    'priority': 'u=0, i',
    'referer': 'https://duckduckgo.com/',
    'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
}

    def get_duckduckgo_agent_system_message(self) -> str:
        """Returns the system message for the DuckDuckGo Agent."""
        system_message = """**System Message: DuckDuckGo Agent LLM**
You are an intelligent assistant designed to help users search the web efficiently using DuckDuckGo.
Please adhere to the following guidelines:

1. **Understand User Intent**: Carefully analyze user queries to accurately determine their search needs.

2. **Perform Searches**: Use DuckDuckGo to perform web searches and retrieve relevant results.

3. **Provide Accurate Information**: Ensure that search results are relevant and accurate.

4. **Enhance Productivity**: Assist users by providing concise summaries of search results.

5. **Maintain User Privacy**: Respect user privacy and confidentiality.

6. **Be Polite and Professional**: Communicate in a courteous and professional manner.

By following these guidelines, you will provide valuable assistance to users, helping them find the information they need effectively.
"""
        return system_message

    @expose_for_llm
    def search(self, data: SearchQueryModel) -> str:
        """Performs a web search using DuckDuckGo."""
        try:
            ddgs = DDGS(headers=self.DEFAULT_HEADERS)
            results_generator = ddgs.text(
                keywords=data.query,
                region=data.region,
                safesearch=data.safesearch,
                timelimit=data.timelimit,
                max_results=data.max_results
            )
            results = list(results_generator)
            if not results:
                return f"No results found for query: {data.query}"
            else:
                # Return formatted results
                formatted_results = ''
                for idx, result in enumerate(results, start=1):
                    formatted_results += (
                        f"Result {idx}:\n"
                        f"Title: {result.get('title', 'No Title')}\n"
                        f"Snippet: {result.get('body', 'No Snippet')}\n"
                        f"URL: {result.get('href', 'No URL')}\n\n"
                    )
                return formatted_results
        except Exception as e:
            logger.error(f"Failed to perform search: {str(e)}")
            return f"Failed to perform search: {str(e)}"

    @expose_for_llm
    def image_search(self, data: ImageSearchQueryModel) -> str:
        """Performs an image search using DuckDuckGo."""
        try:
            ddgs = DDGS(headers=self.DEFAULT_HEADERS)
            results_generator = ddgs.images(
                keywords=data.query,
                region=data.region,
                safesearch=data.safesearch,
                timelimit=data.timelimit,
                size=data.size,
                color=data.color,
                type_image=data.type_image,
                layout=data.layout,
                license_image=data.license_image,
                max_results=data.max_results
            )
            results = list(results_generator)
            if not results:
                return f"No image results found for query: {data.query}"
            else:
                # Return formatted image search results
                formatted_results = ''
                for idx, result in enumerate(results, start=1):
                    formatted_results += (
                        f"Image Result {idx}:\n"
                        f"Title: {result.get('title', 'No Title')}\n"
                        f"Image URL: {result.get('image', 'No Image URL')}\n"
                        f"Thumbnail URL: {result.get('thumbnail', 'No Thumbnail URL')}\n"
                        f"Source: {result.get('source', 'No Source')}\n\n"
                    )
                return formatted_results
        except Exception as e:
            logger.error(f"Failed to perform image search: {str(e)}")
            return f"Failed to perform image search: {str(e)}"

    @expose_for_llm
    def news_search(self, data: NewsSearchQueryModel) -> str:
        """Performs a news search using DuckDuckGo."""
        try:
            ddgs = DDGS(headers=self.DEFAULT_HEADERS)
            results_generator = ddgs.news(
                keywords=data.query,
                region=data.region,
                safesearch=data.safesearch,
                timelimit=data.timelimit,
                max_results=data.max_results
            )
            results = list(results_generator)
            if not results:
                return f"No news results found for query: {data.query}"
            else:
                # Return formatted news search results
                formatted_results = ''
                for idx, result in enumerate(results, start=1):
                    formatted_results += (
                        f"News Result {idx}:\n"
                        f"Title: {result.get('title', 'No Title')}\n"
                        f"Snippet: {result.get('body', 'No Snippet')}\n"
                        f"URL: {result.get('url', 'No URL')}\n"
                        f"Date: {result.get('date', 'No Date')}\n\n"
                    )
                return formatted_results
        except Exception as e:
            logger.error(f"Failed to perform news search: {str(e)}")
            return f"Failed to perform news search: {str(e)}"

    # TODO: Beautify the text, maybe remove the beautifulsoup dependency
    @expose_for_llm
    def web_scrape(self, data: WebScrapeModel) -> str:
        """Performs a web scrape given a url."""
        response = requests.get(data.url)
        # Parse all text
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        return text
