"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span className="text-white text-xl">🤖</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">
                AI Advisory Board
              </h1>
              <p className="text-xs text-blue-300">
                Powered by Microsoft Agent Framework
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
              ● Connected
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Advisor Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {[
            { emoji: "📊", title: "Strategy", desc: "Market & growth" },
            { emoji: "💰", title: "Finance", desc: "ROI & funding" },
            { emoji: "⚖️", title: "Legal", desc: "Compliance & IP" },
            { emoji: "🔧", title: "Tech", desc: "Architecture" },
          ].map((card) => (
            <div
              key={card.title}
              className="p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm text-center hover:bg-white/10 transition-colors"
            >
              <span className="text-2xl">{card.emoji}</span>
              <h3 className="text-sm font-semibold text-white mt-2">
                {card.title}
              </h3>
              <p className="text-xs text-blue-300">{card.desc}</p>
            </div>
          ))}
        </div>

        {/* Chat Interface */}
        <div className="rounded-2xl overflow-hidden border border-white/10 shadow-2xl h-[600px]">
          <CopilotKit runtimeUrl="http://localhost:8000/api/copilotkit">
            <CopilotChat
              labels={{
                title: "AI Advisory Board",
                initial:
                  "👋 Welcome! I'm your AI Advisory Board concierge. Ask me any business question — I'll connect you with our Strategy, Finance, Legal, or Tech advisors.\n\nTry asking:\n• \"I want to start an AI startup — what should I know?\"\n• \"What's the market size for healthtech?\"\n• \"Help me plan the tech architecture for a SaaS platform\"",
              }}
              className="h-full"
            />
          </CopilotKit>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-blue-400/50 mt-6">
          Built with Microsoft Agent Framework · AG-UI Protocol · CopilotKit
        </p>
      </main>
    </div>
  );
}
