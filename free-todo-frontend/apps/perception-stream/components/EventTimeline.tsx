"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { PerceptionEvent } from "@/lib/store/perception-stream-store";
import { EventCard } from "./EventCard";

const BOTTOM_THRESHOLD_PX = 40;

function isNearBottom(el: HTMLDivElement): boolean {
	return el.scrollHeight - el.clientHeight - el.scrollTop <= BOTTOM_THRESHOLD_PX;
}

export function EventTimeline({ events }: { events: PerceptionEvent[] }) {
	const t = useTranslations("perceptionStream");
	const scrollRef = useRef<HTMLDivElement>(null);
	const [pinnedToBottom, setPinnedToBottom] = useState(true);

	const latestEventId = events.length > 0 ? events[events.length - 1].event_id : null;

	useEffect(() => {
		if (!latestEventId) return;
		const el = scrollRef.current;
		if (!el) return;
		if (!pinnedToBottom) return;
		el.scrollTop = el.scrollHeight;
	}, [latestEventId, pinnedToBottom]);

	if (events.length === 0) {
		return (
			<div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
				{t("noEvents")}
			</div>
		);
	}

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
		<div className="relative flex-1 overflow-hidden">
			<div
				ref={scrollRef}
				className="h-full overflow-y-auto"
				onScroll={handleScroll}
			>
				<div className="flex flex-col gap-2 p-4">
					{events.map((e) => (
						<EventCard key={e.event_id} event={e} />
					))}
				</div>
			</div>

			{!pinnedToBottom && (
				<div className="absolute bottom-4 right-4">
					<Button type="button" variant="outline" size="sm" onClick={jumpToLatest}>
						{t("jumpToLatest")}
					</Button>
				</div>
			)}
		</div>
	);
}
