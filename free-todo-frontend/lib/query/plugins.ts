import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { customFetcher } from "@/lib/api/fetcher";
import { queryKeys } from "@/lib/query/keys";
import type {
	InstallPluginInput,
	InstallPluginResponse,
	PluginListResponse,
	UninstallPluginInput,
	UninstallPluginResponse,
} from "@/lib/types";

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
	});
};
