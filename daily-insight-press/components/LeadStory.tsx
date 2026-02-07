import React from 'react';
import { Play, MessageSquare, Heart, Share2 } from 'lucide-react';
import { NewsItem } from '../types';

interface LeadStoryProps {
  story: NewsItem;
}

export const LeadStory: React.FC<LeadStoryProps> = ({ story }) => {
  return (
    <article className="group cursor-pointer">
      <div className="relative w-full aspect-video overflow-hidden rounded-sm mb-4 border border-zinc-800">
        <img 
          src={story.imageUrl} 
          alt={story.title}
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 opacity-90 group-hover:opacity-100"
        />
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/10 transition-colors">
          <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center border border-white/30 transition-transform group-hover:scale-110">
            <Play className="fill-white text-white ml-1" size={32} />
          </div>
        </div>
        <div className="absolute bottom-3 right-3 bg-black/70 text-white text-xs px-2 py-1 font-mono rounded-sm">
          {story.videoDuration}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-3">
            <span className="bg-zinc-800 text-zinc-300 text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider">
              {story.category}
            </span>
            <span className="text-zinc-500 text-xs font-serif italic">
                By {story.source}
            </span>
        </div>
        
        <h2 className="font-serif text-3xl md:text-4xl font-bold leading-tight text-white group-hover:text-zinc-200 transition-colors">
          {story.title}
        </h2>
        
        <p className="font-sans text-ink-400 text-base leading-relaxed line-clamp-3 md:line-clamp-none">
          {story.summary}
        </p>

        <div className="flex items-center gap-6 pt-2 text-zinc-500 text-sm font-medium border-t border-zinc-900 mt-4">
            <div className="flex items-center gap-1.5 hover:text-zinc-300">
                <Heart size={16} /> <span>{(story.likes / 1000).toFixed(1)}k</span>
            </div>
            <div className="flex items-center gap-1.5 hover:text-zinc-300">
                <MessageSquare size={16} /> <span>{(story.comments / 1000).toFixed(1)}k</span>
            </div>
             <div className="flex items-center gap-1.5 hover:text-zinc-300 ml-auto">
                <Share2 size={16} /> <span>Share</span>
            </div>
        </div>
      </div>
    </article>
  );
};