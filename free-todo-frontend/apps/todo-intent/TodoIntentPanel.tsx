"use client";

import { BrainCircuit } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { PanelHeader } from "@/components/common/layout/PanelHeader";
import { Button } from "@/components/ui/button";
import {
	type TodoIntentConnectionState,
	type TodoIntentProcessingRecord,
	useTodoIntentStreamStore,
} from "@/lib/store/todo-intent-stream-store";
import { cn, formatDateTime } from "@/lib/utils";

const BOTTOM_THRESHOLD_PX = 40;
const MARKDOWN_COLLAPSED_HEIGHT = 192;
type EventModality = "audio" | "image" | "text";

interface TodoIntentEventRefView {
	eventId: string;
	source: string;
	modality: EventModality | "unknown";
	sequenceId: number | null;
	timestamp: string | null;
}

const MODALITY_SORT_ORDER: Record<EventModality, number> = {
	audio: 0,
	image: 1,
	text: 2,
};

const markdownComponents: Components = {
	h1: ({ node: _node, ...props }) => (
		<h1 className="text-base font-semibold text-foreground mt-2 mb-1" {...props} />
	),
	h2: ({ node: _node, ...props }) => (
		<h2 className="text-sm font-semibold text-foreground mt-2 mb-1" {...props} />
	),
	h3: ({ node: _node, ...props }) => (
		<h3 className="text-sm font-semibold text-foreground mt-1.5 mb-1" {...props} />
	),
	p: ({ node: _node, ...props }) => (
		<p className="my-1 leading-relaxed text-inherit" {...props} />
	),
	ul: ({ node: _node, ...props }) => (
		<ul className="my-1 ml-4 list-disc space-y-0.5 text-inherit" {...props} />
	),
	ol: ({ node: _node, ...props }) => (
		<ol className="my-1 ml-4 list-decimal space-y-0.5 text-inherit" {...props} />
	),
	li: ({ node: _node, ...props }) => <li className="text-inherit" {...props} />,
	blockquote: ({ node: _node, ...props }) => (
		<blockquote className="my-1 border-l-2 border-border pl-3 text-muted-foreground" {...props} />
	),
	code: ({ node: _node, className, children, ...props }) => {
		const isInline = !className;
		return isInline ? (
			<code
				className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.85em] text-foreground"
				{...props}
			>
				{children}
			</code>
		) : (
			<code className={className} {...props}>
				{children}
			</code>
		);
	},
	pre: ({ node: _node, ...props }) => (
		<pre className="my-2 overflow-x-auto rounded-md bg-muted p-2 text-xs" {...props} />
	),
	a: ({ node: _node, ...props }) => (
		<a
			className="text-primary underline underline-offset-2 hover:text-primary/80"
			target="_blank"
			rel="noopener noreferrer"
			{...props}
		/>
	),
};

function asObject(value: unknown): Record<string, unknown> | null {
	return value && typeof value === "object" && !Array.isArray(value)
		? (value as Record<string, unknown>)
		: null;
}

function normalizeEventRefs(metadata: Record<string, unknown>): TodoIntentEventRefView[] {
	const rawRefs = metadata.event_refs;
	if (!Array.isArray(rawRefs)) return [];

	const normalized: TodoIntentEventRefView[] = [];
	for (const raw of rawRefs) {
		const obj = asObject(raw);
		if (!obj) continue;
		const eventId = typeof obj.event_id === "string" ? obj.event_id.trim() : "";
		if (!eventId) continue;

		const source = typeof obj.source === "string" ? obj.source.trim() : "";
		const rawModality = typeof obj.modality === "string" ? obj.modality.trim() : "";
		const modality: TodoIntentEventRefView["modality"] =
			rawModality === "audio" || rawModality === "image" || rawModality === "text"
				? rawModality
				: "unknown";
		const sequenceId =
			typeof obj.sequence_id === "number" && Number.isFinite(obj.sequence_id)
				? obj.sequence_id
				: null;
		const timestamp = typeof obj.timestamp === "string" ? obj.timestamp : null;

		normalized.push({
			eventId,
			source,
			modality,
			sequenceId,
			timestamp,
		});
	}

	normalized.sort((a, b) => {
		const modalityOrderA =
			a.modality === "unknown" ? 99 : MODALITY_SORT_ORDER[a.modality];
		const modalityOrderB =
			b.modality === "unknown" ? 99 : MODALITY_SORT_ORDER[b.modality];
		if (modalityOrderA !== modalityOrderB) return modalityOrderA - modalityOrderB;

		if (a.sequenceId !== null && b.sequenceId !== null && a.sequenceId !== b.sequenceId) {
			return a.sequenceId - b.sequenceId;
		}

		const at = a.timestamp ? Date.parse(a.timestamp) : Number.NaN;
		const bt = b.timestamp ? Date.parse(b.timestamp) : Number.NaN;
		if (!Number.isNaN(at) && !Number.isNaN(bt) && at !== bt) {
			return at - bt;
		}

		return a.eventId.localeCompare(b.eventId);
	});

	return normalized;
}

