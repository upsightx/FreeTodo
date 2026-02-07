import React from 'react';
import { Play } from 'lucide-react';
import { NewsItem } from '../types';

interface NewsGridProps {
  stories: NewsItem[];
}

export const NewsGrid: React.FC<NewsGridProps> = ({ stories }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-12 pt-8 border-t-4 border-double border-zinc-800">
      {stories.map((story) => (
        <article key={story.id} className="group flex flex-col h-full cursor-pointer">
          <div className="relative aspect-[3/2] mb-4 overflow-hidden rounded-sm bg-zinc-900 border border-zinc-800">
             <img 
              src={story.imageUrl} 
              alt={story.title}
              className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-all duration-500 group-hover:scale-105"
            />
            <div className="absolute top-2 left-2 bg-black/60 backdrop-blur-md px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-white border border-white/10">
                {story.category}
            </div>
          </div>
          
          <div className="flex-1 flex flex-col">
            <h3 className="font-serif text-xl font-bold text-zinc-100 mb-3 group-hover:text-indigo-300 transition-colors leading-tight">
                {story.title}
            </h3>
            <p className="font-sans text-sm text-zinc-400 line-clamp-3 leading-relaxed mb-4 flex-1">
                {story.summary}
            </p>
            
            <div className="flex items-center justify-between pt-3 border-t border-zinc-800/50 text-xs text-zinc-500 font-mono">
                <span>{story.source}</span>
                <span className="flex items-center gap-1">
                     {(story.likes / 1000).toFixed(1)}k reads
                </span>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
};