export interface SummaryItem {
  id: string;
  type: 'paragraph' | 'list';
  title?: string; // For the section header (e.g., "Today's Hotspots")
  content?: string; // For paragraph type
  items?: string[]; // For list type
}

export interface SummaryData {
  title: string;
  sections: SummaryItem[];
}