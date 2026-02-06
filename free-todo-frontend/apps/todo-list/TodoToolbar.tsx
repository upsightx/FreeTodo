"use client";

import { ListTodo, Menu, Search, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import {
	PanelActionButton,
	PanelHeader,
	usePanelIconStyle,
} from "@/components/common/layout/PanelHeader";
import type { Todo } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { TodoFilterState } from "./components/TodoFilter";
import { TodoFilter } from "./components/TodoFilter";

interface TodoToolbarProps {
	searchQuery: string;
	onSearch: (value: string) => void;
	todos: Todo[];
	filter: TodoFilterState;
	onFilterChange: (filter: TodoFilterState) => void;
	isSidebarOpen: boolean;
	onToggleSidebar: () => void;
}

export function TodoToolbar({
	searchQuery,
	onSearch,
	todos,
	filter,
	onFilterChange,
	isSidebarOpen,
	onToggleSidebar,
}: TodoToolbarProps) {
	const t = useTranslations("page");
	const tTodoList = useTranslations("todoList");
	const [isSearchOpen, setIsSearchOpen] = useState(false);
	const searchInputRef = useRef<HTMLInputElement>(null);
	const searchContainerRef = useRef<HTMLDivElement>(null);
	const actionIconStyle = usePanelIconStyle("action");
	const headerIconStyle = usePanelIconStyle("action", {
		size: "h-4 w-4",
		strokeWidth: "stroke-[2.4]",
	});

	useEffect(() => {
		if (isSearchOpen && searchInputRef.current) {
			searchInputRef.current.focus();
		}
	}, [isSearchOpen]);

	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (
				searchContainerRef.current &&
				!searchContainerRef.current.contains(event.target as Node) &&
				!searchQuery
			) {
				setIsSearchOpen(false);
			}
		};

		if (isSearchOpen) {
			document.addEventListener("mousedown", handleClickOutside);
			return () => {
				document.removeEventListener("mousedown", handleClickOutside);
			};
		}
	}, [isSearchOpen, searchQuery]);

	const sidebarToggle = (
		<button
			type="button"
			onClick={onToggleSidebar}
			onPointerDown={(event) => event.stopPropagation()}
			aria-label={tTodoList("toggleSidebar")}
			title={tTodoList("toggleSidebar")}
			className="ml-1 flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
		>
			{isSidebarOpen ? (
				<X className={headerIconStyle} />
			) : (
				<Menu className={headerIconStyle} />
			)}
		</button>
	);

	return (
		<PanelHeader
			icon={ListTodo}
			title={t("todoListTitle")}
			titleAddon={sidebarToggle}
			actions={
				<div className="flex items-center gap-2">
					<TodoFilter
						todos={todos}
						filter={filter}
						onFilterChange={onFilterChange}
					/>
					<div ref={searchContainerRef} className="relative">
						{isSearchOpen ? (
							<div className="relative">
								<Search
									className={cn(
										"absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground",
										actionIconStyle,
									)}
								/>
								<input
									ref={searchInputRef}
									type="text"
									value={searchQuery}
									onChange={(e) => onSearch(e.target.value)}
									placeholder={tTodoList("searchPlaceholder")}
									className="h-7 w-48 rounded-md border border-primary/20 px-8 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
								/>
							</div>
						) : (
							<PanelActionButton
								variant="default"
								icon={Search}
								onClick={() => setIsSearchOpen(true)}
								iconOverrides={{ color: "text-muted-foreground" }}
								buttonOverrides={{ hoverTextColor: "hover:text-foreground" }}
								aria-label={tTodoList("searchPlaceholder")}
							/>
						)}
					</div>
				</div>
			}
		/>
	);
}
