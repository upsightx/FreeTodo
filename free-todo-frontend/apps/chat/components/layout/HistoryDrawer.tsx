import { Loader2 } from "lucide-react";
import type { ChatSessionSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

type HistoryDrawerProps = {
	historyLoading: boolean;
	historyError: string | null;
	sessions: ChatSessionSummary[];
	conversationId: string | null;
	labels: {
		noHistory: string;
		loading: string;
		chatHistory: string;
	};
	onSelectSession: (id: string) => void;
	className?: string;
	listClassName?: string;
};

export function HistoryDrawer({
	historyLoading,
	historyError,
	sessions,
	conversationId,
	labels,
	onSelectSession,
	className,
	listClassName,
}: HistoryDrawerProps) {
	return (
		<div
			className={cn("border-b border-border bg-muted/40 px-4 py-3", className)}
		>
			{historyLoading && (
				<div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
					<Loader2 className="h-3.5 w-3.5 animate-spin" />
					{labels.loading}
				</div>
			)}
			{historyError && (
				<p className="text-xs text-destructive">{historyError}</p>
			)}
			{!historyError && (
				<div
					className={cn(
						"max-h-72 space-y-2 overflow-y-auto pr-1",
						listClassName,
					)}
				>
					{!historyLoading && sessions.length === 0 ? (
						<p className="text-xs text-muted-foreground">{labels.noHistory}</p>
					) : (
						sessions.map((session, index) => (
							<button
								key={
									session.sessionId
										? `${session.sessionId}-${index}`
										: `session-${index}`
								}
								type="button"
								onClick={() => onSelectSession(session.sessionId)}
								disabled={historyLoading}
								className={cn(
									"w-full rounded-(--radius) border border-border bg-background px-3 py-2 text-left text-sm",
									"transition-colors hover:bg-foreground/5",
									"disabled:cursor-not-allowed disabled:opacity-60",
									session.sessionId === conversationId
										? "ring-2 ring-ring"
										: "",
								)}
							>
								<span className="block truncate font-medium text-foreground">
									{session.title || labels.chatHistory}
								</span>
							</button>
						))
					)}
				</div>
			)}
		</div>
	);
}
