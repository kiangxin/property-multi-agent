
import os
import pandas as pd
import json
import faiss
import numpy as np

from typing import Dict, List
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from models.schemas import Property
from sentence_transformers import SentenceTransformer

class DataSourceAgent:
    """
    Agent for handling property data source integration and property data retrieval.
    This agent serves as a bridge between the raw property data and the other agents,
    ensuring consistent data access and formatting.
    """
    
    def __init__(self):
        self.excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                      "scraper", "properties.xlsx")
        self.index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                      "backend", "faiss_index")
        # Load data
        self.properties_data = self._load_data()
        self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2') 

        print(self.index_path)
        # Create or load vector store if OpenAI API key is available
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key and self.properties_data:
            self.embeddings = OpenAIEmbeddings()
            if os.path.exists(self.index_path):
                print("Loading FAISS index from disk.")
                self.vector_store = FAISS.load_local(
                    self.index_path, self.embeddings, allow_dangerous_deserialization=True
                )   
            else:
                print("Creating new FAISS index.")
                # print(self.properties_data)
                self.vector_store = FAISS.from_texts(
                    [json.dumps(prop) for prop in self.properties_data],
                    self.embeddings
                )
                if self.vector_store is not None:  # Ensure it's a valid index
                    self.vector_store.save_local("faiss_index")
        else:
            self.vector_store = None
            if not openai_api_key:
                print("Warning: OpenAI API key not found. Vector search capabilities will be limited.")
    
    def _load_data(self) -> List[Dict]:
        """
        Load property data from Excel.
        
        Returns:
            List of property dictionaries
        """
        try:
            if os.path.exists(self.excel_path):
                print(f"Loading property data from Excel: {self.excel_path}")
                df = pd.read_excel(self.excel_path)
                
                # Convert DataFrame to list of dictionaries
                properties = df.replace({np.nan: None}).to_dict('records')
                
                return properties
            else:
                print("Excel file not found.")
                return []
                
        except Exception as e:
            print(f"Error loading property data: {e}")
            return []
        
    async def get_properties(self, filters: Dict = None) -> List[Property]:
        """
        Retrieve properties based on the specified filters.
        
        Args:
            filters: Dictionary of property filters (e.g., location, price range, etc.)
            
        Returns:
            List of Property objects
        """
        if not self.properties_data:
            return []
            
        filtered_properties = self.properties_data
        
        # # Apply filters if provided
        # if filters:
        #     filtered_properties = self._apply_filters(filtered_properties, filters)
        
        # Convert to Property objects
        return [self._to_property_model(prop) for prop in filtered_properties[:10]]  # Limit to 10 for performance
    
    async def search_similar_properties(self, query: str, filters: Dict = None, user_context: Dict = None, top_k: int = 5) -> List[Property]:
        """
        Search for properties similar to the given query using vector similarity.
        
        Args:
            query: The natural language query to search for
            filters: Dictionary of property filters
            user_context: Dictionary of user context
            top_k: Maximum number of properties to return
            
        Returns:
            List of Property objects similar to the query
        """
        if not self.vector_store:
            # Fallback to simple keyword search if vector store is not available
            return await self._keyword_search(query, top_k)
        
        try:
            # Perform vector similarity search
            results = self.vector_store.similarity_search(query, k=top_k)
            
            # Extract property data from results
            similar_properties = []
            for doc in results:
                property_data = json.loads(doc.page_content)
                similar_properties.append(self._to_property_model(property_data))
            
            # Apply additional filtering based on filters and user context
            # if filters or user_context:
            #     similar_properties = self._apply_filters(similar_properties, filters)
            
            return similar_properties
            
        except Exception as e:
            print(f"Error during vector search: {e}")
            return await self._keyword_search(query, top_k)
    
    async def _keyword_search(self, query: str, top_k: int = 5) -> List[Property]:
        """
        Fallback search method using simple keyword matching.
        
        Args:
            query: Search query
            top_k: Maximum number of properties to return
            
        Returns:
            List of matching Property objects
        """
        # Convert query to lowercase for case-insensitive matching
        query_lower = query.lower()
        
        # Simple scoring function: count occurrences of query terms in property data
        def score_property(prop):
            # Convert all string values to lowercase and join
            text = ' '.join([str(v).lower() for v in prop.values() if isinstance(v, str)])
            return sum(term in text for term in query_lower.split())
        
        # Score and sort properties
        scored_properties = [(prop, score_property(prop)) for prop in self.properties_data]
        scored_properties.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k properties
        top_properties = [self._to_property_model(prop) for prop, score in scored_properties[:top_k] if score > 0]
        
        return top_properties
    
    def _to_property_model(self, property_dict: Dict) -> Property:
        """
        Convert property dictionary to Property model.
        
        Args:
            property_dict: Dictionary containing property data
            
        Returns:
            Property model
        """
        # Create a copy of the dictionary to avoid modifying the original
        prop_data = property_dict.copy()
        
        # Ensure required fields exist
        for field in ["property_desc", "address", "asked_price", "agent", "link"]:
            if field not in prop_data or prop_data[field] is None:
                prop_data[field] = ""
        
        # Handle prop_details field
        if "prop_details" not in prop_data:
            # Create prop_details from individual fields
            prop_data["prop_details"] = {
                "propertyType": prop_data.get("property_type", ""),
                "floorSize": prop_data.get("floor_size_sqft", ""),
                "numberOfBedrooms": prop_data.get("num_bedrooms", 0),
                "numberOfBathrooms": prop_data.get("num_bathrooms", 0),
                "lotType": prop_data.get("lot_type", "")
            }
        
        # Create Property model
        return Property(
            property_desc=prop_data["property_desc"],
            address=prop_data["address"],
            price=prop_data["asked_price"],
            prop_details=prop_data["prop_details"],
            agent=prop_data["agent"],
            link=prop_data.get("link", ""),  # Assuming 'link' is optional
            agent_desc=prop_data.get("agent_desc", "")
        )