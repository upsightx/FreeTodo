import React from 'react';
import { SummaryItem } from '../types';
import { parseStyledText } from '../utils/textParser';
import { motion } from 'framer-motion';

interface Props {
  data: SummaryItem;
  index: number;
}

export const SummarySection: React.FC<Props> = ({ data, index }) => {
  const isLast = false; // logic handled by parent usually, simplified here

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      className="relative pl-6 sm:pl-8 pb-8 last:pb-2"
    >
      {/* Timeline Line */}
      <div className="absolute left-0 top-2 bottom-0 w-px bg-gradient-to-b from-indigo-500/50 via-slate-700/30 to-transparent" />
      
      {/* Timeline Dot (Numbered Badge) */}
      <div className="absolute left-[-11px] top-0 flex items-center justify-center">
         <div className="relative flex items-center justify-center w-6 h-6 rounded-full bg-slate-900 border border-indigo-500/30 shadow-[0_0_10px_rgba(99,102,241,0.2)]">
            <span className="text-xs font-bold text-indigo-400 font-mono">{index + 1}</span>
            <div className="absolute inset-0 rounded-full bg-indigo-500/10 blur-[2px]" />
         </div>
      </div>

      {/* Header */}
      {data.title && (
        <h3 className="text-base sm:text-lg font-semibold text-slate-100 mb-3 flex items-center gap-2">
           {/* Parse title to allow styling if needed, though usually titles are plain text */}
           {parseStyledText(data.title)}
        </h3>
      )}

      {/* Content */}
      <div className="text-sm sm:text-base text-slate-300 leading-7 font-light tracking-wide">
        {data.type === 'paragraph' && (
           <p className="mb-2">{data.content && parseStyledText(data.content)}</p>
        )}

        {data.type === 'list' && (
          <ul className="flex flex-col gap-3">
            {data.items?.map((item, idx) => (
              <li key={idx} className="relative pl-0 group">
                <div className="flex gap-3 items-start">
                    <span className="mt-2.5 w-1.5 h-1.5 min-w-[6px] rounded-full bg-slate-600 group-hover:bg-indigo-400 transition-colors duration-300" />
                    <span className="flex-1 transition-colors duration-300 group-hover:text-slate-200">
                        {parseStyledText(item)}
                    </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </motion.div>
  );
};