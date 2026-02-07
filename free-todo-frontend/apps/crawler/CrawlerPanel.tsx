"use client";

import { Bug } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";
import { PanelHeader } from "@/components/common/layout/PanelHeader";
import { StatusBar, SearchInput, StartButton, ResultList } from "./components";
import { useCrawlerStore } from "./store";

/**
 * 爬虫面板组件 - 媒体爬虫主界面
 */
export function CrawlerPanel() {
	const t = useTranslations("page");
	const { 
		fetchDailySummary, 
		fetchCrawlerStatus,
		loadConfigFromBackend,
		startCrawler,
	} = useCrawlerStore();
	
	const hasAutoStarted = useRef(false);

	// 组件挂载时自动启动爬虫并显示热点速递
	useEffect(() => {
		const initAndAutoStart = async () => {
			// 先加载后端配置
			await loadConfigFromBackend();
			// 获取爬虫状态
			await fetchCrawlerStatus();
			
			// 获取最新状态
			const currentState = useCrawlerStore.getState();
			
			// 如果爬虫没有在运行，且有关键词，则自动启动
			if (!hasAutoStarted.current && currentState.status !== "running" && currentState.keywords.trim()) {
				hasAutoStarted.current = true;
				console.log("[Crawler] 自动启动爬虫...");
				startCrawler();
			}
			
			// 自动显示热点速递界面并加载数据和 AI 摘要
			console.log("[Crawler] 自动显示热点速递...");
			fetchDailySummary();  // 这会同时设置 showDailySummary 并加载 AI 摘要
		};
		
		initAndAutoStart();
		
		// 每 5 秒轮询一次状态
		const intervalId = setInterval(() => {
			fetchCrawlerStatus();
		}, 5000);
		
		return () => clearInterval(intervalId);
	}, [loadConfigFromBackend, fetchCrawlerStatus, startCrawler, fetchDailySummary]);

	return (
		<div className="relative flex h-full flex-col overflow-hidden bg-background">
			{/* 顶部标题栏 */}
			<PanelHeader 
				icon={Bug} 
				title={t("crawlerLabel")} 
			/>

			{/* 爬虫控制区域 - 整体可滚动 */}
			<div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
				{/* 状态栏 */}
				<div>
					<StatusBar />
				</div>

				{/* 搜索输入 */}
				<div className="mt-4">
					<SearchInput />
				</div>

				{/* 启动按钮 */}
				<div className="mt-4">
					<StartButton />
				</div>

				{/* 结果列表 */}
				<div className="mt-4">
					<ResultList />
				</div>
			</div>
		</div>
	);
}
