"""
Prompts used by the Property Multi-Agent System.

This module contains all the prompts used by the various agents and nodes in the workflow.
"""

# Prompt for extracting context from previous messages in a conversation
CONTEXT_EXTRACTION_PROMPT = """
Review this conversation history and the current query to determine if the current query is a follow-up question that needs context from previous messages.

Conversation history:
{conversation_history}

Current query: "{current_query}"

If the current query seems to be a follow-up or references something mentioned earlier:
1. Extract any specific property names mentioned in the conversation
2. Extract any locations mentioned in the conversation
3. Extract any specific features or criteria mentioned in the conversation

Return ONLY a JSON object with this format:
{{
  "is_follow_up": true/false,
  "referenced_property": "property name or null",
  "referenced_location": "location or null",
  "referenced_features": ["feature1", "feature2"] or []
}}
"""

# Prompt for classifying if a query is property-related and/or a recommendation request
QUERY_CLASSIFICATION_PROMPT = """
Analyze the following user message and classify it:

User message: "{user_message}"

Instructions:
1. Determine if this message is asking about property/real estate (apartments, condos, houses, rentals, etc.)
2. Also determine if this is a RECOMMENDATION REQUEST where the user is asking for property suggestions based on criteria
   Examples of recommendation requests:
   - "Help me find properties under 500k in Bangsar"
   - "What condos are available near KL with 2 bedrooms?"
   - "Recommend affordable properties in Mont Kiara"
   - "Show me properties with good investment potential"

Return your classification in this exact format:
PROPERTY: yes/no
RECOMMENDATION: yes/no
"""

# Prompt for extracting search criteria from a recommendation request
SEARCH_CRITERIA_PROMPT = """
Extract detailed property search criteria from this request:

User request: "{user_request}"

Extract the following parameters (use null if not specified):
1. Price range (min-max or under/over X)
2. Location/area
3. Property type (condo, apartment, house, etc.)
4. Size (square feet/meters)
5. Number of bedrooms
6. Number of bathrooms
7. Other amenities or features
8. Price per square foot/meter (if mentioned)

Return ONLY a valid JSON object like this:
{{
  "price_min": null or number,
  "price_max": null or number,
  "location": "area name or null",
  "property_type": "type or null",
  "size_min": null or number,
  "size_max": null or number,
  "bedrooms": null or number,
  "bathrooms": null or number,
  "psf_min": null or number,
  "psf_max": null or number,
  "amenities": ["feature1", "feature2"] or []
}}
"""

# Prompt for deciding whether to perform a web search
WEB_SEARCH_DECISION_PROMPT = """
Based on the following conversation history, identified target property, and available internal data, decide if a web search is needed:

Conversation History:
{chat_history}

Current Query/Topic: {query}
Identified Target Property Name (if any): {target_property_name}
Data Found in RAG for the query/target (if any):
{relevant_properties_str}

Instructions for decision:
1. If a specific 'Identified Target Property Name' is given AND no relevant data is found in RAG, a web search IS VERY LIKELY NEEDED to find information about this property.
2. If the 'Current Query/Topic' asks for specific information (e.g., developer, year built, specific amenity details, layout, architect) AND this information is NOT present or is incomplete in the 'Data Found in RAG for the query/target', a web search IS LIKELY NEEDED to find that missing detail.
3. If the 'Current Query/Topic' is about very recent information (e.g., "latest price changes", "new units launched this month"), a web search IS LIKELY NEEDED.
4. If the 'Data Found in RAG for the query/target' appears comprehensive and directly answers the 'Current Query/Topic', then 'skip'.
5. If the query is too vague and no specific property or information type is mentioned, and RAG data is also general or empty, 'skip' (the main response agent can ask for clarification if needed).

Example 1 (No data for a specific property):
Query: "Tell me about River Park Residence."
Identified Target Property Name: River Park Residence
Data Found in RAG for the query/target: None
Return: "web_search"  (Reason: Need to find basic info about this property not found in RAG)

Example 2 (Info missing from RAG data):
Query: "Who is the developer of The Park Residences Bangsar South?"
Identified Target Property Name: The Park Residences Bangsar South
Data Found in RAG for the query/target:
- The Park Residences Bangsar South (Price: RM 1.2M, Size: 1200sqft)
(Note: Developer info is missing from RAG data for this property)
Return: "web_search" (Reason: Need to find the specific missing detail - developer)

Example 3 (Sufficient RAG data):
Query: "What's the price of Pantai Panorama Condominium?"
Identified Target Property Name: Pantai Panorama Condominium
Data Found in RAG for the query/target:
- Pantai Panorama Condominium (Price: RM 800k, Size: 1000sqft)
Return: "skip" (Reason: RAG data seems sufficient for this price query)

Based on the Current Query/Topic, Identified Target Property, and Data Found in RAG, your decision (web_search or skip):
""" 