function shortEventId(eventId: string): string {
	if (eventId.length <= 14) return eventId;
	return `${eventId.slice(0, 8)}...${eventId.slice(-4)}`;
}

function modalityTone(modality: TodoIntentEventRefView["modality"]): string {
	switch (modality) {
		case "audio":
			return "bg-sky-50 text-sky-700 border-sky-200";
		case "image":
			return "bg-emerald-50 text-emerald-700 border-emerald-200";
		case "text":
			return "bg-slate-50 text-slate-700 border-slate-200";
		default:
			return "bg-muted text-muted-foreground border-border";
	}
}

function modalityLabel(
	modality: TodoIntentEventRefView["modality"],
	tPerception: ReturnType<typeof useTranslations>,
): string {
	switch (modality) {
		case "audio":
			return tPerception("audio");
		case "image":
			return tPerception("image");
		case "text":
			return tPerception("text");
		default:
			return "Unknown";
	}
}

function isNearBottom(el: HTMLDivElement): boolean {
	return el.scrollHeight - el.clientHeight - el.scrollTop <= BOTTOM_THRESHOLD_PX;
}

function ConnectionStatus({
	connectionState,
}: {
	connectionState: TodoIntentConnectionState;
}) {
	const t = useTranslations("todoIntentPanel");
	const isConnected = connectionState === "connected";
	const isReconnecting = connectionState === "reconnecting" || connectionState === "connecting";

	return (
		<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
			<span
				className={cn(
					"h-2 w-2 rounded-full",
					isConnected && "bg-green-500 animate-pulse",
					!isConnected && isReconnecting && "bg-amber-500 animate-pulse",
					!isConnected && !isReconnecting && "bg-red-500",
				)}
			/>
			{isConnected
				? t("connected")
				: isReconnecting
					? t("reconnecting")
					: t("disconnected")}
		</div>
	);
}

function statusTone(status: TodoIntentProcessingRecord["status"]): string {
	switch (status) {
		case "extracted":
			return "bg-green-50 text-green-700 border-green-200";
		case "gate_skipped":
		case "dedupe_hit":
			return "bg-amber-50 text-amber-700 border-amber-200";
		case "failed":
			return "bg-red-50 text-red-700 border-red-200";
		default:
			return "bg-muted text-muted-foreground border-border";
	}
}

function CollapsibleMarkdown({
	content,
	maxCollapsedHeight = MARKDOWN_COLLAPSED_HEIGHT,
	contentClassName,
}: {
	content: string;
	maxCollapsedHeight?: number;
	contentClassName?: string;
}) {
	const t = useTranslations("todoIntentPanel");
	const contentRef = useRef<HTMLDivElement>(null);
	const [expanded, setExpanded] = useState(false);
	const [overflowing, setOverflowing] = useState(false);

	useEffect(() => {
		const el = contentRef.current;
		if (!el) return;

		const checkOverflow = () => {
			const target = contentRef.current;
			if (!target) return;
			setOverflowing(target.scrollHeight > maxCollapsedHeight + 2);
		};

		checkOverflow();

		const resizeObserver = new ResizeObserver(() => {
			checkOverflow();
		});
		resizeObserver.observe(el);

		window.addEventListener("resize", checkOverflow);
		return () => {
			resizeObserver.disconnect();
			window.removeEventListener("resize", checkOverflow);
		};
	}, [maxCollapsedHeight]);

	return (
		<div className="space-y-1">
			<div
				ref={contentRef}
				className={cn(
					"markdown-content break-words",
					!expanded && "overflow-hidden",
					contentClassName,
				)}
				style={expanded ? undefined : { maxHeight: `${maxCollapsedHeight}px` }}
			>
				<ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
					{content}
				</ReactMarkdown>
			</div>
			{overflowing && (
				<Button
					type="button"
					variant="ghost"
					size="sm"
					className="h-6 px-1 text-xs text-muted-foreground hover:text-foreground"
					onClick={() => setExpanded((prev) => !prev)}
				>
					{expanded ? t("collapse") : t("expand")}
				</Button>
			)}
		</div>
	);
}

