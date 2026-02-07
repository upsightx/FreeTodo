import React from 'react';

/**
 * Parses text containing pseudo-markdown.
 * Support:
 * - **bold**
 * - ==highlight==
 * - `code` (optional aesthetic addition)
 */
export const parseStyledText = (text: string): React.ReactNode => {
  if (!text) return null;

  // Split by specific markers. We capture delimiters to know what matches.
  // Regex looks for: (==.*?==) OR (\*\*.*?\*\*)
  const parts = text.split(/(==.*?==|\*\*.*?\*\*)/g);

  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith('==') && part.endsWith('==')) {
          const content = part.slice(2, -2);
          return (
            <span
              key={index}
              className="bg-indigo-500/15 text-indigo-200 border border-indigo-500/20 px-1.5 py-0.5 rounded mx-0.5 text-[0.95em] font-medium shadow-[0_0_10px_rgba(99,102,241,0.1)] transition-all hover:bg-indigo-500/25 cursor-default inline-block leading-snug"
            >
              {content}
            </span>
          );
        } else if (part.startsWith('**') && part.endsWith('**')) {
          const content = part.slice(2, -2);
          return (
            <strong key={index} className="text-white font-semibold tracking-wide">
              {content}
            </strong>
          );
        }
        // Regular text
        return <span key={index} className="opacity-90">{part}</span>;
      })}
    </>
  );
};