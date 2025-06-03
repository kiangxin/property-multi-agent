from typing import Dict, Optional, List
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
import os
import json
import traceback
class WebSearchAgent:
    """Agent for performing web searches to augment property information using GPT-4's search capabilities."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4o-search-preview",  
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Define search integration prompt
        self.prompt = PromptTemplate(
            input_variables=["query", "location"],
            template="""
            You are a property information specialist with access to real-time web search.

            User Query: {query}
            Location: {location}

            Instructions:
            - Perform a web search to answer the user's query as accurately as possible.
            - If the query appears to be asking for property RECOMMENDATIONS or LISTINGS (e.g., "property listings in Bangsar under RM500k"):
                1. Focus on finding SPECIFIC PROPERTIES that match the criteria
                2. Return 3-5 SPECIFIC property recommendations with name, price, location, and brief details
                3. Format each property recommendation on a new line with property name, price, and details
                4. Include factual details only - pricing, location, square footage, etc.
            - If the query asks for a specific fact (e.g., developer, year built, address, layout):
                1. Extract that fact from the most reliable sources you find
                2. Return it directly in the "answer" field
            - If you find the answer, return it in the "answer" field below. If not, set "answer" to null and explain in "summary".
            - Always provide a brief "summary" of what you found (or didn't find).
            - List the top 1-3 sources (URLs or site names) you used in the "sources" field.
            - Set "confidence" to "high" if multiple reputable sources agree, "medium" if only one source, "low" if unclear or conflicting.
            - Return ONLY the following JSON object and nothing else:

            {{
              "answer": "...",        // The direct answer to the user's query, or null if not found
              "summary": "...",       // A 1-2 sentence summary of what you found (or why not found)
              "sources": ["...", "..."], // List of URLs or site names
              "confidence": "high" | "medium" | "low"
            }}
            """
        )
        

       
        self.chain = self.prompt | self.llm
    
    async def search_web(self, query: str, location: str = None) -> Dict:
        """
        Perform a web search for property-related information using GPT-4's search capabilities.
        
        Args:
            query: The search query related to property information
            location: Optional location context to refine the search
            
        Returns:
            Dict containing organized information from the search results
        """
        try:
            # Process and organize search results using GPT-4
            result = await self.chain.ainvoke({
                "query": query,
                "location": location if location else "Not specified"
            })
            
            try:
                parsed = json.loads(result.content)
            except Exception:
                parsed = {"raw": result.content}
            
            return {
                "web_search_results": parsed,
                "query": query
            }
            
        except Exception as e:
            print(traceback.format_exc())
            print(f'Error during web search: {e}')
            # return {
            #     "error": str(e),
            #     "web_search_results": "Could not perform web search at this time.",
            #     "query": query
            # }