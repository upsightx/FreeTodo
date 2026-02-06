const fs = require("node:fs");
const path = require("node:path");
const { execSync } = require("node:child_process");

const nodeExecName = process.platform === "win32" ? "node.exe" : "node";

function parseArgs() {
	const args = process.argv.slice(2);
	const result = {};
	for (let i = 0; i < args.length; i += 1) {
		const key = args[i];
		const value = args[i + 1];
		if (key?.startsWith("--") && value && !value.startsWith("--")) {
			result[key.slice(2)] = value;
			i += 0;
		}
	}
	return result;
}

function copyDir(src, dest) {
	if (!fs.existsSync(src)) {
		console.warn(`Source not found, skipping: ${src}`);
		return;
	}
	fs.mkdirSync(dest, { recursive: true });
	fs.cpSync(src, dest, { recursive: true, force: true });
	console.log(`Copied ${src} -> ${dest}`);
}

function copyFile(src, dest) {
	if (!fs.existsSync(src)) {
		console.warn(`Source not found, skipping: ${src}`);
		return;
	}
	fs.mkdirSync(path.dirname(dest), { recursive: true });
	fs.copyFileSync(src, dest);
	console.log(`Copied ${src} -> ${dest}`);
}

function resolveNodeBinary() {
	const bundledPath = path.join(
		rootDir,
		"src-tauri",
		"resources",
		"node",
		nodeExecName,
	);
	if (fs.existsSync(bundledPath)) {
		return bundledPath;
	}

	const envPath = process.env.FREETODO_NODE_PATH;
	if (envPath) {
		const resolved = path.resolve(envPath);
		if (fs.existsSync(resolved)) {
			if (fs.statSync(resolved).isDirectory()) {
				const candidate = path.join(resolved, nodeExecName);
				if (fs.existsSync(candidate)) {
					return candidate;
				}
			} else {
				return resolved;
			}
		}
	}

	if (process.execPath && fs.existsSync(process.execPath)) {
		return process.execPath;
	}

	const command = process.platform === "win32" ? "where node" : "which node";
	try {
		const output = execSync(command, { stdio: ["ignore", "pipe", "ignore"] })
			.toString()
			.trim();
		const first = output.split(/\r?\n/)[0];
		if (first && fs.existsSync(first)) {
			return first;
		}
	} catch {
		return null;
	}

	return null;
}

function copyNodeBinary(destRoot) {
	const nodePath = resolveNodeBinary();
	if (!nodePath) {
		console.warn("Node.js binary not found. Skipping embedded Node.");
		return;
	}
	const destPath = path.join(destRoot, "node", nodeExecName);
	copyFile(nodePath, destPath);
}

function findLatestReleaseDir(targetRoot) {
	if (!fs.existsSync(targetRoot)) {
		return null;
	}

	const entries = fs.readdirSync(targetRoot, { withFileTypes: true });
	const candidates = [];

	for (const entry of entries) {
		if (!entry.isDirectory()) {
			continue;
		}
		const releaseDir = path.join(targetRoot, entry.name, "release");
		if (fs.existsSync(releaseDir)) {
			const stat = fs.statSync(releaseDir);
			candidates.push({ dir: releaseDir, mtimeMs: stat.mtimeMs });
		}
	}

	candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
	return candidates[0]?.dir ?? null;
}

const args = parseArgs();
const rootDir = path.resolve(__dirname, "..");
const tauriTargetDir = path.join(rootDir, "src-tauri", "target");

let releaseDir = null;
if (args.target) {
	releaseDir = path.join(tauriTargetDir, args.target, "release");
} else {
	const defaultRelease = path.join(tauriTargetDir, "release");
	if (fs.existsSync(defaultRelease)) {
		releaseDir = defaultRelease;
	} else {
		releaseDir = findLatestReleaseDir(tauriTargetDir);
	}
}

if (!releaseDir || !fs.existsSync(releaseDir)) {
	console.error("Release directory not found. Did tauri build finish?");
	process.exit(1);
}

const resourcesDir = path.join(releaseDir, "resources");
fs.mkdirSync(resourcesDir, { recursive: true });

const standaloneSrc = path.join(rootDir, ".next", "standalone");
const standaloneDest = path.join(resourcesDir, "standalone");
copyDir(standaloneSrc, standaloneDest);

const backendSrc = path.join(rootDir, "..", "dist-backend");
const backendDest = path.join(resourcesDir, "dist-backend");
copyDir(backendSrc, backendDest);

copyNodeBinary(resourcesDir);
