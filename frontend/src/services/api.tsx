
import { ChatMessage, ApiResponse } from "../types";

const API_URL = "http://localhost:8000"; // Change this to your FastAPI server URL

export const chatWithAgent = async (message: string): Promise<ApiResponse> => {
  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      message: data.response,
      success: true,
    };
  } catch (error) {
    console.error("Error chatting with agent:", error);
    return {
      message: "Sorry, I'm having trouble connecting to the server right now. Please try again later.",
      success: false,
    };
  }
};

// Mock function for development/testing without backend
export const mockChatWithAgent = async (message: string): Promise<ApiResponse> => {
  await new Promise((resolve) => setTimeout(resolve, 1000)); // Simulate network delay
  
  // Simple keyword detection for demo purposes
  const lowercaseMessage = message.toLowerCase();
  
  if (lowercaseMessage.includes("hello") || lowercaseMessage.includes("hi")) {
    return {
      message: "Hello! I'm PropertyBot. How can I help you with your property search today?",
      success: true,
    };
  } else if (lowercaseMessage.includes("property") || lowercaseMessage.includes("house") || lowercaseMessage.includes("apartment")) {
    return {
      message: "I can help you find properties based on location, price, number of bedrooms, and more. What are your requirements?",
      success: true,
    };
  } else if (lowercaseMessage.includes("price") || lowercaseMessage.includes("cost") || lowercaseMessage.includes("budget")) {
    return {
      message: "Properties in our database range from $150,000 to $5,000,000. What's your budget range?",
      success: true,
    };
  } else if (lowercaseMessage.includes("location") || lowercaseMessage.includes("area") || lowercaseMessage.includes("where")) {
    return {
      message: "We have properties in downtown areas, suburbs, and rural settings. Which area are you interested in?",
      success: true,
    };
  } else {
    return {
      message: "I'm here to help with your property search. You can ask me about available properties, pricing, locations, or specific features you're looking for.",
      success: true,
    };
  }
};
