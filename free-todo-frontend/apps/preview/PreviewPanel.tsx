"use client";

import {
	Code2,
	ExternalLink,
	Eye,
	FileCode2,
	FileImage,
	FileText,
	FolderOpen,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import {
	PanelActionButton,
	PanelHeader,
} from "@/components/common/layout/PanelHeader";
import { cn } from "@/lib/utils";

type PreviewMode = "code" | "view";
type PreviewFileKind = "markdown" | "html" | "pdf" | "image";
type PreviewStatus = "live" | "rendering" | "ready";

type PreviewFile = {
	id: string;
	name: string;
	path: string;
	kind: PreviewFileKind;
	size: string;
	updatedAt: string;
	status: PreviewStatus;
};

const PREVIEW_FILES: [PreviewFile, ...PreviewFile[]] = [
	{
		id: "md-spec",
		name: "Preview Dock Spec.md",
		path: "workspace/specs/preview-dock.md",
		kind: "markdown",
		size: "18.4 KB",
		updatedAt: "2m ago",
		status: "live",
	},
	{
		id: "html-sample",
		name: "viewer-frame.html",
		path: "workspace/sandbox/viewer-frame.html",
		kind: "html",
		size: "9.8 KB",
		updatedAt: "just now",
		status: "rendering",
	},
	{
		id: "pdf-report",
		name: "Research Snapshot.pdf",
		path: "workspace/reports/2024-q3-snapshot.pdf",
		kind: "pdf",
		size: "2.4 MB",
		updatedAt: "1h ago",
		status: "ready",
	},
];

const FILE_KIND_META: Record<
	PreviewFileKind,
	{ labelKey: string; Icon: typeof FileText; badgeClass: string }
> = {
	markdown: {
		labelKey: "types.markdown",
		Icon: FileText,
		badgeClass:
			"border-emerald-200/70 bg-emerald-50 text-emerald-700 dark:border-emerald-400/40 dark:bg-emerald-500/10 dark:text-emerald-200",
	},
	html: {
		labelKey: "types.html",
		Icon: FileCode2,
		badgeClass:
			"border-sky-200/70 bg-sky-50 text-sky-700 dark:border-sky-400/40 dark:bg-sky-500/10 dark:text-sky-200",
	},
	pdf: {
		labelKey: "types.pdf",
		Icon: FileText,
		badgeClass:
			"border-amber-200/70 bg-amber-50 text-amber-700 dark:border-amber-400/40 dark:bg-amber-500/10 dark:text-amber-200",
	},
	image: {
		labelKey: "types.image",
		Icon: FileImage,
		badgeClass:
			"border-purple-200/70 bg-purple-50 text-purple-700 dark:border-purple-400/40 dark:bg-purple-500/10 dark:text-purple-200",
	},
};

const STATUS_META: Record<
	PreviewStatus,
	{ labelKey: string; dotClass: string; textClass: string }
> = {
	live: {
		labelKey: "status.live",
		dotClass: "bg-emerald-500",
		textClass: "text-emerald-700 dark:text-emerald-200",
	},
	rendering: {
		labelKey: "status.rendering",
		dotClass: "bg-sky-500 animate-pulse",
		textClass: "text-sky-700 dark:text-sky-200",
	},
	ready: {
		labelKey: "status.ready",
		dotClass: "bg-amber-500",
		textClass: "text-amber-700 dark:text-amber-200",
	},
};

const CODE_SAMPLES: Record<PreviewFileKind, string> = {
	markdown: `# Preview Dock

Design a universal preview panel for local files.

## Modes
- Code: raw source
- View: rendered output

## Requirements
1. Single active file (no multi preview)
2. External open support
3. Auto refresh on save`,
	html: `<!doctype html>
<html>
  <head>
    <title>Preview Panel</title>
  </head>
  <body>
    <main class="stage">
      <h1>Preview Dock</h1>
      <p>Full HTML render with scripts enabled.</p>
    </main>
  </body>
</html>`,
	pdf: "",
	image: "",
};

export function PreviewPanel() {
	const tPage = useTranslations("page");
	const t = useTranslations("previewPanel");

	const [activeFileId, setActiveFileId] = useState(PREVIEW_FILES[0].id);
	const [mode, setMode] = useState<PreviewMode>("view");

	const activeFile = useMemo(
		() => PREVIEW_FILES.find((file) => file.id === activeFileId) ?? PREVIEW_FILES[0],
		[activeFileId],
	);
	const supportsCode = activeFile.kind === "markdown" || activeFile.kind === "html";

	useEffect(() => {
		if (!supportsCode && mode === "code") {
			setMode("view");
		}
	}, [supportsCode, mode]);

	const kindMeta = FILE_KIND_META[activeFile.kind];
	const statusMeta = STATUS_META[activeFile.status];
	const StatusIcon = kindMeta.Icon;

	return (
		<div className="flex h-full flex-col bg-background">
			<PanelHeader
				icon={Eye}
				title={tPage("previewLabel")}
				actions={
					<div className="flex items-center gap-1">
						<PanelActionButton
							icon={ExternalLink}
							aria-label={t("openExternal")}
						/>
						<PanelActionButton
							icon={FolderOpen}
							aria-label={t("revealInFolder")}
						/>
					</div>
				}
			/>

			<div className="border-b bg-muted/20 px-4 py-3">
				<div className="flex flex-wrap items-start justify-between gap-3">
					<div className="flex min-w-[220px] items-center gap-3">
						<div className="rounded-lg border border-border bg-background p-2">
							<StatusIcon className="h-5 w-5 text-muted-foreground" />
						</div>
						<div>
							<div className="text-sm font-semibold text-foreground">
								{activeFile.name}
							</div>
							<div className="text-xs text-muted-foreground">
								{activeFile.path}
							</div>
						</div>
					</div>

					<div className="flex flex-wrap items-center gap-2 text-xs">
						<span
							className={cn(
								"inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium",
								kindMeta.badgeClass,
							)}
						>
							{t(kindMeta.labelKey)}
						</span>
						<span className="text-muted-foreground">{activeFile.size}</span>
						<span className="text-muted-foreground">•</span>
						<span className="text-muted-foreground">
							{t("updatedAt", { time: activeFile.updatedAt })}
						</span>
						<span className="text-muted-foreground">•</span>
						<span
							className={cn(
								"inline-flex items-center gap-1 rounded-full border border-border bg-background px-2 py-0.5 font-medium",
								statusMeta.textClass,
							)}
						>
							<span className={cn("h-2 w-2 rounded-full", statusMeta.dotClass)} />
							{t(statusMeta.labelKey)}
						</span>
					</div>
				</div>

				<div className="mt-3 flex flex-wrap items-center justify-between gap-3">
					<div className="flex items-center gap-2 text-xs text-muted-foreground">
						<span className="uppercase tracking-wide">{t("recentFiles")}</span>
						<div className="flex flex-wrap items-center gap-2">
							{PREVIEW_FILES.map((file) => {
								const isActive = file.id === activeFile.id;
								return (
									<button
										key={file.id}
										type="button"
										onClick={() => setActiveFileId(file.id)}
										className={cn(
											"inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
											isActive
												? "border-primary/40 bg-primary/10 text-primary"
												: "border-border bg-background text-muted-foreground hover:text-foreground",
										)}
									>
										{file.name}
									</button>
								);
							})}
						</div>
					</div>

					<div className="flex flex-wrap items-center gap-2">
						<div className="inline-flex rounded-lg border border-border bg-background/80 p-0.5">
							<button
								type="button"
								onClick={() => setMode("code")}
								disabled={!supportsCode}
								className={cn(
									"inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-semibold transition-colors",
									mode === "code"
										? "bg-foreground text-background"
										: "text-muted-foreground",
									!supportsCode && "cursor-not-allowed opacity-40",
								)}
							>
								<Code2 className="h-3.5 w-3.5" />
								{t("modeCode")}
							</button>
							<button
								type="button"
								onClick={() => setMode("view")}
								className={cn(
									"inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-semibold transition-colors",
									mode === "view"
										? "bg-foreground text-background"
										: "text-muted-foreground",
								)}
							>
								<Eye className="h-3.5 w-3.5" />
								{t("modeView")}
							</button>
						</div>
						{!supportsCode && (
							<span className="text-xs font-medium text-muted-foreground">
								{t("viewOnly")}
							</span>
						)}
					</div>
				</div>
			</div>

			<div className="flex-1 overflow-hidden">
				<div className="h-full overflow-y-auto bg-muted/10 px-6 py-6">
					{mode === "code" && supportsCode ? (
						<div className="rounded-xl border border-border bg-background p-4 shadow-sm">
							<div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
								<Code2 className="h-3.5 w-3.5" />
								{t("codeModeTitle")}
							</div>
							<pre className="max-h-[520px] overflow-auto rounded-lg bg-muted/40 p-4 text-xs text-foreground">
								<code className="font-mono">{CODE_SAMPLES[activeFile.kind]}</code>
							</pre>
						</div>
					) : (
						<div className="space-y-6">
							{activeFile.kind === "markdown" && (
								<div className="rounded-2xl border border-border bg-background p-6 shadow-sm">
									<div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
										{t("renderedMarkdown")}
									</div>
									<h3 className="mt-2 text-2xl font-semibold text-foreground">
										Preview Dock
									</h3>
									<p className="mt-2 text-sm text-muted-foreground">
										{t("markdownIntro")}
									</p>
									<div className="mt-4 grid gap-3 sm:grid-cols-2">
										<div className="rounded-lg border border-border bg-muted/20 p-3">
											<div className="text-xs font-semibold text-muted-foreground">
												{t("cardModeTitle")}
											</div>
											<ul className="mt-2 space-y-1 text-sm text-foreground">
												<li>{t("cardModeItem1")}</li>
												<li>{t("cardModeItem2")}</li>
												<li>{t("cardModeItem3")}</li>
											</ul>
										</div>
										<div className="rounded-lg border border-border bg-muted/20 p-3">
											<div className="text-xs font-semibold text-muted-foreground">
												{t("cardViewTitle")}
											</div>
											<ul className="mt-2 space-y-1 text-sm text-foreground">
												<li>{t("cardViewItem1")}</li>
												<li>{t("cardViewItem2")}</li>
												<li>{t("cardViewItem3")}</li>
											</ul>
										</div>
									</div>
									<div className="mt-4 rounded-lg border border-border bg-muted/30 p-3 text-xs text-muted-foreground">
										<span className="font-semibold text-foreground">
											{t("calloutLabel")}
										</span>{" "}
										{t("calloutText")}
									</div>
								</div>
							)}

							{activeFile.kind === "html" && (
								<div className="rounded-2xl border border-border bg-background p-5 shadow-sm">
									<div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
										{t("renderedHtml")}
										<span className="rounded-full border border-border bg-muted/30 px-2 py-0.5 text-[10px]">
											{t("fullRender")}
										</span>
									</div>
									<div className="overflow-hidden rounded-xl border border-border bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-slate-100">
										<div className="flex items-center justify-between border-b border-slate-200/70 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
											<span>{t("htmlFrameTitle")}</span>
											<span>{t("htmlFrameBadge")}</span>
										</div>
										<div className="px-6 py-5">
											<h3 className="text-2xl font-semibold">
												Preview Dock
											</h3>
											<p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
												{t("htmlIntro")}
											</p>
											<div className="mt-4 grid gap-3 sm:grid-cols-3">
												{[
													t("htmlPillScan"),
													t("htmlPillRender"),
													t("htmlPillInspect"),
												].map((label) => (
													<div
														key={label}
														className="rounded-lg border border-slate-200/70 bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400"
													>
														{label}
													</div>
												))}
											</div>
										</div>
									</div>
								</div>
							)}

							{activeFile.kind === "pdf" && (
								<div className="rounded-2xl border border-border bg-background p-5 shadow-sm">
									<div className="mb-4 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-muted-foreground">
										<span>{t("pdfPreviewTitle")}</span>
										<span>{t("pdfPages", { count: 12 })}</span>
									</div>
									<div className="grid gap-4 sm:grid-cols-2">
										{[1, 2, 3, 4].map((page) => (
											<div
												key={page}
												className="flex flex-col overflow-hidden rounded-lg border border-border bg-muted/30"
											>
												<div className="flex-1 bg-linear-to-br from-muted/10 via-muted/40 to-muted/10 p-4">
													<div className="h-full rounded-md border border-dashed border-muted-foreground/30 bg-background/60" />
												</div>
												<div className="border-t border-border bg-background px-3 py-2 text-xs text-muted-foreground">
													{t("pdfPageLabel", { page })}
												</div>
											</div>
										))}
									</div>
									<div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
										<span className="rounded-full border border-border bg-muted/20 px-2 py-1">
											{t("pdfSearchHint")}
										</span>
										<span className="rounded-full border border-border bg-muted/20 px-2 py-1">
											{t("pdfZoomHint")}
										</span>
									</div>
								</div>
							)}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
