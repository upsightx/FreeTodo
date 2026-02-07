import { NewsItem, BriefItem } from './types';

export const LEAD_STORY: NewsItem = {
  id: '1',
  title: "Facing Cancer, Li Kaifu's Dialogue with Master Hsing Yun: An Epiphany on Life and Death",
  summary: "In a profound conversation that has touched millions, Li Kaifu discusses his battle with stage IV lymphoma and how his dialogue with Master Hsing Yun transformed his view on success, ambition, and the true meaning of life. A journey from 'desperate work' to 'living towards death'.",
  category: "Spiritual Growth",
  imageUrl: "https://picsum.photos/seed/likaifu1/800/450",
  likes: 80000,
  comments: 4600,
  videoDuration: "12:34",
  source: "Mindfulness Daily"
};

export const SUB_STORIES: NewsItem[] = [
  {
    id: '2',
    title: "Li Kaifu on Hiring: What Kind of Talent Does an AI Pioneer Want?",
    summary: "Revealing the core traits looked for in the age of AGI: adaptability, critical thinking, and empathy.",
    category: "Business",
    imageUrl: "https://picsum.photos/seed/talent/400/250",
    likes: 51000,
    comments: 2000,
    source: "Entrepreneur Mag"
  },
  {
    id: '3',
    title: "DeepSeek: The Local Deployment Guide for Enterprise",
    summary: "Why Chinese enterprises are rushing to deploy DeepSeek locally and how it compares to GPT-4.",
    category: "Technology",
    imageUrl: "https://picsum.photos/seed/deepseek/400/250",
    likes: 34000,
    comments: 1500,
    source: "Phoenix Tech"
  },
  {
    id: '4',
    title: "AI Agents: The 8-Minute Breakdown on Efficiency",
    summary: "Not just a tool, but a workforce. How AI Agents are doubling enterprise output in 2026.",
    category: "AI Trends",
    imageUrl: "https://picsum.photos/seed/agent/400/250",
    likes: 14000,
    comments: 800,
    source: "Future Work"
  }
];

export const BRIEFS: BriefItem[] = [
  { id: 'b1', content: "Wang Woming discusses the 'Darkest Hour' at Apple with Li Kaifu.", tags: ['Apple', 'History'] },
  { id: 'b2', content: "Illness revealed my own ignorance and fragility.", tags: ['Health', 'Reflection'] },
  { id: 'b3', content: "Li Kaifu's youngest daughter has a new boyfriend.", tags: ['Celebrity', 'Family'] },
  { id: 'b4', content: "Guo Yingcheng on Private Enterprise AI Empowerment potentials.", tags: ['Business', 'AI'] },
  { id: 'b5', content: "2016 Prediction on Large Models finally comes true.", tags: ['Tech', 'Forecast'] },
  { id: 'b6', content: "Professor Qiu Xipeng's team makes new MOSS discovery.", tags: ['Research', 'MOSS'] },
];

export const AI_SUMMARY_TEXT = "Today's social media landscape is dominated by deep philosophical reflections from Li Kaifu regarding his battle with cancer and his dialogues with Master Hsing Yun. Concurrently, the tech sector is buzzing with discussions on DeepSeek's enterprise deployment and the rise of AI Agents as productivity multipliers. The sentiment leans heavily towards introspection combined with pragmatic technological optimism.";
