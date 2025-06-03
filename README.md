# Property Multi-Agent System

A sophisticated multi-agent system designed for property inquiries and analysis, leveraging LLMs, RAG (Retrieval Augmented Generation), and dynamic web search capabilities.

## 🌟 Features

- **Intelligent Query Understanding**: Automatically classifies and extracts key information from natural language property inquiries
- **Multi-Agent Architecture**: Specialized agents for validation, data retrieval, web search, and response generation
- **RAG System**: Vector database for efficient property similarity search
- **Dynamic Web Search**: Intelligently decides when to supplement property data with web search results
- **Conversation Memory**: Maintains context across multiple user interactions
- **Property Recommendations**: Provides tailored property suggestions based on user preferences

## 🏗️ Architecture

The system is built on a multi-agent architecture using LangGraph for workflow orchestration:

```
User Query → Query Classification → Validation → Property Search → 
[If needed] Web Search → Response Generation → User
```

### Core Components

1. **Backend**
   - FastAPI application with LangGraph workflows
   - Multiple specialized agents for different tasks
   - FAISS vector database for similarity search
   - OpenAI integration for natural language processing

2. **Frontend**
   - React application with TypeScript
   - Tailwind CSS for styling
   - Real-time chat interface

3. **Scraper**
   - Data collection tools for property listings
   - Data cleaning and processing utilities

## 🤖 Agents

- **ValidationAgent**: Extracts and validates information from user queries
- **DataSourceAgent**: Handles RAG-based property searches using vector embeddings
- **WebSearchAgent**: Performs dynamic web searches for additional property information
- **ResponseAgent**: Generates natural language responses using all gathered information

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, LangChain, LangGraph, FAISS, OpenAI
- **Frontend**: TypeScript, React, Tailwind CSS
- **Data**: Vector embeddings, JSON, XLSX
- **DevOps**: Docker (planned)

## 📋 Setup Instructions

### Prerequisites

- Python 3.9+
- Node.js 16+
- OpenAI API key

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

5. Start the backend server:
   ```
   uvicorn main:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run dev
   ```

## 🚀 Usage

1. Access the frontend application at `http://localhost:8080`
2. Enter property inquiries in natural language
3. The system will process your query through multiple agents and return relevant property information

## 📊 Example Queries

- "Show me condos in Bangsar South under RM 800,000"
- "What amenities does River Park have?"
- "Are there any properties near KLCC with 3 bedrooms under RM 1.5 million?"
- "Tell me more about the neighborhood around Mont Kiara"

## 🔄 Workflow

1. **Initial Property Query**
   ```
   User Query → Query Understanding → RAG Search →
   [If found] → Validation → Response
   [If not found] → Web Research → Validation → Response + Suggestions
   ```

2. **Follow-up Questions**
   ```
   Follow-up Query → Query Understanding →
   [Context Lookup] → Specific Property Check →
   [If needed] Web Research → Validation → Response
   ```

## 🧠 Future Improvements

- SalesAgent for inquiry routing
- Comprehensive test suite
- Error logging
- API authentication
- Docker containerization
- CI/CD pipeline setup
- Caching mechanism
- API monitoring and rate limiting

## 📝 License

[MIT License](LICENSE) 