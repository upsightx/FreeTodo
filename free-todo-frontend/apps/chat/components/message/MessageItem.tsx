import { Loader2, MoreVertical } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import type { ExtractionState } from "@/apps/chat/hooks/useMessageExtraction";
import type { ChatMessage } from "@/apps/chat/types";
import { cn } from "@/lib/utils";
import { MessageContent } from "./MessageContent";
import { MessageTodoExtractionPanel } from "./MessageTodoExtractionPanel";
import {
	removeToolCalls,
	removeToolEvents,
} from "./utils/messageContentUtils";

type MessageItemProps = {
	message: ChatMessage;
	isLastMessage: boolean;
	isStreaming: boolean;
	typingText: string;
	extractionState?: ExtractionState;
	onRemoveExtractionState: () => void;
	onMenuButtonClick: (event: React.MouseEvent, messageId: string) => void;
	onMessageBoxRef: (messageId: string, ref: HTMLDivElement | null) => void;
};

export function MessageItem({
	message,
	isLastMessage,
	isStreaming,
	typingText,
	extractionState,
	onRemoveExtractionState,
	onMenuButtonClick,
	onMessageBoxRef,
}: MessageItemProps) {
	const tContextMenu = useTranslations("contextMenu");
	const [hovered, setHovered] = useState(false);

	const sanitizedContent = message.content
		? removeToolEvents(message.content)
		: "";
	// 移除工具调用标记后的内容
	const contentWithoutToolCalls = sanitizedContent
		? removeToolCalls(sanitizedContent)
		: "";
	const trimmedContent = contentWithoutToolCalls.trim();

	// 判断是否是正在等待首次回复的空 assistant 消息
	const isEmptyStreamingMessage =
		isStreaming &&
		isLastMessage &&
		message.role === "assistant" &&
		!trimmedContent;

	// 跳过没有内容的非 streaming assistant 消息
	// 注意：这里使用 contentWithoutToolCalls 来判断，排除工具调用标记
	if (
		!trimmedContent &&
		message.role === "assistant" &&
		!isEmptyStreamingMessage
	) {
		return null;
	}

	// 是否为 assistant 消息且不是空的 streaming 消息
	// 使用 contentWithoutToolCalls 来判断，排除工具调用标记
	const isAssistantMessageWithContent =
		message.role === "assistant" &&
		trimmedContent &&
		!isEmptyStreamingMessage;

	// 处理消息菜单按钮点击
	const handleMessageMenuClick = (event: React.MouseEvent) => {
		event.stopPropagation();
		onMenuButtonClick(event, message.id);
	};

	// 使用 ref callback 来传递 ref
	const handleMessageBoxRef = (el: HTMLDivElement | null) => {
		onMessageBoxRef(message.id, el);
	};

	return (
		<div
			className={cn(
				"flex flex-col",
				message.role === "assistant" ? "items-start" : "items-end",
			)}
		>
			<div className="max-w-[80%] flex flex-col">
				{/* 空的 streaming 消息显示 loading 指示器 */}
				{isEmptyStreamingMessage ? (
					<div className="flex items-center gap-2 rounded-full bg-muted px-3 py-2 text-xs text-muted-foreground">
						<Loader2 className="h-4 w-4 animate-spin" />
						{typingText}
					</div>
				) : (
					<div
						ref={handleMessageBoxRef}
						role="group"
						className={cn(
							"relative rounded-2xl px-4 py-3 text-sm shadow-sm",
							message.role === "assistant"
								? "bg-muted/30 text-foreground"
								: "bg-primary/10 dark:bg-primary/20 text-foreground",
						)}
						onMouseEnter={() => {
							if (isAssistantMessageWithContent) {
								setHovered(true);
							}
						}}
						onMouseLeave={() => {
							setHovered(false);
						}}
					>
						{/* <div className="mb-1 text-[11px] uppercase tracking-wide opacity-70">
							{message.role === "assistant" ? t("assistant") : t("user")}
						</div> */}
						<div className="leading-relaxed relative">
							{/* Hover 时显示的菜单按钮 - 位于右下角 */}
							{hovered && isAssistantMessageWithContent && (
								<button
									type="button"
									onClick={handleMessageMenuClick}
									className="absolute -bottom-1 -right-1 opacity-70 hover:opacity-100 transition-opacity rounded-full p-1.5 bg-background/80 hover:bg-background shadow-sm border border-border/50"
									aria-label={tContextMenu("extractButton")}
								>
									<MoreVertical className="h-3.5 w-3.5" />
								</button>
							)}
							<MessageContent message={message} />
						</div>
					</div>
				)}
			</div>
			{/* 提取待办面板 - 显示在消息下方 */}
			{extractionState && (
				<div
					className={cn(
						"w-full",
						message.role === "assistant" ? "max-w-[80%]" : "max-w-[80%]",
					)}
				>
					<MessageTodoExtractionPanel
						todos={extractionState.todos}
						parentTodoId={extractionState.parentTodoId}
						isExtracting={extractionState.isExtracting}
						onComplete={onRemoveExtractionState}
					/>
				</div>
			)}
		</div>
	);
}
