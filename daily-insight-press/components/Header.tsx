import React from 'react';
import { Calendar, CloudSun, RefreshCw } from 'lucide-react';

export const Header: React.FC = () => {
  const currentDate = new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  });

  return (
    <header className="mb-8 border-b-4 border-zinc-700 pb-2">
      <div className="flex justify-between items-center text-xs text-ink-400 font-sans tracking-widest border-b border-zinc-800 pb-1 mb-4 uppercase">
        <div className="flex items-center gap-2">
          <Calendar size={12} />
          <span>{currentDate}</span>
        </div>
        <div className="flex items-center gap-2">
          <CloudSun size={12} />
          <span>Beijing, Clear -2°C</span>
        </div>
      </div>

      <div className="text-center relative py-2">
        <h1 className="font-serif text-5xl md:text-7xl font-bold tracking-tight text-white mb-2">
          热点速递
        </h1>
        <p className="font-serif italic text-ink-400 text-lg">Daily Social Insights & Media Digest</p>
        
        {/* Decorative Lines mimicking newspaper layout */}
        <div className="absolute top-1/2 left-0 w-4 md:w-24 h-[1px] bg-zinc-700 hidden md:block"></div>
        <div className="absolute top-1/2 right-0 w-4 md:w-24 h-[1px] bg-zinc-700 hidden md:block"></div>
      </div>

      <div className="flex justify-between items-end mt-4 border-t border-zinc-800 pt-2">
        <div className="text-xs text-ink-400 font-mono">
          Vol. 2026-01-25 • No. 3 Edition
        </div>
        <button className="flex items-center gap-2 text-xs font-bold text-zinc-300 hover:text-white transition-colors uppercase tracking-wider">
          <RefreshCw size={12} />
          Refresh Feed
        </button>
      </div>
    </header>
  );
};