function RecordCard({ record }: { record: TodoIntentProcessingRecord }) {
	const t = useTranslations("todoIntentPanel");
	const tPerception = useTranslations("perceptionStream");
	const metadata = record.metadata ?? {};
	const appName = String(metadata.app_name ?? "");
	const windowTitle = String(metadata.window_title ?? "");
	const speaker = String(metadata.speaker ?? "");
	const eventRefs = normalizeEventRefs(metadata);
	const timeWindow = `${formatDateTime(record.time_window_start, "HH:mm:ss")} - ${formatDateTime(record.time_window_end, "HH:mm:ss")}`;

	return (
		<div className="rounded-lg border bg-background p-3 shadow-sm">
			<div className="flex items-start justify-between gap-2">
				<div className="flex flex-wrap items-center gap-1.5">
					<span
						className={cn(
							"inline-flex h-6 items-center rounded-md border px-2 text-xs font-medium",
							statusTone(record.status),
						)}
					>
						{t(`status.${record.status}`)}
					</span>
					{record.gate_decision && (
						<span className="inline-flex h-6 items-center rounded-md border px-2 text-xs font-medium">
							{record.gate_decision.should_extract
								? t("gate.pass")
								: t("gate.skip")}
						</span>
					)}
				</div>
				<div className="text-xs tabular-nums text-muted-foreground">
					{formatDateTime(record.created_at, "HH:mm:ss")}
				</div>
			</div>

			<div className="mt-2 grid grid-cols-1 gap-1 text-xs text-muted-foreground sm:grid-cols-2">
				<div>
					{t("app")}: {appName || "-"}
				</div>
				<div>
					{t("window")}: {windowTitle || "-"}
				</div>
				<div>
					{t("speaker")}: {speaker || "-"}
				</div>
				<div>
					{t("sources")}:{" "}
					{record.source_set.length > 0 ? record.source_set.join(", ") : "-"}
				</div>
				<div>
					{t("timeWindow")}: {timeWindow}
				</div>
			</div>

			{eventRefs.length > 0 && (
				<div className="mt-2">
					<div className="text-[11px] font-medium text-muted-foreground">
						{t("events")} ({eventRefs.length})
					</div>
					<div className="mt-1 flex flex-wrap gap-1.5">
						{eventRefs.map((eventRef) => (
							<span
								key={eventRef.eventId}
								className={cn(
									"inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px]",
									modalityTone(eventRef.modality),
								)}
								title={`event_id: ${eventRef.eventId}\nsource: ${eventRef.source || "-"}`}
							>
								<span className="font-medium">
									{modalityLabel(eventRef.modality, tPerception)}
								</span>
								<span className="opacity-70">#</span>
								<span className="font-mono">{shortEventId(eventRef.eventId)}</span>
							</span>
						))}
					</div>
				</div>
			)}

			<div className="mt-2 rounded-md border bg-muted/40 p-2">
				<div className="mb-1 text-[11px] font-medium text-muted-foreground">
					{t("mergedText")}
				</div>
				<CollapsibleMarkdown
					content={record.merged_text || "-"}
					maxCollapsedHeight={220}
					contentClassName="text-sm text-foreground"
				/>
			</div>

			{record.gate_decision && (
				<div className="mt-2 text-xs text-muted-foreground">
					{t("gateReason")}: {record.gate_decision.reason || "-"}
				</div>
			)}

			{record.candidates.length > 0 && (
				<div className="mt-3 space-y-2">
					<div className="text-xs font-medium text-muted-foreground">
						{t("todos")} ({record.candidates.length})
					</div>
					{record.candidates.map((candidate, index) => (
						<div key={`${record.record_id}-${index}`} className="rounded-md border p-2">
							<div className="text-sm font-medium">{candidate.name}</div>
							{candidate.description && (
								<CollapsibleMarkdown
									content={candidate.description}
									maxCollapsedHeight={120}
									contentClassName="mt-1 text-xs text-muted-foreground"
								/>
							)}
							<div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
								<span>{t("due")}: {candidate.due || "-"}</span>
								<span>{t("confidence")}: {candidate.confidence.toFixed(2)}</span>
								<span>{t("priority")}: {candidate.priority || "none"}</span>
							</div>
							{candidate.source_text && (
								<div className="mt-1">
									<div className="text-xs text-muted-foreground">{t("sourceText")}:</div>
									<CollapsibleMarkdown
										content={candidate.source_text}
										maxCollapsedHeight={120}
										contentClassName="text-xs text-muted-foreground"
									/>
								</div>
							)}
						</div>
					))}
				</div>
			)}

			{record.integration_results.length > 0 && (
				<div className="mt-3 space-y-1">
					<div className="text-xs font-medium text-muted-foreground">
						{t("integration")}
					</div>
					{record.integration_results.map((result, index) => (
						<div
							key={`${record.record_id}-integration-${index}`}
							className="text-xs text-muted-foreground"
						>
							{result.action} {result.reason ? `(${result.reason})` : ""}
						</div>
					))}
				</div>
			)}

			{record.error && (
				<div className="mt-2 text-xs text-red-600">
					{t("error")}: {record.error}
				</div>
			)}
		</div>
	);
}

