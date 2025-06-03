import React, { useState, useRef } from "react";
import Hero from "@/components/Hero";
import Features from "@/components/Features";
import ChatWidget from "@/components/ChatWidget";
import { Button } from "@/components/ui/button";
import { MessageSquare } from "lucide-react";

const Index = () => {
  const [showChat, setShowChat] = useState(false);
  const chatSectionRef = useRef<HTMLDivElement>(null);

  const scrollToChat = () => {
    setShowChat(true);
    setTimeout(() => {
      chatSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header/Navigation */}
      <header className="py-4 px-6 bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <MessageSquare className="h-6 w-6 text-property-primary" />
            <span className="font-bold text-xl">PropertyBot</span>
          </div>
          <div className="flex items-center space-x-4">
            <a href="#features" className="text-gray-600 hover:text-property-primary hidden md:inline-block">Features</a>
            <Button size="sm" className="flex items-center gap-2" onClick={scrollToChat}>
              <MessageSquare className="h-4 w-4" />
              <span>Try It</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <Hero onTryDemo={scrollToChat} />
      
      {/* Features Section */}
      <Features />

      {/* Demo Section */}
      <section id="demo" ref={chatSectionRef} className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4 text-property-dark">
              Experience the PropertyBot in Action
            </h2>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto">
              Ask our AI assistant about properties, pricing, locations, or any real estate questions you have.
            </p>
          </div>
          
          <div className="flex justify-center">
            <ChatWidget useMock={true} />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 bg-property-dark text-white">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <MessageSquare className="h-5 w-5" />
              <span className="font-bold text-lg">PropertyBot</span>
            </div>
            <div className="text-sm text-gray-400">
              &copy; {new Date().getFullYear()} PropertyBot. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
