import React from 'react';
import { AISummaryCard } from './components/AISummaryCard';
import { SummaryData } from './types';

// Mock Data reproducing the content from the user's screenshot
const mockSummaryData: SummaryData = {
  title: "AI 总结摘要",
  sections: [
    {
      id: "1",
      type: "paragraph",
      title: "**今日热点**",
      content: "电脑选购与==DIY==成为绝对主旋律，==知乎==集中爆发2026年2月多篇高互动配置推荐（如==Liang科技==等）。"
    },
    {
      id: "2",
      type: "list",
      title: "**高热内容**",
      items: [
        "==“2026年哪一款笔记本电脑值得买？”==（Liang科技，知乎，点赞66114）==：== 开学季刚需+高性能本关注度极高。",
        "==“@张小胖哈哈哈(03x9m9yxckmtgztm) 的精彩视频”==（快手，分享344万）==：== 依赖账号流量分发。",
        "==“爱喝牛奶的建议反复观看”==（课代表小邹邹，微博，点赞4377）==：== 垂类知识型博主+强节奏剪辑。"
      ]
    },
    {
      id: "3",
      type: "list",
      title: "**值得关注**",
      items: [
        "==知乎“电脑是否仍必要”系列讨论==（如==向死而生==《年轻人不喜欢用电脑》、==成哥==相关回答）。",
        "==乌镇相关帖文在贴吧集体冷启动==（如==量估==乌镇峰会AI议题、==仲夏的夜==名人纪念帖等）。"
      ]
    }
  ]
};

function App() {
  return (
    <div className="min-h-screen w-full bg-[#020617] text-slate-200 p-4 sm:p-10 flex flex-col items-center justify-start bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-950/40 via-[#020617] to-[#020617]">
      <header className="mb-10 text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight text-white">Interface Redesign</h1>
        <p className="text-slate-400">Reimagining the AI output for better readability and aesthetics.</p>
      </header>
      
      <AISummaryCard summary={mockSummaryData} />
      
      <div className="text-center text-slate-600 text-sm mt-20">
        <p>Demo showing React 18 + Tailwind + Framer Motion</p>
      </div>
    </div>
  );
}

export default App;