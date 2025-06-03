import traceback
import logging
import json
import re

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional, TypedDict, Annotated
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.checkpoint.memory import InMemorySaver

from agents.validation import ValidationAgent
from agents.response import ResponseAgent
from agents.web_search import WebSearchAgent
from agents.data_source import DataSourceAgent
from models.schemas import AgentResponse, Property
from utils.prompts import (
    CONTEXT_EXTRACTION_PROMPT,
    QUERY_CLASSIFICATION_PROMPT,
    SEARCH_CRITERIA_PROMPT,
    WEB_SEARCH_DECISION_PROMPT
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

app = FastAPI(
    title="Property Multi-Agent System",
    description="A multi-agent system for property inquiries and analysis",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # React frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
validation_agent = ValidationAgent()
response_agent = ResponseAgent()
web_search_agent = WebSearchAgent()
data_source_agent = DataSourceAgent()

class AgentState(TypedDict):
    current_input: str  # The user's most recent message for this turn
    filters: Optional[Dict]
    user_context: Optional[Dict]
    relevant_properties: Optional[List[Property]]
    web_search_result: Optional[Dict]
    web_search_decision: Optional[str]
    response: Optional[Dict] # API response
    chat_history: Annotated[List[BaseMessage], add_messages] # For LangGraph memory
    is_property_query: bool # Flag to indicate if current_input is property related
    target_property_name: Optional[str] # Specific property name user might be asking for
    property_exists: Optional[bool] # Whether the target_property_name exists in our known list
    is_recommendation_request: Optional[bool] # Flag indicating if user is asking for property recommendations
    search_criteria: Optional[Dict] # Structured search criteria for recommendation requests
    conversation_context: Optional[Dict] # Context extracted from previous conversation for follow-up questions

async def classify_input_node(state: AgentState) -> AgentState:
    """Classify the input using LLM and update chat history."""
    # Get the full chat history from checkpointer before appending the new message
    previous_chat_history = state.get("chat_history", [])
    
    # Add the current input to chat history
    state["chat_history"] = previous_chat_history + [HumanMessage(content=state["current_input"])]
    
    # Extract contextual information from previous messages if this appears to be a follow-up
    if previous_chat_history and len(state["current_input"].split()) < 15:  # Short query might be a follow-up
        # Look at previous messages for context
        conversation_history = ' '.join([f"{msg.type}: {msg.content}" for msg in previous_chat_history[-3:]])
        context_extraction_prompt = CONTEXT_EXTRACTION_PROMPT.format(
            conversation_history=conversation_history,
            current_query=state["current_input"]
        )
        
        try:
            context_result = await validation_agent.llm.ainvoke(context_extraction_prompt)
            
            if hasattr(context_result, 'content'):
                context_text = context_result.content.strip()
            else:
                context_text = str(context_result).strip()
            
            json_match = re.search(r'\{[\s\S]*\}', context_text)
            if json_match:
                context_json = json.loads(json_match.group(0))
                state["conversation_context"] = context_json
                logging.info(f"Extracted conversation context: {context_json}")
                
                # If this is a follow-up about a property, set target_property_name
                if context_json.get("is_follow_up") and context_json.get("referenced_property"):
                    state["target_property_name"] = context_json.get("referenced_property")
                    logging.info(f"Set target_property_name from conversation context: {state['target_property_name']}")
        except Exception as e:
            logging.error(f"Error extracting conversation context: {e}")
            state["conversation_context"] = None
    
    # Use the LLM to classify if this is a property-related query and if it's a recommendation request
    classification_prompt = QUERY_CLASSIFICATION_PROMPT.format(user_message=state["current_input"])
    
    classification_result = await validation_agent.llm.ainvoke(classification_prompt)
    
    # Extract the decision from the LLM response
    if hasattr(classification_result, 'content'):
        classification_text = classification_result.content.strip().lower()
    else:
        classification_text = str(classification_result).strip().lower()
    
    # Set the property query flag based on LLM classification
    state["is_property_query"] = "property: yes" in classification_text
    
    # Set a new flag for recommendation requests
    state["is_recommendation_request"] = "recommendation: yes" in classification_text
    
    logging.info(f"Input classified as property-related: {state['is_property_query']}, recommendation request: {state.get('is_recommendation_request', False)}")
    return state

def decide_initial_route(state: AgentState) -> str:
    """Determine the next step based on query classification."""
    if state["is_property_query"]:
        return "validate_input"
    else:
        return "generate_response" # Directly generate a conversational response

async def validate_input(state: AgentState) -> AgentState:
    """Validate and extract information from the user's query, including a target property name and search criteria."""
    validation_result = await validation_agent.validate(state["current_input"])
    state["filters"] = validation_result.get("extracted_filters", {})
    state["user_context"] = validation_result.get("extracted_user_context", {})

    # If this is a recommendation request, extract detailed search criteria
    if state.get("is_recommendation_request"):
        # Extract detailed search criteria with an LLM
        search_criteria_prompt = SEARCH_CRITERIA_PROMPT.format(user_request=state["current_input"])
        
        criteria_result = await validation_agent.llm.ainvoke(search_criteria_prompt)
        
        # Extract the JSON from the LLM response
        try:
            if hasattr(criteria_result, 'content'):
                criteria_text = criteria_result.content.strip()
            else:
                criteria_text = str(criteria_result).strip()
            
            # Find JSON object in the text using regex
            json_match = re.search(r'\{[\s\S]*\}', criteria_text)
            if json_match:
                criteria_json = json.loads(json_match.group(0))
                state["search_criteria"] = criteria_json
                logging.info(f"Extracted search criteria: {criteria_json}")
                
                # Add to filters for downstream use
                if state["filters"] is None:
                    state["filters"] = {}
                    
                # Map the structured criteria to filters
                if criteria_json.get("price_max"):
                    state["filters"]["price_max"] = criteria_json["price_max"]
                if criteria_json.get("location"):
                    state["filters"]["location"] = criteria_json["location"]
                if criteria_json.get("property_type"):
                    state["filters"]["property_type"] = criteria_json["property_type"]
        except Exception as e:
            logging.error(f"Error parsing search criteria: {e}")
            state["search_criteria"] = None

    # Extract property name from input, using filters or direct detection
    extracted_name = state["filters"].get('name', None)
    if not extracted_name:
        # Check for River Park directly in the current input
        if "river park" in state["current_input"].lower():
            state["target_property_name"] = "River Park Bangsar South"
    else:
        state["target_property_name"] = str(extracted_name)

    return state

async def check_property_existence(state: AgentState) -> AgentState:
    """
    This function now simply passes through the target_property_name without checking against a static list.
    We'll set property_exists to None since we're no longer checking against a hardcoded list.
    """
    # We're no longer checking against a hardcoded list
    state["property_exists"] = None
    return state

def decide_after_existence_check(state: AgentState) -> str:
    """
    Determine next step after property identification.
    
    Logic:
    1. For recommendation requests, always use RAG (perform_similarity_search)
    2. For specific property queries:
       a. If we have relevant properties from RAG, use them (perform_similarity_search)
       b. If we don't have relevant properties, try web search (should_perform_web_search)
    3. For general property queries, use RAG first (perform_similarity_search)
    """
    # For recommendation requests, we want to search our database first
    if state.get("is_recommendation_request"):
        logging.info("Recommendation request detected, routing to perform_similarity_search")
        return "perform_similarity_search"
    
    # For specific property queries, check if we have any data
    if state.get("target_property_name"):
        # We'll use the RAG system first to see if we have information
        # The should_perform_web_search node will later decide if web search is needed
        # based on the RAG results and the specific question
        logging.info(f"Specific property '{state.get('target_property_name')}' identified, routing to perform_similarity_search")
        return "perform_similarity_search"
    
    # For general property queries without a specific target, use RAG
    logging.info("No specific target property identified, routing to perform_similarity_search for general RAG")
    return "perform_similarity_search"

async def perform_similarity_search(state: AgentState) -> AgentState:
    """
    Perform similarity search using current user input and filters.
    
    If a target property name is identified, it will be added to the search query
    to make the search more specific and relevant.
    """
    query_for_search = state["current_input"]
    filters_for_search = state.get("filters", {})

    # If we have a target property name, use it to enhance the search query
    if state.get("target_property_name"):
        original_query = query_for_search
        query_for_search = f"{state['target_property_name']} {query_for_search}"
        logging.info(f"Enhanced search query from '{original_query}' to '{query_for_search}' using target property name")

    logging.info(f"Performing similarity search with query: '{query_for_search}'")
    state["relevant_properties"] = await data_source_agent.search_similar_properties(
        query=query_for_search,
        filters=filters_for_search,
        user_context=state.get("user_context")
    )
    
    # Log whether we found any properties and how many
    if state["relevant_properties"]:
        logging.info(f"Similarity search found {len(state['relevant_properties'])} properties")
        # Log the first few property names for debugging
        property_names = [getattr(prop, 'name', 'Unknown') for prop in state["relevant_properties"][:3]]
        if len(state["relevant_properties"]) > 3:
            property_names.append(f"...and {len(state['relevant_properties']) - 3} more")
        logging.info(f"Found properties: {', '.join(property_names)}")
    else:
        logging.info("Similarity search found no properties")
        
    return state

async def should_perform_web_search(state: AgentState) -> AgentState:
    """
    Decide whether to perform a web search based on the query and available data.
    
    This function analyzes:
    1. Whether the query is property-related
    2. Whether a specific property was mentioned
    3. Whether the RAG system returned relevant results
    4. Whether the query asks for specific details that might not be in the RAG results
    
    It then decides whether to perform a web search or use the RAG results.
    """
    if not state["is_property_query"]:
        state["web_search_decision"] = "skip"
        logging.info("Not a property query, web search decision: skip.")
        return state

    # Force web search if there's a specific property mentioned but no relevant properties from RAG
    if state.get("target_property_name") and not state.get("relevant_properties"):
        state["web_search_decision"] = "web_search"
        logging.info(f"Specific property '{state.get('target_property_name')}' mentioned but no relevant properties found in RAG, forcing web search.")
        return state

    query_for_decision = state["current_input"]  # Always use current input
    
    chat_history_list = [f'{msg.type}: {msg.content}' for msg in state.get("chat_history", [])]
    chat_history_str = '\n'.join(chat_history_list)
    
    # Prepare relevant_properties string for the prompt
    relevant_properties_str = "None"
    if state.get("relevant_properties"):
        # Summarize properties to keep the prompt concise, avoid stringifying large objects directly
        props_summary = []
        for prop in state["relevant_properties"][:3]: # Show first 3 properties
            # Ensure attributes exist before accessing
            name = getattr(prop, 'name', 'N/A')
            price = getattr(prop, 'price', 'N/A')
            size = getattr(prop, 'size', 'N/A')
            props_summary.append(f"- {name} (Price: {price}, Size: {size})")
        if len(state["relevant_properties"]) > 3:
            props_summary.append(f"...and {len(state['relevant_properties']) - 3} more.")
        relevant_properties_str = '\n'.join(props_summary)
    
    decision_prompt = WEB_SEARCH_DECISION_PROMPT.format(
        chat_history=chat_history_str,
        query=query_for_decision,
        target_property_name=state.get("target_property_name", "None specified"),
        relevant_properties_str=relevant_properties_str
    )
    
    decision_message = await validation_agent.llm.ainvoke(decision_prompt)
    
    decision_content = ""
    if hasattr(decision_message, 'content'):
        decision_content = decision_message.content.strip().lower()
    else:
        # Fallback for direct string output if not a BaseMessage object
        decision_content = str(decision_message).strip().lower()
    
    state["web_search_decision"] = "web_search" if "web_search" in decision_content else "skip"
    logging.info(f"Web search final decision: {state['web_search_decision']}")

    # Force web search if no relevant properties from RAG and it's a property query
    # (This is a fallback in case the early check for target_property_name didn't catch it)
    if not state.get('relevant_properties') and state["is_property_query"]:
        state['web_search_decision'] = 'web_search'
        logging.info('No relevant properties found in RAG for a property query, forcing web search.')
        return state

    return state

async def perform_web_search(state: AgentState) -> AgentState:
    """Perform web search to gather additional information."""
    logging.info("--- Performing Web Search --- Node triggered.")
    search_query = state["current_input"]  # Start with current input
    location_filter = state.get('filters', {}).get('location')
    
    # Add context from conversation if this is a follow-up question
    if state.get("conversation_context") and state["conversation_context"].get("is_follow_up"):
        context = state["conversation_context"]
        
        # Add property name if available
        if context.get("referenced_property") and context.get("referenced_property") not in search_query:
            search_query = f"{context.get('referenced_property')} {search_query}"
            logging.info(f"Added property context to search query: {context.get('referenced_property')}")
        
        # Add location if available and not already in filters
        if context.get("referenced_location") and not location_filter:
            location_filter = context.get("referenced_location")
            logging.info(f"Added location context to search: {location_filter}")
        
        # Add features if relevant
        if context.get("referenced_features") and len(context.get("referenced_features")) > 0:
            features_str = " ".join(context.get("referenced_features"))
            if features_str not in search_query:
                search_query = f"{search_query} {features_str}"
                logging.info(f"Added feature context to search query: {features_str}")
    
    # If this is a recommendation request, format the search query specifically for property listings
    if state.get("is_recommendation_request") and state.get("search_criteria"):
        criteria = state.get("search_criteria")
        search_query = "property listings "
        
        # Build a more specific search query based on the extracted criteria
        if criteria.get("location"):
            search_query += f"in {criteria.get('location')} "
        
        if criteria.get("price_max"):
            search_query += f"under RM{criteria.get('price_max')} "
        
        if criteria.get("property_type"):
            search_query += f"{criteria.get('property_type')} "
        
        if criteria.get("bedrooms"):
            search_query += f"{criteria.get('bedrooms')} bedroom "
        
        if criteria.get("psf_min") or criteria.get("psf_max"):
            psf_range = ""
            if criteria.get("psf_min"):
                psf_range += f"above RM{criteria.get('psf_min')} per square foot "
            if criteria.get("psf_max"):
                psf_range += f"below RM{criteria.get('psf_max')} per square foot "
            search_query += psf_range
        
        logging.info(f"Formatted recommendation search query: {search_query}")
    # Optionally include target property name for context if it exists and this is not a recommendation request
    elif state.get("target_property_name") and state.get("target_property_name") not in search_query:
        search_query = f"{state['target_property_name']} {search_query}"
    
    logging.info(f"Search Query for Web: {search_query}, Location: {location_filter}")

    if not search_query:
        logging.warning("Web search triggered but search_query is empty.")
        state["web_search_result"] = {"error": "Empty search query"}
        return state
        
    state["web_search_result"] = await web_search_agent.search_web(search_query, location_filter)
    logging.info(f"Web search result obtained (summary/keys): {state['web_search_result'].keys() if isinstance(state['web_search_result'], dict) else 'Result not a dict'}")
    return state

async def generate_response(state: AgentState) -> AgentState:
    """Generate the final response using all gathered information."""
    if state["is_property_query"]:
        api_response_data = await response_agent.generate_natural_language_response(
            query=state["current_input"],  # Always use current input
            validation={"filters": state.get("filters"), "user_context": state.get("user_context")},
            properties=state.get("relevant_properties"),
            web_search_data=state.get("web_search_result"),
            chat_history=state.get("chat_history"),
            is_recommendation_request=state.get("is_recommendation_request", False)  # Pass the recommendation flag
        )
        # Assuming api_response_data is already an AgentResponse or dict serializable to it
        state["response"] = api_response_data.dict() if isinstance(api_response_data, AgentResponse) else api_response_data
        state["chat_history"] = [AIMessage(content=api_response_data.response if isinstance(api_response_data, AgentResponse) else str(api_response_data.get("response")))]
    else:
        last_user_message = ""
        if state.get("chat_history"):
            # Get the last human message
            for msg in reversed(state["chat_history"]):
                if msg.type == "human":
                    last_user_message = msg.content
                    break
        chitchat_response_data = await response_agent.generate_natural_language_response(
            query=state["current_input"],
            chat_history=state.get("chat_history"),
            is_chitchat=True # Add a flag if ResponseAgent needs it
        )
        state["response"] = chitchat_response_data.dict() if isinstance(chitchat_response_data, AgentResponse) else chitchat_response_data
        state["chat_history"] = [AIMessage(content=chitchat_response_data.response if isinstance(chitchat_response_data, AgentResponse) else str(chitchat_response_data.get("response")))]

    return state

# Create and configure the workflow
def create_workflow():
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify_input", classify_input_node)
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("check_property_existence", check_property_existence)
    workflow.add_node("perform_similarity_search", perform_similarity_search)
    workflow.add_node("should_perform_web_search", should_perform_web_search)
    workflow.add_node("perform_web_search", perform_web_search)
    workflow.add_node("generate_response", generate_response)

    # Define edges
    workflow.add_edge(START, "classify_input")
    
    # Conditional routing after classification
    workflow.add_conditional_edges(
        "classify_input",
        decide_initial_route,
        {
            "validate_input": "validate_input",
            "generate_response": "generate_response"
        }
    )
    
    workflow.add_edge("validate_input", "check_property_existence")

    # Conditional routing after existence check
    workflow.add_conditional_edges(
        "check_property_existence",
        decide_after_existence_check,
        {
            "perform_similarity_search": "perform_similarity_search",
            "should_perform_web_search": "should_perform_web_search"
        }
    )
    
    # Ensure that after performing a RAG similarity search, we always decide on web search next
    workflow.add_edge("perform_similarity_search", "should_perform_web_search")

    # Conditional edges based on web search decision
    workflow.add_conditional_edges(
        "should_perform_web_search",
        lambda x: x["web_search_decision"],
        {
            "web_search": "perform_web_search", 
            "skip": "generate_response"
        }
    )
    workflow.add_edge("perform_web_search", "generate_response")
    workflow.add_edge("generate_response", END)

    # Add checkpointer for memory
    # Reason: Enables conversation history persistence across requests for the same thread_id.
    checkpointer = InMemorySaver()
    return workflow.compile(checkpointer=checkpointer)

# Create the workflow instance
workflow_app = create_workflow()

@app.get("/")
async def root():
    return {"message": "Property Multi-Agent System API"}

@app.post("/api/property/inquiry", response_model=AgentResponse)
async def property_inquiry(current_input: str = Body(..., embed=True, alias="query"), thread_id: str = Body(..., embed=True)):
    try:
        # Initialize state with the current input and an empty history (or load from checkpointer)
        # The checkpointer handles loading chat_history if thread_id exists
        initial_state: AgentState = {
            "current_input": current_input,
            "filters": None,
            "user_context": None,
            "relevant_properties": None,
            "web_search_result": None,
            "web_search_decision": None,
            "response": None,
            "chat_history": [], # Checkpointer will populate this if thread_id has history
            "is_property_query": False, # Will be set in classify_input
            "target_property_name": None,
            "property_exists": None,
            "is_recommendation_request": False, # New field
            "search_criteria": None, # New field
            "conversation_context": None # New field for tracking context across messages
        }
        
        # Execute workflow
        # Pass thread_id in configurable for the checkpointer
        config = {"configurable": {"thread_id": thread_id}}
        result_state = await workflow_app.ainvoke(initial_state, config=config)
        
        final_response_data = result_state.get("response")

        if final_response_data:
            # Ensure the response matches AgentResponse schema
            if isinstance(final_response_data, dict):
                try:
                    return AgentResponse(**final_response_data)
                except Exception as pydantic_exc:
                    print(f"Pydantic validation error for final response: {pydantic_exc}")
                    print(f"Data was: {final_response_data}")
                    # Fallback or re-raise, depending on desired error handling
                    raise HTTPException(status_code=500, detail="Error formatting final response.")

            elif isinstance(final_response_data, AgentResponse):
                return final_response_data
            else:
                raise HTTPException(status_code=500, detail="Invalid response format from workflow.")
        else:
            raise HTTPException(status_code=500, detail="No response generated by the workflow.")
        
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 