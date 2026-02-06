"use client";

import type { ChatMessage, ToolCallStatus, ToolCallStep } from "@/apps/chat/types";
import { cn } from "@/lib/utils";
import { ToolCallSteps } from "./ToolCallSteps";
import { extractToolCalls, removeToolEvents } from "./utils/messageContentUtils";

type ToolCallBlockProps = {
	message: ChatMessage;
	isStreaming: boolean;
	isLastMessage: boolean;
	className?: string;
};

const parseLegacyToolArgs = (
	params?: string,
): Record<string, string> | undefined => {
	if (!params) return undefined;

	const result: Record<string, string> = {};
	const entries = params
		.split(",")
		.map((entry) => entry.trim())
		.filter(Boolean);

	for (const entry of entries) {
		const separatorIndex = entry.indexOf(":");
		if (separatorIndex === -1) continue;
		const key = entry.slice(0, separatorIndex).trim();
		const value = entry.slice(separatorIndex + 1).trim();
		if (key) {
			result[key] = value;
		}
	}

	return Object.keys(result).length > 0 ? result : undefined;
};

const buildLegacySteps = (
	messageId: string,
	toolCalls: ReturnType<typeof extractToolCalls>,
	status: ToolCallStatus,
): ToolCallStep[] =>
	toolCalls.map((toolCall, index) => ({
		id: `${messageId}-legacy-${index}`,
		toolName: toolCall.name,
		toolArgs: parseLegacyToolArgs(toolCall.params),
		status,
		startTime: 0,
		endTime: status === "completed" ? 0 : undefined,
	}));

export function ToolCallBlock({
	message,
	isStreaming,
	isLastMessage,
	className,
}: ToolCallBlockProps) {
	if (message.role !== "assistant") {
		return null;
	}

	const toolCallSteps = message.toolCallSteps || [];
	if (toolCallSteps.length > 0) {
		return (
			<div className={cn("flex w-full justify-start", className)}>
				<div className="max-w-[80%]">
					<ToolCallSteps steps={toolCallSteps} className="mb-0" />
				</div>
			</div>
		);
	}

	const sanitizedContent = message.content
		? removeToolEvents(message.content)
		: "";
	const legacyToolCalls = sanitizedContent
		? extractToolCalls(sanitizedContent)
		: [];
	if (legacyToolCalls.length === 0) {
		return null;
	}

	const status: ToolCallStatus =
		isStreaming && isLastMessage ? "running" : "completed";
	const legacySteps = buildLegacySteps(message.id, legacyToolCalls, status);

	return (
		<div className={cn("flex w-full justify-start", className)}>
			<div className="max-w-[80%]">
				<ToolCallSteps steps={legacySteps} className="mb-0" />
			</div>
		</div>
	);
}
