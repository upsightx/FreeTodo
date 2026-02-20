"use client";

import { BrainCircuit } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { PanelHeader } from "@/components/common/layout/PanelHeader";
import { Button } from "@/components/ui/button";
import { useTodoIntentStreamStore } from "@/lib/store/todo-intent-stream-store";
import { ConnectionStatus, isNearBottom, RecordCard } from "./TodoIntentPanel.parts";

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
					<div ref={scrollRef} className="h-full overflow-y-auto" onScroll={handleScroll}>
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
