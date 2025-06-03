
import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Search, Home, BarChart, Clock, MessageSquare, Filter } from "lucide-react";

const Features = () => {
  const features = [
    {
      icon: <Search className="h-10 w-10 text-property-primary" />,
      title: "Intelligent Search",
      description: "Natural language search that understands your preferences and requirements."
    },
    {
      icon: <Home className="h-10 w-10 text-property-primary" />,
      title: "Property Matching",
      description: "Get personalized property recommendations based on your specific needs."
    },
    {
      icon: <BarChart className="h-10 w-10 text-property-primary" />,
      title: "Market Insights",
      description: "Access real-time market data and trends to make informed decisions."
    },
    {
      icon: <Filter className="h-10 w-10 text-property-primary" />,
      title: "Smart Filtering",
      description: "Filter properties by multiple criteria with natural language commands."
    },
    {
      icon: <Clock className="h-10 w-10 text-property-primary" />,
      title: "24/7 Availability",
      description: "Get property information and assistance anytime, day or night."
    },
    {
      icon: <MessageSquare className="h-10 w-10 text-property-primary" />,
      title: "Conversational UI",
      description: "Chat naturally as if you're talking to a human real estate agent."
    },
  ];

  return (
    <section className="py-20 bg-property-light" id="features">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-property-dark">
            Powerful Features to Streamline Your Property Search
          </h2>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            Our AI-powered property chatbot offers a range of features designed to make your property search experience seamless and efficient.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <Card key={index} className="border border-gray-200 hover:shadow-md transition-shadow duration-300 h-full">
              <CardHeader className="pb-2">
                <div className="mb-2">{feature.icon}</div>
                <CardTitle className="text-xl font-semibold text-property-primary">
                  {feature.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-gray-600 text-base">
                  {feature.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Features;
