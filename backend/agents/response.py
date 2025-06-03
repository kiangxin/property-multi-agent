from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.messages import BaseMessage
import os
import json

from models.schemas import PropertyQuery, AgentResponse, Property

class ResponseAgent:
    """Agent for generating natural language responses based on property data and analysis."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0.3,  # Lowered temperature for more factual adherence
            model_name="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # New prompt for natural language responses, now including chat history and chitchat flag
        self.natural_language_prompt = PromptTemplate(
            input_variables=["chat_history_str", "current_user_input", "validation_str", "properties_str", "web_search_data_str", "is_chitchat"],
            template="""
            Previous Conversation History (if any):
            {chat_history_str}
            
            Current User Input: {current_user_input}

            Supporting Information (Use only if relevant and 'is_chitchat' is false):
            1. Validation Results (from initial query processing): {validation_str}
            2. Relevant Properties Found (from internal RAG database): {properties_str}
            3. Web Search Information (if a web search was performed): {web_search_data_str}

            Your Task & Instructions:
            You are a helpful AI Property Assistant. Your goal is to provide accurate and relevant information.

            1. If 'is_chitchat' is true:
               - Engage in a friendly, conversational manner based on 'Previous Conversation History' and 'Current User Input'.
               - You can acknowledge you are a property assistant but avoid deep property analysis unless the user explicitly steers the conversation back to it.
           
            2. If 'is_chitchat' is false (it's a property-related query about the 'Current User Input'):
               - Your primary goal is to ACCURATELY answer the 'Current User Input'. Use 'Previous Conversation History' for conversational context only.
               
               - **Responding to Factual Questions (e.g., developer, year built, specific amenities, layout details):**
                 A. First, check if the specific factual detail is clearly and unambiguously present in 'Relevant Properties Found (from internal RAG database)' or 'Validation Results'.
                 B. If the detail is NOT found or is unclear in the internal RAG/Validation, YOU MUST THEN CHECK 'Web Search Information' (if provided and relevant to the query).
                 C. If 'Web Search Information' provides a clear, direct answer to the specific factual detail, state that answer.
                 D. **VERY IMPORTANT: If the specific factual detail is NOT clearly found or is ambiguous in ANY of the provided information sources (RAG, Validation, Web Search), YOU MUST explicitly state that you are unable to find that specific piece of information for the property in question. Do NOT invent, guess, or infer facts not present in the data. For example, say: "I couldn't find specific information about the developer for [Property Name]." or "I don't have the layout details for [Property Name] in my current information sources."**
              
               - **For General Queries about a property (e.g., "Tell me about X property"):** Synthesize information from all relevant provided sources (RAG, Web Search, Validation) to give a comprehensive overview. If a source doesn't have info, don't mention it or state it wasn't found.

               - **General Guidelines for Property Queries:**
                 - If no relevant properties are found at all for a general property search (and web search doesn't help), politely state that.
                 - Be professional and helpful. Do NOT write an email.
                 - Maintain a formal and professional tone.

            Response:
            """
        )
        
        # Create separate chains
        self.natural_language_chain = self.natural_language_prompt | self.llm

    async def generate_natural_language_response(
        self,
        query: str,
        validation: Optional[Dict] = None,
        properties: Optional[List[Property]] = None,
        web_search_data: Optional[Dict] = None,
        chat_history: Optional[List[BaseMessage]] = None,
        is_chitchat: bool = False,
        is_recommendation_request: bool = False  # New parameter to handle recommendation formatting
    ) -> AgentResponse:
        """
        Generate a natural language response based on all available information, including chat history.
        
        Args:
            query: The user's current input for this turn.
            validation: Results from the ValidationAgent (for property queries).
            properties: Optional properties from DataSourceAgent (for property queries).
            web_search_data: Optional results from WebSearchAgent (for property queries).
            chat_history: List of previous messages in the conversation.
            is_chitchat: Boolean flag indicating if the query is general chitchat.
            is_recommendation_request: Boolean flag indicating if this is a property recommendation request.
            
        Returns:
            An AgentResponse object containing the response and relevant information.
        """
        # Format chat history for the prompt
        chat_history_formatted = []
        if chat_history:
            # Iterate in reverse if you want to limit history size, but for now, use all.
            # Also, ensure messages are in chronological order for the LLM.
            for msg in chat_history:
                role = "User" if msg.type == "human" else "Assistant"
                chat_history_formatted.append(f"{role}: {msg.content}")
        # The last message in chat_history is the current user query if it was appended before calling this.
        # However, main.py passes current_input separately as 'query', so we use that.
        chat_history_str = "\n".join(chat_history_formatted[:-1]) if chat_history and len(chat_history) > 1 else "No previous messages in this session." # Exclude current query if already in `query`
        
        current_user_input = query # This is current_input from AgentState

        # Prepare other inputs for the prompt, making them descriptive for non-property queries
        validation_str = json.dumps(validation, indent=2) if validation and not is_chitchat else "Not applicable or not a property query."
        
        properties_serializable = [prop.dict() for prop in properties] if properties and not is_chitchat else []
        properties_str = json.dumps(properties_serializable, indent=2) if properties_serializable else "No specific properties found or not a property query."
        
        # Check if this is a recommendation request with web search data
        is_recommendation_with_data = is_recommendation_request and web_search_data and web_search_data.get("web_search_results")
        
        # Modify the prompt to handle recommendations specifically
        recommendation_instruction = ""
        if is_recommendation_request:
            recommendation_instruction = """
            SPECIAL INSTRUCTIONS FOR PROPERTY RECOMMENDATIONS:
            This query is asking for property recommendations based on specific criteria.
            
            1. Format your response as a list of specific property recommendations with details
            2. Start with a brief introduction summarizing what you found
            3. Present each recommendation in a clear, structured way with:
               - Property name and location
               - Price
               - Key features (bedrooms, size, amenities)
               - Any unique selling points
            4. End with a brief conclusion and follow-up question offering additional help
            5. If you couldn't find specific properties meeting all criteria, acknowledge this and suggest alternatives
            
            EXAMPLE FORMATTING:
            "Based on your criteria, I found several properties in [LOCATION] that match your requirements:
            
            **[PROPERTY NAME]**
            - Price: RM [PRICE]
            - [X] bedrooms, [Y] bathrooms
            - [SIZE] sq ft
            - [KEY FEATURES]
            
            **[PROPERTY NAME 2]**
            - Price: RM [PRICE]
            - [KEY DETAILS]
            
            Would you like more information about any of these properties?"
            """
        
        # Be careful with web_search_data structure; it might be a list of results or a complex dict.
        # For the prompt, a string representation is needed. If it's a list of search snippets, join them.
        # If it's a dict, json.dumps might be okay, but ensure it's what the LLM expects.
        web_search_data_str = "No web search performed or no relevant results found."
        if web_search_data and not is_chitchat:
            if isinstance(web_search_data, dict) and web_search_data.get("web_search_results"):
                search_results = web_search_data.get("web_search_results")
                if is_recommendation_request:
                    # Format specifically for recommendations - extract just the answer
                    if isinstance(search_results, dict) and search_results.get("answer"):
                        web_search_data_str = search_results.get("answer")
                    elif isinstance(search_results, dict) and search_results.get("summary"):
                        web_search_data_str = search_results.get("summary")
                    else:
                        web_search_data_str = json.dumps(search_results, indent=2)
                else:
                    # Regular formatting for non-recommendation web search
                    if isinstance(web_search_data["web_search_results"], dict):
                        web_search_data_str = json.dumps(web_search_data["web_search_results"], indent=2)
                    elif isinstance(web_search_data["web_search_results"], list):
                        snippets = [str(res) for res in web_search_data["web_search_results"][:3]]
                        web_search_data_str = '\n'.join(snippets) if snippets else web_search_data_str
                    else:
                        web_search_data_str = str(web_search_data["web_search_results"])
            elif isinstance(web_search_data, list): # If web_search_data is already a list of results
                 snippets = [str(res) for res in web_search_data[:3]]
                 web_search_data_str = '\n'.join(snippets) if snippets else web_search_data_str
            else:
                 web_search_data_str = str(web_search_data) # Generic fallback

        # Add recommendation instructions to the prompt template if needed
        prompt_template = self.natural_language_prompt.template
        if is_recommendation_request:
            # Insert recommendation instructions after the Supporting Information section
            lines = prompt_template.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if "Supporting Information" in line:
                    insert_idx = i + 4  # Insert after this section and its explanation lines
                    break
            
            if insert_idx > 0:
                lines.insert(insert_idx, recommendation_instruction)
                prompt_template = '\n'.join(lines)
        
        # Create a new PromptTemplate with the possibly modified template
        current_prompt = PromptTemplate(
            input_variables=self.natural_language_prompt.input_variables,
            template=prompt_template
        )
        current_chain = current_prompt | self.llm

        prompt_inputs = {
            "chat_history_str": chat_history_str,
            "current_user_input": current_user_input,
            "validation_str": validation_str,
            "properties_str": properties_str,
            "web_search_data_str": web_search_data_str,
            "is_chitchat": is_chitchat
        }
        
        # Generate natural language response
        response_result = await current_chain.ainvoke(prompt_inputs)
        response_text = response_result.content.strip()

        # Prepare additional information (mostly relevant for property queries)
        additional_info = {}
        if not is_chitchat:
            additional_info = {
                "validation_details": validation if validation else {},
                "fact_check_summary": {
                    "total_verified": len(properties) if properties else 0,
                }
            }
            if web_search_data:
                additional_info["web_search_conducted"] = True
                additional_info["web_search_data_summary_for_prompt"] = web_search_data_str
                if is_recommendation_request:
                    additional_info["is_recommendation_response"] = True
        
        return AgentResponse(
            response=response_text,
            relevant_properties=properties if properties and not is_chitchat else [],
            additional_info=additional_info
        ) 