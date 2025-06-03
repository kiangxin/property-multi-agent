
import React from "react";
import { Button } from "@/components/ui/button";

interface HeroProps {
  onTryDemo: () => void;
}

const Hero = ({ onTryDemo }: HeroProps) => {
  return (
    <section className="relative py-20 bg-hero-pattern text-white overflow-hidden">
      <div className="absolute inset-0 bg-gradient-radial from-transparent to-property-dark/50"></div>
      <div className="container mx-auto px-4 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          <div className="space-y-6 animate-fade-in">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight">
              Find Your Dream Property with AI Assistance
            </h1>
            <p className="text-lg md:text-xl opacity-90">
              Our intelligent property chatbot helps you discover, compare, and decide on the perfect property without the hassle.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Button onClick={onTryDemo} size="lg" className="bg-white text-property-primary hover:bg-gray-100">
                Try Demo Now
              </Button>
              <Button variant="outline" size="lg" className="border-white bg-transparent text-property-dark hover:bg-white hover:text-property-primary font-medium">
                Learn More
              </Button>
            </div>
          </div>
          <div className="flex justify-center md:justify-end animate-bounce-in">
            <div className="relative w-full max-w-md aspect-[3/4] rounded-lg bg-white/10 backdrop-blur-sm p-1">
              <div className="absolute inset-0 rounded-lg border border-white/20"></div>
              <div className="h-full w-full rounded-lg bg-gradient-to-br from-property-primary/90 to-property-accent/80 shadow-xl flex items-center justify-center p-6">
                <div className="text-center space-y-2">
                  <div className="text-5xl font-bold">PropertyBot</div>
                  <p className="text-sm opacity-80">Your AI-powered real estate assistant</p>
                  <div className="pt-6">
                    <div className="inline-flex items-center justify-center bg-white/20 backdrop-blur-sm rounded-full px-4 py-2">
                      <span className="animate-pulse inline-block h-2 w-2 mr-2 bg-green-400 rounded-full"></span>
                      <span className="text-xs font-medium">Online & Ready to Help</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
