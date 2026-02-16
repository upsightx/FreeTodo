import { create, type StateCreator } from "zustand";

export type PerceptionSource =
	| "mic_pc"
	| "mic_hardware"
	| "ocr_screen"
	| "ocr_proactive"
	| "user_input";

export type PerceptionModality = "audio" | "image" | "text";

export interface PerceptionEvent {
	event_id: string;
	sequence_id: number;
	timestamp: string;
	ingested_at: string | null;
	source: PerceptionSource;
	modality: PerceptionModality;
	content_text: string;
	content_raw?: string | null;
	metadata: Record<string, unknown>;
	priority: number;
}

export interface StreamFilter {
	sources: Set<PerceptionSource>;
	modalities: Set<PerceptionModality>;
}

export type PerceptionConnectionState =
	| "disconnected"
	| "connecting"
	| "connected"
	| "reconnecting";

interface PerceptionStreamState {
	events: PerceptionEvent[];
	connectionState: PerceptionConnectionState;
	filter: StreamFilter;
	connect: () => void;
	disconnect: () => void;
	loadRecentEvents: (count?: number) => Promise<void>;
	setFilter: (filter: Partial<StreamFilter>) => void;
	clearEvents: () => void;
}

const MAX_EVENTS = 200;
const RECONNECT_DELAY_MS = 1500;

const WS_PATH_CANDIDATES = ["/api/perception/stream", "/perception/stream"] as const;
const RECENT_PATH_CANDIDATES = [
	"/api/perception/events/recent",
	"/perception/events/recent",
] as const;

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let shouldReconnect = false;
let activeWsPath: (typeof WS_PATH_CANDIDATES)[number] | null = null;

function getApiBaseUrl(): string {
	return (
		process.env.NEXT_PUBLIC_API_URL ||
		(typeof window !== "undefined" &&
			(window as Window & { __BACKEND_URL__?: string }).__BACKEND_URL__) ||
		"http://127.0.0.1:8100"
	);
}

function buildWsUrl(path: string): string {
	const apiBaseUrl = getApiBaseUrl();
	const wsBaseUrl = apiBaseUrl
		.replace("http://", "ws://")
		.replace("https://", "wss://");
	return `${wsBaseUrl}${path}`;
}

function appendAndDedupeEvents(
	existing: PerceptionEvent[],
	incoming: PerceptionEvent[],
): PerceptionEvent[] {
	if (incoming.length === 0) return existing;
	const seen = new Set(existing.map((e) => e.event_id));
	const merged = [...existing];
	for (const e of incoming) {
		if (seen.has(e.event_id)) continue;
		seen.add(e.event_id);
		merged.push(e);
	}
	merged.sort((a, b) => (a.sequence_id ?? 0) - (b.sequence_id ?? 0));
	return merged.slice(-MAX_EVENTS);
}

async function loadRecentBestEffort(
	set: Parameters<StateCreator<PerceptionStreamState>>[0],
	count: number,
): Promise<void> {
	try {
		const recent = await fetchRecentEvents(count);
		if (recent.length === 0) return;
		set((state) => ({
			events: appendAndDedupeEvents(state.events, recent),
		}));
	} catch {}
}

async function fetchRecentEvents(count: number): Promise<PerceptionEvent[]> {
	const query = `?count=${encodeURIComponent(String(count))}`;

	for (const path of RECENT_PATH_CANDIDATES) {
		const relUrl = `${path}${query}`;
		try {
			const res = await fetch(relUrl);
			if (res.ok) return (await res.json()) as PerceptionEvent[];
		} catch {}

		try {
			const absUrl = `${getApiBaseUrl()}${path}${query}`;
			const res = await fetch(absUrl);
			if (res.ok) return (await res.json()) as PerceptionEvent[];
		} catch {}
	}

	return [];
}

function clearReconnectTimer(): void {
	if (reconnectTimer) {
		clearTimeout(reconnectTimer);
		reconnectTimer = null;
	}
}

function closeWs(): void {
	try {
		ws?.close();
	} catch {}
	ws = null;
}

function connectWithFallback(
	set: Parameters<StateCreator<PerceptionStreamState>>[0],
	candidateIndex: number,
	isReconnectAttempt: boolean,
): void {
	if (!shouldReconnect) return;
	if (ws) return;

	const candidate = WS_PATH_CANDIDATES[candidateIndex];
	if (!candidate) {
		set({ connectionState: "disconnected" });
		void loadRecentBestEffort(set, 50);
		return;
	}

	set({ connectionState: isReconnectAttempt ? "reconnecting" : "connecting" });
	const wsUrl = buildWsUrl(candidate);
	const socket = new WebSocket(wsUrl);
	ws = socket;

	let opened = false;
	const openTimeout = setTimeout(() => {
		if (opened) return;
		if (ws !== socket) return;
		closeWs();
		connectWithFallback(set, candidateIndex + 1, isReconnectAttempt);
	}, 2000);

	socket.onopen = () => {
		opened = true;
		activeWsPath = candidate;
		clearTimeout(openTimeout);
		set({ connectionState: "connected" });
	};

	socket.onclose = () => {
		clearTimeout(openTimeout);
		if (ws === socket) ws = null;
		set({ connectionState: "disconnected" });

		if (!shouldReconnect) return;
		clearReconnectTimer();
		reconnectTimer = setTimeout(() => {
			if (!shouldReconnect) return;
			const retryPath = activeWsPath ?? WS_PATH_CANDIDATES[0];
			const retryIndex = WS_PATH_CANDIDATES.indexOf(retryPath);
			connectWithFallback(set, Math.max(0, retryIndex), true);
		}, RECONNECT_DELAY_MS);
	};

	socket.onmessage = (msg) => {
		try {
			const event = JSON.parse(String(msg.data)) as PerceptionEvent;
			set((state) => ({
				events: appendAndDedupeEvents(state.events, [event]),
			}));
		} catch {}
	};
}

export const usePerceptionStreamStore = create<PerceptionStreamState>((set) => ({
	events: [],
	connectionState: "disconnected",
	filter: { sources: new Set(), modalities: new Set() },

	connect: () => {
		shouldReconnect = true;
		clearReconnectTimer();
		void loadRecentBestEffort(set, 50);
		connectWithFallback(set, 0, false);
	},

	disconnect: () => {
		shouldReconnect = false;
		clearReconnectTimer();
		closeWs();
		set({ connectionState: "disconnected" });
	},

	loadRecentEvents: async (count = 50) => {
		const recent = await fetchRecentEvents(count);
		set((state) => ({
			events: appendAndDedupeEvents(state.events, recent),
		}));
	},

	setFilter: (partial) =>
		set((state) => ({
			filter: {
				sources: partial.sources ?? state.filter.sources,
				modalities: partial.modalities ?? state.filter.modalities,
			},
		})),

	clearEvents: () => set({ events: [] }),
}));
