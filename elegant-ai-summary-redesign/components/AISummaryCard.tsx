import React, { useState } from 'react';
import { SummaryData } from '../types';
import { SummarySection } from './SummarySection';
import { Sparkles, ChevronDown, ChevronUp, Share2, Copy } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  summary: SummaryData;
}

export const AISummaryCard: React.FC<Props> = ({ summary }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="w-full max-w-3xl mx-auto my-10 px-4 sm:px-0">
      <div className="group relative overflow-hidden rounded-2xl bg-slate-900/40 backdrop-blur-xl border border-glass-border shadow-2xl">
        
        {/* Subtle Ambient Glow Background */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/10 rounded-full blur-[100px] -z-10 pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-violet-600/5 rounded-full blur-[80px] -z-10 pointer-events-none" />

        {/* Header Section */}
        <div 
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center justify-between px-6 py-5 cursor-pointer bg-white/5 border-b border-white/5 hover:bg-white/10 transition-colors duration-300"
        >
            <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20">
                    <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                    <h2 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-200 to-slate-400">
                        {summary.title}
                    </h2>
                    <p className="text-xs text-slate-400 font-medium tracking-wider uppercase opacity-70">
                        AI Generated Digest
                    </p>
                </div>
            </div>
            
            <div className="flex items-center gap-2">
                <button 
                    className="p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-all"
                    title="Toggle View"
                >
                    {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </button>
            </div>
        </div>

        {/* Content Body */}
        <AnimatePresence initial={false}>
            {isExpanded && (
                <motion.div
                    initial="collapsed"
                    animate="open"
                    exit="collapsed"
                    variants={{
                        open: { opacity: 1, height: 'auto' },
                        collapsed: { opacity: 0, height: 0 }
                    }}
                    transition={{ duration: 0.4, ease: [0.04, 0.62, 0.23, 0.98] }}
                >
                    <div className="p-6 sm:p-8 pt-8">
                        <div className="relative pl-2">
                             {/* Content Render */}
                            {summary.sections.map((section, index) => (
                                <SummarySection key={section.id} data={section} index={index} />
                            ))}
                        </div>

                        {/* Footer Actions */}
                        <div className="mt-8 pt-6 border-t border-white/5 flex items-center justify-between text-xs text-slate-500">
                            <span>Generated via Gemini 2.0 Flash</span>
                            <div className="flex gap-4">
                                <button className="flex items-center gap-1.5 hover:text-indigo-300 transition-colors">
                                    <Copy size={14} /> Copy
                                </button>
                                <button className="flex items-center gap-1.5 hover:text-indigo-300 transition-colors">
                                    <Share2 size={14} /> Share
                                </button>
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
      </div>
    </div>
  );
};