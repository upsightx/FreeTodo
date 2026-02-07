import React from 'react';
import { createRoot } from 'react-dom/client';
import { Header } from './components/Header';
import { LeadStory } from './components/LeadStory';
import { AiSummaryBox } from './components/AiSummaryBox';
import { NewsGrid } from './components/NewsGrid';
import { BriefsSidebar } from './components/BriefsSidebar';
import { LEAD_STORY, SUB_STORIES, BRIEFS, AI_SUMMARY_TEXT } from './constants';

const App = () => {
  return (
    <div className="min-h-screen bg-black text-white p-2 md:p-8 font-sans selection:bg-indigo-500/30 selection:text-white">
      <div className="max-w-7xl mx-auto bg-[#09090b] p-4 md:p-10 shadow-2xl ring-1 ring-white/5 min-h-[calc(100vh-4rem)]">
        <Header />
        
        <AiSummaryBox text={AI_SUMMARY_TEXT} />
        
        {/* Main Content Layout: 12 Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 mb-12">
            {/* Left Column: Lead Story (8 cols) */}
            <main className="lg:col-span-8">
                <LeadStory story={LEAD_STORY} />
            </main>
            
            {/* Right Column: Briefs / Sidebar (4 cols) */}
            <aside className="lg:col-span-4 pl-0 lg:pl-8 lg:border-l border-zinc-800">
                <BriefsSidebar briefs={BRIEFS} />
            </aside>
        </div>

        {/* Bottom Section: Sub Stories */}
        <NewsGrid stories={SUB_STORIES} />
        
        <footer className="mt-16 pt-8 border-t border-zinc-800 flex flex-col md:flex-row justify-between items-center text-zinc-500 text-sm font-serif">
            <p>&copy; 2026 Daily Insight Press. All rights reserved.</p>
            <div className="flex gap-6 mt-4 md:mt-0 font-sans text-xs tracking-widest uppercase">
                <a href="#" className="hover:text-zinc-300">Privacy</a>
                <a href="#" className="hover:text-zinc-300">Terms</a>
                <a href="#" className="hover:text-zinc-300">About</a>
                <a href="#" className="hover:text-zinc-300">Contact</a>
            </div>
        </footer>
      </div>
    </div>
  );
};

const rootElement = document.getElementById('root');
if (rootElement) {
  const root = createRoot(rootElement);
  root.render(<App />);
}