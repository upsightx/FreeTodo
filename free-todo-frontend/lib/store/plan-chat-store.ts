import { create } from "zustand";

type PlanChatEventType = "chat_message" | "chat_chunk" | "chat_message_completed";

export type PlanChatEvent = {
	id: number;
	type: PlanChatEventType;
	sessionId: string;
	role?: "user" | "assistant";
	content?: string;
	stepId?: string;
};

interface PlanChatState {
	lastEventId: number;
	lastEvent: PlanChatEvent | null;
	activeSessions: Record<string, boolean>;
	publishEvent: (event: Omit<PlanChatEvent, "id">) => void;
	markSessionRunning: (sessionId: string, running: boolean) => void;
}

export const usePlanChatStore = create<PlanChatState>((set) => ({
	lastEventId: 0,
	lastEvent: null,
	activeSessions: {},
	publishEvent: (event) =>
		set((state) => ({
			lastEventId: state.lastEventId + 1,
			lastEvent: {
				...event,
				id: state.lastEventId + 1,
			},
		})),
	markSessionRunning: (sessionId, running) =>
		set((state) => ({
			activeSessions: {
				...state.activeSessions,
				[sessionId]: running,
			},
		})),
}));
