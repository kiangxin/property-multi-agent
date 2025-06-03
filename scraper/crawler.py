#!/usr/bin/env python3
"""
Property Web Crawler

This module implements a web crawler for real estate properties from EdgeProp.
It extracts property information from listing pages and individual property pages,
using both CSS selectors and LLM-based extraction strategies.
"""

import asyncio
import logging
import os
import json
from typing import Dict, List, Optional, Set
from pprint import pprint
from datetime import datetime

from dotenv import load_dotenv
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig, BrowserConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy

from utils.data_cleaner import DataCleaner
from utils.data_saver import DataSaver
from utils.url_handler import URLHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration settings
CONFIG = {
    "base_url": "https://www.edgeprop.my/buy/kuala-lumpur/all-residential",
    "max_pages": 20,  # Maximum number of pages to crawl
    "output_file": "properties",  # Base filename without extension
    "delay_between_pages": 2,  # Delay between page crawls (seconds)
    "delay_between_properties": 1,  # Delay between property detail crawls (seconds)
}


class Property(BaseModel):
    """
    Data model for property descriptions extracted by the LLM.
    """
    description: str
    floorSize: int
    numberOfBedrooms: int
    numberOfBathrooms: int
    propertyType: str
    lotType : str


# CSS Selectors for property listings
PROPERTY_LISTING_SCHEMA = {
    "name": "Property Extractor",
    "baseSelector": "div.css-1tjb2q6",
    "fields": [
        {"name": "property_desc", "selector": "p.agent-listing-desc", "type": "text"},
        {"name": "address", "selector": "div.listing-address", "type": "text"},
        {"name": "price", "selector": "div.listing-price", "type": "text"},
        {"name": "agent", "selector": "p.agent-name", "type": "text"},
        {"name": "link", "selector": "a.text-decoration-none", "type": "attribute", "attribute": "href"}
    ],
}


