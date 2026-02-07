"use client";

import { useTranslations } from "next-intl";
import { useUiStore } from "@/lib/store/ui-store";
import { toastSuccess } from "@/lib/toast";
import { SettingsSection } from "./SettingsSection";
import { ToggleSwitch } from "./ToggleSwitch";

interface NotificationPopupSectionProps {
	loading?: boolean;
}

/**
 * 通知弹窗设置区块组件
 * 控制系统级通知弹窗的开关和弹出频率
 */
export function NotificationPopupSection({
	loading = false,
}: NotificationPopupSectionProps) {
	const tSettings = useTranslations("page.settings");

	const enabled = useUiStore((state) => state.notificationPopupEnabled);
	const intervalSeconds = useUiStore(
		(state) => state.notificationPopupIntervalSeconds,
	);
	const setEnabled = useUiStore(
		(state) => state.setNotificationPopupEnabled,
	);
	const setIntervalSeconds = useUiStore(
		(state) => state.setNotificationPopupIntervalSeconds,
	);

	const handleToggle = (newEnabled: boolean) => {
		setEnabled(newEnabled);
		toastSuccess(
			newEnabled
				? tSettings("notificationPopupEnabled")
				: tSettings("notificationPopupDisabled"),
		);
	};

	const handleIntervalChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const value = Number.parseInt(e.target.value, 10);
		if (!Number.isNaN(value)) {
			setIntervalSeconds(value);
		}
	};

	return (
		<SettingsSection
			title={tSettings("notificationPopupTitle")}
			description={tSettings("notificationPopupDescription")}
			searchKeywords={[
				"notification",
				"popup",
				"通知",
				"弹窗",
				"频率",
				"interval",
				tSettings("notificationPopupTitle"),
			]}
		>
			<div className="space-y-4">
				{/* 开关 */}
				<div className="flex items-center justify-between">
					<label
						htmlFor="notification-popup-toggle"
						className="text-sm font-medium text-foreground cursor-pointer"
					>
						{tSettings("notificationPopupToggleLabel")}
					</label>
					<ToggleSwitch
						id="notification-popup-toggle"
						enabled={enabled}
						disabled={loading}
						onToggle={handleToggle}
						ariaLabel={tSettings("notificationPopupToggleLabel")}
					/>
				</div>

				{/* 频率设置 */}
				<div className="flex items-center justify-between">
					<label
						htmlFor="notification-popup-interval"
						className="text-sm font-medium text-foreground"
					>
						{tSettings("notificationPopupIntervalLabel")}
					</label>
					<div className="flex items-center gap-2">
						<input
							id="notification-popup-interval"
							type="number"
							min={3}
							max={3600}
							step={1}
							value={intervalSeconds}
							onChange={handleIntervalChange}
							disabled={loading || !enabled}
							className="w-20 rounded-md border border-border bg-background px-3 py-1.5 text-right text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
						/>
						<span className="text-sm text-muted-foreground">
							{tSettings("notificationPopupIntervalUnit")}
						</span>
					</div>
				</div>

				{/* 提示 */}
				<p className="text-xs text-muted-foreground">
					{tSettings("notificationPopupHint")}
				</p>
			</div>
		</SettingsSection>
	);
}
