import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { customFetcher } from "@/lib/api/fetcher";
import { queryKeys } from "@/lib/query/keys";
import type {
	InstallPluginInput,
	InstallPluginResponse,
	PluginListResponse,
	PluginTaskListResponse,
	TogglePluginInput,
	TogglePluginResponse,
	UninstallPluginInput,
	UninstallPluginResponse,
} from "@/lib/types";

const extractApiErrorMessage = (error: unknown): string => {
	if (!(error instanceof Error)) {
		return String(error);
	}
	const text = error.message;
	const marker = "API Error:";
	if (!text.startsWith(marker)) {
		return text;
	}
	const firstBrace = text.indexOf("{");
	if (firstBrace < 0) {
		return text;
	}
	try {
		const payload = JSON.parse(text.slice(firstBrace)) as {
			detail?: { code?: string; message?: string };
		};
		const detail = payload.detail;
		if (detail?.code && detail?.message) {
			return `${detail.code}: ${detail.message}`;
		}
		if (detail?.message) {
			return detail.message;
		}
		return text;
	} catch {
		return text;
	}
};

export const usePlugins = () =>
	useQuery({
		queryKey: queryKeys.plugins.list(),
		queryFn: () => customFetcher<PluginListResponse>("/api/plugins"),
	});

export const useInstallPlugin = () => {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (input: InstallPluginInput) =>
			customFetcher<InstallPluginResponse>("/api/plugins/install", {
				method: "POST",
				data: input,
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: queryKeys.plugins.all });
		},
		onError: (error) => {
			throw new Error(extractApiErrorMessage(error));
		},
	});
};

export const useUninstallPlugin = () => {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (input: UninstallPluginInput) =>
			customFetcher<UninstallPluginResponse>("/api/plugins/uninstall", {
				method: "POST",
				data: input,
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: queryKeys.plugins.all });
		},
		onError: (error) => {
			throw new Error(extractApiErrorMessage(error));
		},
	});
};

export const useTogglePlugin = () => {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (input: TogglePluginInput) =>
			customFetcher<TogglePluginResponse>("/api/plugins/toggle", {
				method: "POST",
				data: input,
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: queryKeys.plugins.all });
		},
		onError: (error) => {
			throw new Error(extractApiErrorMessage(error));
		},
	});
};

export const usePluginTasks = (pluginId?: string) =>
	useQuery({
		queryKey: queryKeys.plugins.tasks(pluginId),
		queryFn: () =>
			customFetcher<PluginTaskListResponse>("/api/plugins/tasks", {
				params: { pluginId, limit: 50 },
			}),
	});