def get_llm_strategy() -> LLMExtractionStrategy:
    """
    Create and configure the LLM extraction strategy.
    
    Returns:
        Configured LLM extraction strategy
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set")
    
    return LLMExtractionStrategy(
        provider="openai/gpt-4o-mini",
        api_token=api_key,
        schema=Property.model_json_schema(),
        extraction_type="schema",
        instruction=(
            """
            Step 1: Extract the property description and transform it into a well-structured, human-readable paragraph.
            - Use examples to illustrate the desired output format, such as: 'Luxury modern 3 storey bungalow with a private swimming pool located in Country Heights, Kajang, Selangor. The property is fully furnished and features 6 + 1 bedrooms and 8 bathrooms. It has a built-up area of 7,531 sqft and a land area of 6,368 sqft.'

            Step 2: Extract the property details as following required fields:
            - propertyType
            - floorSize
            - numberOfBedrooms
            - numberOfBathrooms
            - lotType
            
            """
        ),
        input_format="markdown",
        verbose=True,
    )

async def crawl_property_detail(
    crawler: AsyncWebCrawler, 
    llm_strategy: LLMExtractionStrategy, 
    session_id: str,
    property_url: str
) -> Optional[List[Dict]]:
    """
    Crawl a property's detail page to extract additional information.
    """
    js_commands = [
        # Scroll to ensure the show more button is in view
        "window.scrollTo(0, document.body.scrollHeight);",
        # Click the show more button and wait for content to load
        """
        (async () => {
            // Find the show more button using precise selector
            const showMoreButton = document.querySelector('div.showmore-btn.d-flex > div:first-child');
            
            if (showMoreButton && showMoreButton.textContent.trim() === 'Show more') {
                // Create proper mouse event
                const clickEvent = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                
                // Dispatch event on the actual clickable element
                showMoreButton.dispatchEvent(clickEvent);
                
                // Wait for content expansion
                await new Promise(resolve => {
                    const observer = new MutationObserver(() => {
                        const content = document.querySelector('pre.description-content');
                        if (content && !content.textContent.includes('...')) {
                            observer.disconnect();
                            resolve();
                        }
                    });
                    
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true
                    });
                    
                    // Fallback timeout
                    setTimeout(resolve, 2000);
                });
            }
        })();
        """
    ]
    
    config = CrawlerRunConfig(
        # js_code=js_commands,
        session_id = session_id
    )

    try:
        logger.info(f"Crawling details for: {property_url}")
        result = await crawler.arun(
            url=property_url,
            extraction_strategy=llm_strategy,
            # config=config,
            cache_mode=CacheMode.BYPASS,
    
        )
        
        # pprint(result.extracted_content)
        if result.success:
            description = json.loads(result.extracted_content)
            return description
        else:
            logger.warning(f"Failed to extract content from {property_url}")
        return None
    except Exception as e:
        logger.error(f"Error crawling detail page {property_url}: {e}")
        return None


class PropertyCrawler:
    """Main crawler class for property listings."""
    
    def __init__(self, config: Dict):
        """Initialize crawler with configuration."""
        self.config = config
        self.data_cleaner = DataCleaner()
        self.data_saver = DataSaver(self.data_cleaner)
        self.url_handler = URLHandler()
        self.seen_properties: Set[str] = set()
    
    async def crawl_pages(self) -> None:
        """
        Main crawling function that iterates through property listing pages
        and extracts data from both listing and detail pages.
        """
        page_number = 12
        all_properties = []

        # Create CSS-based extraction strategy for property listings
        extraction_strategy = JsonCssExtractionStrategy(PROPERTY_LISTING_SCHEMA, verbose=True)

        logger.info(f"Starting crawler with base URL: {self.config['base_url']}")
        
        while page_number <= self.config["max_pages"]:
            current_url = f"{self.config['base_url']}?page={page_number}"
            logger.info(f"Crawling page {page_number}: {current_url}")

            session_id = "scrape_listings_session"

            async with AsyncWebCrawler(config=BrowserConfig(light_mode=True)) as crawler:
                try:
                    # Get property listings from the current page
                    result = await crawler.arun(
                        url=current_url,
                        extraction_strategy=extraction_strategy,
                        cache_mode=CacheMode.BYPASS,
                        session_id=session_id
                    )

                    if not result.success:
                        logger.error(f"Failed to crawl page {page_number}")
                        break

                    properties = json.loads(result.extracted_content)
                    logger.info(f"Found {len(properties)} properties on page {page_number}")

                    # Filter out properties we've already seen
                    new_properties = []
                    for prop in properties:
                        relative_url = prop.get('link')
                        if relative_url:
                            full_url = self.url_handler.get_full_url(relative_url)
                            if relative_url not in self.seen_properties and self.url_handler.is_valid_url(full_url):
                                prop['link'] = full_url
                                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                prop['crawled_at'] = current_time
                                new_properties.append(prop)

                    if not new_properties:
                        logger.info("No new properties found. Stopping crawl.")
                        break

                    # Create LLM extraction strategy for property details
                    llm_strategy = get_llm_strategy()

                    # Process each property's detail page
                    for prop in new_properties:
                        property_url = prop.get('link')
                        if property_url and self.url_handler.is_valid_url(property_url):
                            # Get additional details from the property's page
                            details = await crawl_property_detail(crawler, llm_strategy, session_id, property_url)

                            if details:
                                # Merge listing and detail information
                                combined_data = {**prop}
                                if isinstance(details, list) and len(details) > 0:
                                    description_obj = details[0]
                                    if 'description' in description_obj:
                                        combined_data['agent_desc'] = description_obj['description']
                                        combined_data['propertyType'] = description_obj['propertyType']
                                        combined_data['floorSize'] = description_obj['floorSize']
                                        combined_data['numberOfBedrooms'] = description_obj['numberOfBedrooms']
                                        combined_data['numberOfBathrooms'] = description_obj['numberOfBathrooms']
                                        combined_data['lotType'] = description_obj['lotType']

                                pprint(combined_data)
                                all_properties.append(combined_data)
                                self.seen_properties.add(property_url)

                            # Delay between property detail requests
                            await asyncio.sleep(self.config["delay_between_properties"])

                    logger.info(f"Page {page_number}: Added {len(new_properties)} new properties with details")

                    # Save progress after each page
                    self.data_saver.save_all(all_properties, self.config["output_file"])

                    page_number += 1
                    await asyncio.sleep(self.config["delay_between_pages"])

                except Exception as e:
                    logger.error(f"Error on page {page_number}: {e}", exc_info=True)
                    break

        logger.info(f"Crawling completed. Total properties collected: {len(all_properties)}")

async def main() -> None:
    """Main entry point for the crawler application."""
    logger.info("Starting property crawler")
    try:
        crawler = PropertyCrawler(CONFIG)
        await crawler.crawl_pages()
    except Exception as e:
        logger.error(f"Unhandled exception in crawler: {e}", exc_info=True)
    logger.info("Crawler finished")


if __name__ == "__main__":
    asyncio.run(main())