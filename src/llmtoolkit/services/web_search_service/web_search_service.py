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

class SearchModel(BaseModel):
    query: str = Field(..., description="The search query string.")
    region: Optional[str] = Field("wt-wt", description="Region code for localized results (e.g., 'wt-wt', 'us-en').")
    safesearch: Optional[str] = Field('moderate', description="Safe search level: 'on', 'moderate', or 'off'.")
    timelimit: Optional[str] = Field(None, description="Time frame for results: 'd' (day), 'w' (week), 'm' (month), or 'y' (year).")
    max_results: Optional[int] = Field(10, description="Maximum number of search results to return.")


class ImageSearchModel(BaseModel):
    query: str = Field(..., description="The image search query string.")
    region: Optional[str] = Field("wt-wt", description="Region code for localized image results (e.g., 'wt-wt', 'us-en').")
    safesearch: Optional[str] = Field('moderate', description="Safe search level: 'on', 'moderate', or 'off'.")
    timelimit: Optional[str] = Field(None, description="Time frame for image results: 'Day', 'Week', 'Month', or 'Year'.")
    size: Optional[str] = Field(None, description="Filter images by size: 'Small', 'Medium', 'Large', or 'Wallpaper'.")
    color: Optional[str] = Field(None, description="Filter images by color (e.g., 'color', 'Monochrome', 'Red').")
    type_image: Optional[str] = Field(None, description="Filter images by type: 'photo', 'clipart', 'gif', 'transparent', or 'line'.")
    layout: Optional[str] = Field(None, description="Filter images by layout: 'Square', 'Tall', or 'Wide'.")
    license_image: Optional[str] = Field(None, description="Filter images by license: 'any', 'Public', 'Share', 'ShareCommercially', 'Modify', or 'ModifyCommercially'.")
    max_results: Optional[int] = Field(10, description="Maximum number of image results to return.")

class NewsSearchModel(BaseModel):
    query: str = Field(..., description="The news search query string.")
    region: Optional[str] = Field("wt-wt", description="Region code for localized news results (e.g., 'wt-wt', 'us-en').")
    safesearch: Optional[str] = Field('moderate', description="Safe search level: 'on', 'moderate', or 'off'.")
    timelimit: Optional[str] = Field(None, description="Time frame for news results: 'd' (day), 'w' (week), or 'm' (month).")
    max_results: Optional[int] = Field(10, description="Maximum number of news results to return.")

class WebScrapeModel(BaseModel):
    url: str = Field(..., description="The URL of the web page to scrape.")

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

    def get_web_search_agent_system_message(self) -> str:
        """Returns the system message for the web search agent."""
        system_message = """You are a highly capable assistant equipped with web search functionalities. Your purpose is to help users find information efficiently by performing web searches.

**Your Objectives:**

1. **Comprehend User Requests:** Carefully understand the user's questions or information needs.

2. **Utilize Provided Functions:** Use the functions effectively by supplying the appropriate parameters based on the user's request.

3. **Provide Clear Responses:** Present the information in a concise and understandable manner, summarizing results when necessary.

**Instructions:**

- If additional information is needed to perform a function, politely ask the user for clarification.
- Focus on being accurate, helpful, and efficient in assisting the user.
"""
        return system_message

    @expose_for_llm
    def search(self, data: SearchModel) -> str:
        """Performs a web search based on the provided query and parameters.

        Returns:
            str: A formatted string containing the search results.
        """
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

    @expose_for_llm
    def image_search(self, data: ImageSearchModel) -> str:
        """Performs an image search based on the provided query and parameters.

        Returns:
            str: A formatted string containing the image search results.
        """
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

    @expose_for_llm
    def news_search(self, data: NewsSearchModel) -> str:
        """Performs a news search based on the provided query and parameters.

        Returns:
            str: A formatted string containing the news search results.
        """
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
                    f"Source: {result.get('source', 'No Source')}\n\n"
                )
            return formatted_results

    # TODO: Beautify the text, maybe remove the beautifulsoup dependency
    @expose_for_llm
    def web_scrape(self, data: WebScrapeModel) -> str:
        """Scrapes and returns the text content from the provided URL.

        Returns:
            str: The textual content extracted from the web page.
        """
        response = requests.get(data.url)
        # Parse all text
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        return text
