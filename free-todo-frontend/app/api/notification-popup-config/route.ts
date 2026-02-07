import fs from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

/**
 * 通知弹窗配置文件路径
 * 供独立 Electron 弹窗进程读取
 */
const CONFIG_PATH = path.join(process.cwd(), ".notification-popup.json");

/**
 * POST: 保存通知弹窗配置
 */
export async function POST(request: Request) {
	try {
		const body = (await request.json()) as {
			enabled?: unknown;
			intervalSeconds?: unknown;
		};

		const config = {
			enabled: typeof body.enabled === "boolean" ? body.enabled : true,
			intervalSeconds:
				typeof body.intervalSeconds === "number" &&
				body.intervalSeconds >= 3 &&
				body.intervalSeconds <= 3600
					? body.intervalSeconds
					: 10,
		};

		fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), "utf-8");

		return NextResponse.json({ ok: true });
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		return NextResponse.json({ ok: false, error: message }, { status: 500 });
	}
}

/**
 * GET: 读取通知弹窗配置
 */
export async function GET() {
	try {
		const data = fs.readFileSync(CONFIG_PATH, "utf-8");
		return NextResponse.json(JSON.parse(data) as Record<string, unknown>);
	} catch {
		return NextResponse.json({ enabled: true, intervalSeconds: 10 });
	}
}
