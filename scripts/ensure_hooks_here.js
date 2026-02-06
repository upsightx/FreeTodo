#!/usr/bin/env node
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

function runGit(args, cwd) {
	return execFileSync("git", args, {
		cwd,
		stdio: ["ignore", "pipe", "pipe"],
		encoding: "utf8",
	}).trim();
}

function safeChmod(filePath, mode) {
	try {
		fs.chmodSync(filePath, mode);
	} catch {
		// No-op: chmod is best effort (e.g., on Windows).
	}
}

function main() {
	let repoRoot = "";
	try {
		repoRoot = runGit(["rev-parse", "--show-toplevel"], process.cwd());
	} catch {
		return;
	}

	const hooksDir = path.join(repoRoot, ".githooks");
	if (!fs.existsSync(hooksDir)) {
		return;
	}

	let currentHooks = "";
	try {
		currentHooks = runGit(["config", "--get", "core.hooksPath"], repoRoot);
	} catch {
		currentHooks = "";
	}

	if (currentHooks !== ".githooks") {
		try {
			execFileSync("git", ["-C", repoRoot, "config", "core.hooksPath", ".githooks"], {
				stdio: "ignore",
			});
		} catch {
			return;
		}
	}

	if (os.platform() !== "win32") {
		for (const hook of ["pre-commit", "post-checkout"]) {
			const hookPath = path.join(hooksDir, hook);
			if (fs.existsSync(hookPath)) {
				safeChmod(hookPath, 0o755);
			}
		}
	}
}

main();
