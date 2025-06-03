import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "@/types";
import { useToast } from "@/components/ui/use-toast";
import { SendIcon, Loader2 } from "lucide-react";
import { v4 as uuidv4 } from "uuid";
import ReactMarkdown from 'react-markdown';
import './ChatWidget.css';

// Define a placeholder Property type if not already defined elsewhere
// You should replace this with the actual Property type from your backend schemas
interface Property {
  id: string;
  name: string;
  price: number | string; // Allow string if price can be formatted like "$1,000,000"
  location?: string;
  description?: string;
  image_url?: string;
  // Add other relevant fields that your backend Property model might have
}

// Define a placeholder for additional_info
// Replace with a more specific type if known
interface AdditionalInfo extends Record<string, unknown> {
  summary?: string;
  // other fields
}

interface ApiResponse {
  response: string; // Reverted from answer to response to match backend AgentResponse
  relevant_properties?: Property[];
  web_search_data?: AdditionalInfo;
  additional_info?: {
    web_search_conducted?: boolean;
  };
}

const ChatWidget = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-message",
      content: "Hello! I'm PropertyBot. How can I help you find your dream property today?",
      role: "assistant",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  useEffect(() => {
    if (!threadId) {
      setThreadId(uuidv4());
    }
    if (scrollAreaRef.current) {
      const scrollArea = scrollAreaRef.current;
      scrollArea.scrollTop = scrollArea.scrollHeight;
    }
  }, [messages, threadId]);

  const formatMessage = (content: string) => {
    // First handle markdown-style links [text](url)
    const markdownContent = content.replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      (_, text, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`
    );

    // Then handle any remaining HTML-style links (if any)
    const finalContent = markdownContent.replace(
      /<a\s+href="([^"]+)"[^>]*>([^<]+)<\/a>/g,
      (_, url, text) => `[${text}](${url})`
    );
    
    return (
      <div className="markdown-content">
        <ReactMarkdown
          components={{
            p: ({node, ...props}) => <p className="mb-2 text-left" {...props} />,
            h1: ({node, ...props}) => <h1 className="text-xl font-bold mb-2" {...props} />,
            h2: ({node, ...props}) => <h2 className="text-lg font-bold mb-2" {...props} />,
            strong: ({node, ...props}) => <span className="font-bold" {...props} />,
            a: ({node, href, children, ...props}) => (
              <a 
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 underline"
                {...props}
              >
                {children}
                <svg 
                  className="w-3 h-3 inline-block" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            ),
            li: ({node, ...props}) => (
              <li className="ml-4 mb-1 text-left list-item" {...props} />
            ),
            ul: ({node, ...props}) => (
              <ul className="mb-2 space-y-1 list-none" {...props} />
            ),
          }}
        >
          {finalContent}
        </ReactMarkdown>
      </div>
    );
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !threadId) return;

    const userMessage: ChatMessage = {
      id: uuidv4(),
      content: inputValue,
      role: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/property/inquiry", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: inputValue, thread_id: threadId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ApiResponse = await response.json();
      console.log("API Response:", data);
      
      const botMessage: ChatMessage = {
        id: uuidv4(),
        content: data.response,
        role: "assistant",
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("API Error:", error);
      toast({
        title: "Error",
        description: "Failed to connect to the property agent. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="w-full h-full flex justify-center items-center p-4">
      <Card className="h-[600px] w-full max-w-2xl flex flex-col shadow-lg border-2">
        <CardHeader className="bg-primary text-white rounded-t-lg py-4">
          <CardTitle className="text-center">Property Chat Assistant</CardTitle>
        </CardHeader>
        
        <CardContent className="flex-grow overflow-hidden p-0 relative">
          <ScrollArea className="h-[450px] p-4" ref={scrollAreaRef}>
            <div className="flex flex-col gap-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`chat-bubble max-w-[85%] ${
                      message.role === "user" 
                        ? "bg-primary text-white rounded-lg p-3" 
                        : "bg-gray-100 rounded-lg p-4"
                    }`}
                  >
                    {message.role === "user" ? (
                      <p className="text-left">{message.content}</p>
                    ) : (
                      formatMessage(message.content)
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="chat-bubble bg-gray-100 rounded-lg p-3 flex items-center space-x-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
        
        <CardFooter className="pt-2 pb-4 px-4 border-t">
          <div className="flex w-full gap-2">
            <Input
              placeholder="Ask about properties..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              className="flex-1"
            />
            <Button onClick={handleSendMessage} disabled={isLoading || !inputValue.trim()}>
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendIcon className="h-4 w-4" />}
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
};

export default ChatWidget;
