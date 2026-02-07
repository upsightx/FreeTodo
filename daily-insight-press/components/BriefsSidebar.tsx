import React from 'react';
import { BriefItem } from '../types';
import { Hash, TrendingUp, ChevronRight } from 'lucide-react';

interface BriefsSidebarProps {
  briefs: BriefItem[];
}

export const BriefsSidebar: React.FC<BriefsSidebarProps> = ({ briefs }) => {
  return (
    <div className="h-full">
      <div className="flex items-center gap-2 mb-6 border-b border-zinc-800 pb-2">
        <TrendingUp size={16} className="text-indigo-400" />
        <h3 className="font-sans text-xs font-bold uppercase tracking-[0.2em] text-zinc-400">
          In Brief
        </h3>
      </div>

      <div className="space-y-6">
        {briefs.map((brief, index) => (
          <div key={brief.id} className="group cursor-pointer">
            <div className="flex items-start gap-3">
               <span className="font-serif text-2xl text-zinc-700 font-bold leading-none -mt-1 group-hover:text-zinc-500 transition-colors">
                 {index + 1}
               </span>
               <div>
                 <p className="font-serif text-lg leading-snug text-zinc-200 mb-2 group-hover:text-white transition-colors">
                   {brief.content}
                 </p>
                 <div className="flex flex-wrap gap-2">
                   {brief.tags.map(tag => (
                     <span key={tag} className="inline-flex items-center text-[10px] text-zinc-500 font-mono border border-zinc-800 px-1.5 py-0.5 rounded hover:border-zinc-600 hover:text-zinc-400 transition-colors">
                       <Hash size={8} className="mr-0.5" />
                       {tag}
                     </span>
                   ))}
                 </div>
               </div>
            </div>
            {index !== briefs.length - 1 && (
                <div className="w-12 h-[1px] bg-zinc-800 mt-6 ml-8"></div>
            )}
          </div>
        ))}
      </div>

      <button className="w-full mt-8 py-3 flex items-center justify-center gap-2 text-xs font-bold text-zinc-400 border border-zinc-800 hover:bg-zinc-800 hover:text-white transition-all uppercase tracking-wider group">
        View Archive <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
      </button>
      
      {/* Advertisement Placeholder area often found in newspapers */}
      <div className="mt-12 p-6 bg-zinc-900/50 border border-zinc-800 border-dashed text-center">
        <p className="font-serif italic text-zinc-600 text-sm">Advertisement</p>
        <p className="font-sans font-bold text-zinc-500 mt-1 text-xs tracking-widest uppercase">Subscribe to Premium</p>
      </div>
    </div>
  );
};