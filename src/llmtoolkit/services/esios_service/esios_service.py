import logging
from datetime import datetime
from typing import Optional, List
import requests
from pydantic import BaseModel, Field

from llmtoolkit.llm_interface.utils import expose_for_llm

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class SearchIndicatorModel(BaseModel):
    query: str = Field(..., description="Search query to filter indicators by name or description")

class GetIndicatorDataModel(BaseModel):
    indicator_id: int = Field(..., description="ID of the indicator to retrieve")
    start_date: datetime = Field(..., description="Start date for the data retrieval")
    end_date: datetime = Field(..., description="End date for the data retrieval")
    time_trunc: str = Field("hour", description="Time truncation (hour, day, month, year)")
    time_agg: str = Field("sum", description="Time aggregation (sum, avg), default is sum, generation should use sum and price should use avg")
    #geo_id: Optional[int] = Field(None, description="Optional geographical ID for the indicator")

class EsiosService:
    def __init__(self, api_token: str):
        """Initializes the connection to the ESIOS API."""
        self.base_url = "https://api.esios.ree.es"
        if not api_token:
            raise ValueError("API token is required to access ESIOS API.")
        self.headers = {
            'x-api-key': api_token,
        }
        self.indicators_cache = None

    def get_agent_system_message(self) -> str:
        """Returns the system message for the ESIOS Agent."""
        esios_agent_system_message = """You are an ESIOS Assistant designed to help users retrieve energy data from the Spanish electricity system.

**Your Objectives:**

1. **Understand User Requests:** Carefully interpret user instructions related to searching indicators and retrieving data.
2. **Provide Clear Responses:** Present the results or information in a clear and concise manner.

**Instructions:**

- If additional information is needed to perform a function, ask the user for clarification.
- If you need clarification to identify the right indicator, ask the user for more details.
- Help users find the right indicators by suggesting relevant search terms.
- Ensure date ranges are valid when retrieving indicator data.

"""
        return esios_agent_system_message

    def _fetch_all_indicators(self) -> List[dict]:
        """Fetches all indicators from ESIOS API and caches them."""
        if self.indicators_cache is None:
            try:
                response = requests.get(f"{self.base_url}/indicators", headers=self.headers)
                response.raise_for_status()
                self.indicators_cache = response.json()['indicators']
            except Exception as e:
                logger.error(f"Failed to fetch indicators: {str(e)}")
                raise
        return self.indicators_cache

    @expose_for_llm
    def search_indicators(self, data: SearchIndicatorModel) -> str:
        """Searches for indicators matching the query in their name or description.

        The search is case-insensitive and looks for partial matches in both the name
        and description of the indicators.
        """
        try:
            indicators = self._fetch_all_indicators()
            query = data.query.lower()

            matching_indicators = [
                {
                    'id': ind['id'],
                    'name': ind['name'],
                    'short_name': ind['short_name'],
                    'description': ind.get('description'),
                }
                for ind in indicators
                if query in ind['name'].lower() or 
                   query in ind.get('description', '').lower()
            ]

            if not matching_indicators:
                return "No indicators found matching your query."

            result = f"Found {len(matching_indicators)} matching indicators:\n"
            for ind in matching_indicators:
                result += (
                    f"ID: {ind['id']}\n"
                    f"Name: {ind['name']}\n"
                    f"Short name: {ind['short_name']}\n"
                    f"Description: {ind['description']}\n"
                )

            return result
        except Exception as e:
            logger.error(f"Failed to search indicators: {str(e)}")
            return f"Failed to search indicators: {str(e)}"

    @expose_for_llm
    def get_indicator_data(self, data: GetIndicatorDataModel) -> str:
        """Retrieves data for a specific indicator within the given date range.

        The data can be truncated by hour, day, month, or year using the time_trunc parameter.
        """
        start_date = data.start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date = data.end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        endpoint = (f"{self.base_url}/indicators/{data.indicator_id}"
                    f"?start_date={start_date}&end_date={end_date}"
                    f"&time_trunc={data.time_trunc}"
                    f"&time_agg={data.time_agg}")

        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()

        indicator_data = response.json()

        # Format the response
        result = f"Data for indicator {data.indicator_id}:\n"
        result += f"Name: {indicator_data['indicator']['name']}\n"
        result += f"Values: {len(indicator_data['indicator']['values'])} data points\n"

        # Add some sample values
        for value in indicator_data['indicator']['values']:
            result += f"Datetime: {value['datetime']}, Value: {value['value']}, Geo name: {value["geo_name"]}\n "
        return result