export function TodoIntentPanel() {
	const t = useTranslations("todoIntentPanel");
	const records = useTodoIntentStreamStore((s) => s.records);
	const connectionState = useTodoIntentStreamStore((s) => s.connectionState);
	const connect = useTodoIntentStreamStore((s) => s.connect);
	const disconnect = useTodoIntentStreamStore((s) => s.disconnect);
	const loadRecent = useTodoIntentStreamStore((s) => s.loadRecent);
	const clearRecords = useTodoIntentStreamStore((s) => s.clearRecords);
	const scrollRef = useRef<HTMLDivElement>(null);
	const [pinnedToBottom, setPinnedToBottom] = useState(true);

	const latestRecordId = records.length > 0 ? records[records.length - 1].record_id : null;

	useEffect(() => {
		connect();
		return () => disconnect();
	}, [connect, disconnect]);

	useEffect(() => {
		if (!latestRecordId) return;
		const el = scrollRef.current;
		if (!el) return;
		if (!pinnedToBottom) return;
		el.scrollTop = el.scrollHeight;
	}, [latestRecordId, pinnedToBottom]);

	const handleScroll = () => {
		const el = scrollRef.current;
		if (!el) return;
		const nextPinned = isNearBottom(el);
		setPinnedToBottom((prev) => (prev === nextPinned ? prev : nextPinned));
	};

	const jumpToLatest = () => {
		const el = scrollRef.current;
		if (!el) return;
		el.scrollTop = el.scrollHeight;
		setPinnedToBottom(true);
	};

	return (
		<div className="flex h-full flex-col overflow-hidden bg-background">
			<PanelHeader
				icon={BrainCircuit}
				title={t("title")}
				actions={
					<div className="flex items-center gap-2">
						<Button
							type="button"
							variant="outline"
							size="sm"
							className="h-7 px-2 text-xs"
							onClick={() => void loadRecent(50)}
						>
							{t("loadRecent")}
						</Button>
						<Button
							type="button"
							variant="outline"
							size="sm"
							className="h-7 px-2 text-xs"
							onClick={() => void loadRecent(200)}
						>
							{t("loadMore")}
						</Button>
						<Button
							type="button"
							variant="outline"
							size="sm"
							className="h-7 px-2 text-xs"
							onClick={clearRecords}
						>
							{t("clear")}
						</Button>
						<ConnectionStatus connectionState={connectionState} />
					</div>
				}
			/>

			{records.length === 0 ? (
				<div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
					{t("noRecords")}
				</div>
			) : (
				<div className="relative flex-1 overflow-hidden">
					<div
						ref={scrollRef}
						className="h-full overflow-y-auto"
						onScroll={handleScroll}
					>
						<div className="flex flex-col gap-2 p-4">
							{records.map((record) => (
								<RecordCard key={record.record_id} record={record} />
							))}
						</div>
					</div>
					{!pinnedToBottom && (
						<div className="absolute right-4 bottom-4">
							<Button type="button" variant="outline" size="sm" onClick={jumpToLatest}>
								{t("jumpToLatest")}
							</Button>
						</div>
					)}
				</div>
			)}
		</div>
	);
}
