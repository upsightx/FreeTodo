/**
 * Unified frontend types (camelCase)
 * These types match the auto-transformed API response structure from customFetcher.
 * The fetcher automatically converts snake_case (API) -> camelCase (frontend).
 */

// ============================================================================
// Todo Types
// ============================================================================

export type TodoStatus = "active" | "completed" | "canceled" | "draft";
export type TodoPriority = "high" | "medium" | "low" | "none";

export interface TodoAttachment {
	id: number;
	fileName: string;
	filePath: string;
	fileSize?: number;
	mimeType?: string;
	source?: "user" | "ai";
}

export interface Todo {
	id: number;
	name: string;
	summary?: string;
	description?: string;
	userNotes?: string;
	parentTodoId?: number | null;
	itemType?: string;
	location?: string;
	categories?: string | null;
	classification?: string;
	deadline?: string;
	startTime?: string;
	endTime?: string;
	dtstart?: string;
	dtend?: string;
	due?: string;
	duration?: string;
	timeZone?: string;
	tzid?: string;
	isAllDay?: boolean;
	dtstamp?: string;
	created?: string;
	lastModified?: string;
	sequence?: number;
	rdate?: string;
	exdate?: string;
	recurrenceId?: string;
	relatedToUid?: string;
	relatedToReltype?: string;
	icalStatus?: string;
	reminderOffsets?: number[] | null;
	rrule?: string | null;
	status: TodoStatus;
	priority: TodoPriority;
	completedAt?: string;
	percentComplete?: number;
	order?: number;
	tags?: string[];
	attachments?: TodoAttachment[];
	relatedActivities?: number[];
	createdAt: string;
	updatedAt: string;
}

export interface CreateTodoInput {
	name: string;
	summary?: string;
	description?: string;
	userNotes?: string;
	parentTodoId?: number | null;
	itemType?: string;
	location?: string;
	categories?: string | null;
	classification?: string;
	deadline?: string;
	startTime?: string;
	endTime?: string;
	dtstart?: string;
	dtend?: string;
	due?: string;
	duration?: string;
	timeZone?: string;
	tzid?: string;
	isAllDay?: boolean;
	dtstamp?: string;
	created?: string;
	lastModified?: string;
	sequence?: number;
	rdate?: string;
	exdate?: string;
	recurrenceId?: string;
	relatedToUid?: string;
	relatedToReltype?: string;
	icalStatus?: string;
	reminderOffsets?: number[] | null;
	rrule?: string | null;
	status?: TodoStatus;
	priority?: TodoPriority;
	completedAt?: string;
	percentComplete?: number;
	order?: number;
	tags?: string[];
	relatedActivities?: number[];
}

export interface UpdateTodoInput {
	name?: string;
	summary?: string;
	description?: string;
	userNotes?: string;
	status?: TodoStatus;
	priority?: TodoPriority;
	itemType?: string;
	location?: string;
	categories?: string;
	classification?: string;
	deadline?: string | null;
	startTime?: string | null;
	endTime?: string | null;
	dtstart?: string | null;
	dtend?: string | null;
	due?: string | null;
	duration?: string | null;
	timeZone?: string | null;
	tzid?: string | null;
	isAllDay?: boolean | null;
	dtstamp?: string | null;
	created?: string | null;
	lastModified?: string | null;
	sequence?: number | null;
	rdate?: string | null;
	exdate?: string | null;
	recurrenceId?: string | null;
	relatedToUid?: string | null;
	relatedToReltype?: string | null;
	icalStatus?: string | null;
	reminderOffsets?: number[] | null;
	rrule?: string | null;
	completedAt?: string | null;
	percentComplete?: number | null;
	order?: number;
	tags?: string[];
	parentTodoId?: number | null;
	relatedActivities?: number[];
}

// ============================================================================
// Screenshot & Event Types
// ============================================================================

export interface Screenshot {
	id: number;
	filePath: string;
	appName: string;
	windowTitle: string;
	createdAt: string;
	textContent?: string;
	width: number;
	height: number;
	ocrResult?: {
		textContent: string;
	};
}

export interface Event {
	id: number;
	appName: string;
	windowTitle: string;
	startTime: string;
	endTime?: string;
	screenshotCount: number;
	firstScreenshotId?: number;
	screenshots?: Screenshot[];
	aiTitle?: string;
	aiSummary?: string;
}

// ============================================================================
// Activity Types
// ============================================================================

export interface Activity {
	id: number;
	startTime: string;
	endTime: string;
	aiTitle?: string;
	aiSummary?: string;
	eventCount: number;
	createdAt?: string;
	updatedAt?: string;
}

export interface ActivityWithEvents extends Activity {
	eventIds?: number[];
	events?: Event[];
}

// ============================================================================
// Utility Types for API List Responses (auto-transformed)
// ============================================================================

export interface TodoListResponse {
	total: number;
	todos: Todo[];
}

export interface ActivityListResponse {
	total: number;
	activities: Activity[];
}

export interface EventListResponse {
	total: number;
	events: Event[];
}

export interface ActivityEventsResponse {
	eventIds: number[];
}

// ============================================================================
// Automation Task Types
// ============================================================================

export type AutomationScheduleType = "interval" | "cron" | "once";

export interface AutomationSchedule {
	type: AutomationScheduleType;
	intervalSeconds?: number;
	cron?: string;
	runAt?: string;
	timezone?: string;
}

export interface AutomationAction {
	type: string;
	payload: Record<string, unknown>;
}

export interface AutomationTask {
	id: number;
	name: string;
	description?: string;
	enabled: boolean;
	schedule: AutomationSchedule;
	action: AutomationAction;
	lastRunAt?: string;
	lastStatus?: string;
	lastError?: string;
	lastOutput?: string;
	createdAt: string;
	updatedAt: string;
}

export interface AutomationTaskListResponse {
	total: number;
	tasks: AutomationTask[];
}

export interface AutomationTaskCreateInput {
	name: string;
	description?: string;
	enabled?: boolean;
	schedule: AutomationSchedule;
	action: AutomationAction;
}

export interface AutomationTaskUpdateInput {
	name?: string;
	description?: string;
	enabled?: boolean;
	schedule?: AutomationSchedule;
	action?: AutomationAction;
}

// ============================================================================
// Plugin Center Types
// ============================================================================

export type BackendPluginKind = "backend";

export type BackendPluginStatus =
	| "discovered"
	| "enabled"
	| "running"
	| "disabled"
	| "unavailable"
	| "installed"
	| string;

export interface BackendPluginState {
	id: string;
	name: string;
	version: string;
	kind: BackendPluginKind;
	source: string;
	enabled: boolean;
	installed: boolean;
	available: boolean;
	status: BackendPluginStatus;
	missingDeps: string[];
}

export interface PluginListResponse {
	plugins: BackendPluginState[];
	installedThirdParty: string[];
}

export interface InstallPluginInput {
	pluginId: string;
	archivePath: string;
	expectedSha256?: string;
	force?: boolean;
}

export interface InstallPluginResponse {
	pluginId: string;
	success: boolean;
	installDir: string;
	checksum?: string;
	message: string;
	manifest?: Record<string, unknown> | null;
}

export interface UninstallPluginInput {
	pluginId: string;
}

export interface UninstallPluginResponse {
	pluginId: string;
	success: boolean;
	installDir: string;
	message: string;
}

export interface PluginLifecycleEvent {
	eventId: string;
	pluginId: string;
	action: "install" | "uninstall" | string;
	stage: string;
	status: "running" | "success" | "failed" | string;
	message: string;
	progress?: number | null;
	timestamp: string;
	details: Record<string, unknown>;
}
