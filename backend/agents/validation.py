from typing import Dict, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
import os
import json

class ValidationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Define prompt for extracting filters and user context
        self.prompt = PromptTemplate(
            input_variables=["query"],
            template="""
            Extract structured filters and user context from the following property query:
            
            User Query: {query}
            
            Please:
            1. Extract key filters:
               - Location
               - Property type
               - Price range
               - Number of bedrooms
               - Number of bathrooms
               - Size requirements
               - Other specific features
            
            2. Extract user context:
               - Preferred areas
               - Budget range
               - Must-have features
               - Any other preferences or constraints
            
            Return the results in JSON format with two keys: "filters" and "user_context".
            """
        )
        
        # Create RunnableSequence instead of LLMChain
        self.chain = self.prompt | self.llm
    
    async def validate(self, query: str) -> Dict:
        """
        Validate the property query and extract structured filters and user context.
        """
        # Extract filters and user context from the query
        try:
            extraction_result = await self.chain.ainvoke({"query": query})
            json_str = extraction_result.content
            if json_str.startswith('```json'):
                json_str = json_str.split('```json')[1].split('```')[0].strip()

            # Parse the JSON result from the message content
            extracted_data = json.loads(json_str)
            # print(f'Cleaned JSON data: {extracted_data}')

            filters = {
                k.lower().replace(' ', '_'): v 
                for k, v in extracted_data.get("filters", {}).items() 
                if v is not None
            }
            
            user_context = {
                k.lower().replace(' ', '_'): v 
                for k, v in extracted_data.get("user_context", {}).items() 
                if v is not None
            }
            
            return {
                "extracted_filters": filters,
                "extracted_user_context": user_context
            }
        
        except (json.JSONDecodeError, KeyError) as e:
            print(f'JSON parsing error: {str(e)}')
            return {
                "extracted_filters": {},
                "extracted_user_context": {}
            }