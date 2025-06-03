from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional

class PropertyQuery(BaseModel):
    query: str = Field(..., description="The user's property inquiry in natural language")


class Property(BaseModel):
    property_desc: str
    address: str
    price: int
    prop_details: Dict
    agent: str
    link: str
    agent_desc: Optional[str] = None

    @validator('price')
    def validate_price(cls, value):
        if value <= 0:
            raise ValueError("Price must be positive")
        return round(value, 2)
    
class AgentResponse(BaseModel):
    response: str = Field(..., description="Natural language response to the user's query")
    relevant_properties: List[Property] = Field(..., description="List of relevant properties")
    additional_info: Optional[Dict] = Field(default_factory=dict, description="Additional information from agents") 