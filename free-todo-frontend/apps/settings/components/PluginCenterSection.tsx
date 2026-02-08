"use client";

import { Download, Loader2, Plug, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { useInstallPlugin, usePlugins, useUninstallPlugin } from "@/lib/query";
import { toastError, toastSuccess } from "@/lib/toast";
import type { PluginLifecycleEvent } from "@/lib/types";
import { cn } from "@/lib/utils";
import { SettingsSection } from "./SettingsSection";

interface PluginCenterSectionProps {
	loading?: boolean;
}

const statusToneClass: Record<string, string> = {
	enabled: "text-emerald-600",
	running: "text-emerald-600",
	disabled: "text-muted-foreground",
	unavailable: "text-amber-600",
	installed: "text-sky-600",
};

export function PluginCenterSection({
	loading = false,
}: PluginCenterSectionProps) {
	const t = useTranslations("pluginCenter");
	const { data, isLoading, refetch } = usePlugins();
	const installMutation = useInstallPlugin();
	const uninstallMutation = useUninstallPlugin();

	const [pluginId, setPluginId] = useState("");
	const [archivePath, setArchivePath] = useState("");
	const [expectedSha256, setExpectedSha256] = useState("");
	const [forceInstall, setForceInstall] = useState(false);
	const [events, setEvents] = useState<PluginLifecycleEvent[]>([]);

	const busy =
		loading ||
		isLoading ||
		installMutation.isPending ||
		uninstallMutation.isPending;

	const plugins = data?.plugins ?? [];

	const sortedPlugins = useMemo(
		() => [...plugins].sort((a, b) => a.id.localeCompare(b.id)),
		[plugins],
	);

	useEffect(() => {
		const source = new EventSource("/api/plugins/events");

		source.addEventListener("plugin_event", (event) => {
			try {
				const payload = JSON.parse((event as MessageEvent).data) as PluginLifecycleEvent;
				setEvents((previous) => {
					const next = [...previous, payload];
					if (next.length > 40) {
						next.splice(0, next.length - 40);
					}
					return next;
				});
				if (payload.status === "success") {
					void refetch();
				}
			} catch {
				// ignore malformed event payload
			}
		});

		source.onerror = () => {
			// browser EventSource auto-reconnect handles transient errors
		};

		return () => {
			source.close();
		};
	}, [refetch]);

	const handleInstall = async () => {
		if (!pluginId.trim()) {
			toastError(t("errors.pluginIdRequired"));
			return;
		}
		if (!archivePath.trim()) {
			toastError(t("errors.archivePathRequired"));
			return;
		}
		try {
			const result = await installMutation.mutateAsync({
				pluginId: pluginId.trim(),
				archivePath: archivePath.trim(),
				expectedSha256: expectedSha256.trim() || undefined,
				force: forceInstall,
			});
			toastSuccess(result.message || t("messages.installed"));
			setExpectedSha256("");
		} catch (error) {
			const msg = error instanceof Error ? error.message : String(error);
			toastError(t("errors.installFailed", { error: msg }));
		}
	};

	const handleUninstall = async (id: string) => {
		if (!window.confirm(t("confirmUninstall", { pluginId: id }))) {
			return;
		}
		try {
			const result = await uninstallMutation.mutateAsync({ pluginId: id });
			toastSuccess(result.message || t("messages.uninstalled"));
		} catch (error) {
			const msg = error instanceof Error ? error.message : String(error);
			toastError(t("errors.uninstallFailed", { error: msg }));
		}
	};

	const renderStatus = (status: string) => {
		const tone = statusToneClass[status] ?? "text-muted-foreground";
		const statusLabel =
			status === "discovered" ||
			status === "enabled" ||
			status === "running" ||
			status === "disabled" ||
			status === "unavailable" ||
			status === "installed"
				? t(`status.${status}`)
				: status;
		return (
			<span className={cn("text-xs font-medium", tone)}>{statusLabel}</span>
		);
	};

	return (
		<SettingsSection
			title={t("title")}
			description={t("description")}
			searchKeywords={[
				t("title"),
				t("description"),
				t("labels.pluginId"),
				t("labels.archivePath"),
			]}
		>
			<div className="space-y-4">
				<div className="rounded-lg border border-border bg-background/70 p-3">
					<p className="mb-3 text-sm font-medium text-foreground">{t("installTitle")}</p>
					<div className="grid gap-3 md:grid-cols-2">
						<div className="space-y-2">
							<label htmlFor="plugin-center-plugin-id" className="text-xs text-muted-foreground">
								{t("labels.pluginId")}
							</label>
							<input
								id="plugin-center-plugin-id"
								value={pluginId}
								onChange={(event) => setPluginId(event.target.value)}
								placeholder={t("placeholders.pluginId")}
								className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
							/>
						</div>
						<div className="space-y-2">
							<label htmlFor="plugin-center-archive-path" className="text-xs text-muted-foreground">
								{t("labels.archivePath")}
							</label>
							<input
								id="plugin-center-archive-path"
								value={archivePath}
								onChange={(event) => setArchivePath(event.target.value)}
								placeholder={t("placeholders.archivePath")}
								className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
							/>
						</div>
						<div className="space-y-2">
							<label htmlFor="plugin-center-sha256" className="text-xs text-muted-foreground">
								{t("labels.expectedSha256")}
							</label>
							<input
								id="plugin-center-sha256"
								value={expectedSha256}
								onChange={(event) => setExpectedSha256(event.target.value)}
								placeholder={t("placeholders.expectedSha256")}
								className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
							/>
						</div>
						<div className="space-y-2">
							<label htmlFor="plugin-center-force" className="text-xs text-muted-foreground">
								{t("labels.forceInstall")}
							</label>
							<label
								htmlFor="plugin-center-force"
								className="inline-flex cursor-pointer items-center gap-2 text-sm text-foreground"
							>
								<input
									id="plugin-center-force"
									type="checkbox"
									checked={forceInstall}
									onChange={(event) => setForceInstall(event.target.checked)}
									className="h-4 w-4 rounded border-border"
								/>
								<span>{t("labels.forceInstallHint")}</span>
							</label>
						</div>
					</div>
					<div className="mt-3 flex items-center gap-2">
						<button
							type="button"
							onClick={handleInstall}
							disabled={busy}
							className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
						>
							{installMutation.isPending ? (
								<Loader2 className="h-4 w-4 animate-spin" />
							) : (
								<Download className="h-4 w-4" />
							)}
							{t("actions.install")}
						</button>
						<p className="text-xs text-muted-foreground">{t("installHint")}</p>
					</div>
				</div>

			<div className="space-y-2">
				{sortedPlugins.length === 0 && !isLoading && (
					<p className="text-sm text-muted-foreground">{t("empty")}</p>
				)}
				{isLoading && (
					<p className="text-sm text-muted-foreground">{t("loading")}</p>
				)}
				{sortedPlugins.map((plugin) => (
						<div
							key={plugin.id}
							className="rounded-lg border border-border bg-background/70 px-3 py-3"
						>
							<div className="flex flex-wrap items-center justify-between gap-2">
								<div className="min-w-0">
									<p className="text-sm font-medium text-foreground">{plugin.name}</p>
									<p className="truncate text-xs text-muted-foreground">
										{plugin.id} · v{plugin.version} · {plugin.source}
									</p>
								</div>
								<div className="flex items-center gap-3">
									{renderStatus(plugin.status)}
									{plugin.source === "third_party" && (
										<button
											type="button"
											onClick={() => handleUninstall(plugin.id)}
											disabled={busy}
											className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-destructive"
										>
											<Trash2 className="h-3 w-3" />
											{t("actions.uninstall")}
										</button>
									)}
								</div>
							</div>
							<div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
								<span>{plugin.enabled ? t("labels.enabled") : t("labels.disabled")}</span>
								<span>
									{plugin.available ? t("labels.available") : t("labels.unavailable")}
								</span>
								<span>
									{plugin.installed ? t("labels.installed") : t("labels.notInstalled")}
								</span>
							</div>
							{plugin.missingDeps.length > 0 && (
								<p className="mt-2 text-xs text-amber-600">
									{t("labels.missingDeps", {
										deps: plugin.missingDeps.join(", "),
									})}
								</p>
							)}
						</div>
					))}
				</div>

				<div className="rounded-lg border border-border bg-background/70 p-3">
					<p className="mb-2 text-sm font-medium text-foreground">
						<Plug className="mr-1 inline h-4 w-4" />
						{t("eventsTitle")}
					</p>
					{events.length === 0 ? (
						<p className="text-xs text-muted-foreground">{t("eventsEmpty")}</p>
					) : (
						<div className="max-h-48 space-y-1 overflow-y-auto pr-1">
							{[...events].reverse().map((eventItem) => (
								<div
									key={eventItem.eventId}
									className="rounded border border-border/60 bg-muted/20 px-2 py-1"
								>
									<p className="text-xs text-foreground">
										[{eventItem.action}] {eventItem.pluginId} · {eventItem.stage}
									</p>
									<p className="text-[11px] text-muted-foreground">
										{eventItem.message}
										{typeof eventItem.progress === "number" ? ` (${eventItem.progress}%)` : ""}
									</p>
								</div>
							))}
						</div>
					)}
				</div>
			</div>
		</SettingsSection>
	);
}
