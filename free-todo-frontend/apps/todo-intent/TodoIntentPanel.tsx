"use client";

import { BrainCircuit } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { PanelHeader } from "@/components/common/layout/PanelHeader";
import { Button } from "@/components/ui/button";
import {
	type TodoIntentConnectionState,
	type TodoIntentProcessingRecord,
	useTodoIntentStreamStore,
} from "@/lib/store/todo-intent-stream-store";
import { cn, formatDateTime } from "@/lib/utils";

const BOTTOM_THRESHOLD_PX = 40;

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

function RecordCard({ record }: { record: TodoIntentProcessingRecord }) {
	const t = useTranslations("todoIntentPanel");
	const metadata = record.metadata ?? {};
	const appName = String(metadata.app_name ?? "");
	const windowTitle = String(metadata.window_title ?? "");
	const speaker = String(metadata.speaker ?? "");
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

			<div className="mt-2 rounded-md border bg-muted/40 p-2">
				<div className="mb-1 text-[11px] font-medium text-muted-foreground">
					{t("mergedText")}
				</div>
				<div className="text-sm whitespace-pre-wrap break-words">
					{record.merged_text || "-"}
				</div>
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
								<div className="mt-1 text-xs text-muted-foreground whitespace-pre-wrap break-words">
									{candidate.description}
								</div>
							)}
							<div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
								<span>{t("due")}: {candidate.due || "-"}</span>
								<span>{t("confidence")}: {candidate.confidence.toFixed(2)}</span>
								<span>{t("priority")}: {candidate.priority || "none"}</span>
							</div>
							{candidate.source_text && (
								<div className="mt-1 text-xs text-muted-foreground whitespace-pre-wrap break-words">
									{t("sourceText")}: {candidate.source_text}
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
