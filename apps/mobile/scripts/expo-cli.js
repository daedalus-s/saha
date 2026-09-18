const { execFileSync, spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..", "..");

function localNodePath(dirName) {
  return process.platform === "win32"
    ? path.join(repoRoot, ".tools", dirName, "node.exe")
    : path.join(repoRoot, ".tools", dirName, "bin", "node");
}

function readVersion(execPath) {
  if (execPath === process.execPath) return process.versions.node;
  return execFileSync(execPath, ["-p", "process.versions.node"], {
    encoding: "utf8",
  }).trim();
}

function isSupported(ver) {
  const [maj, min, patch] = ver.split(".").map((n) => Number.parseInt(n, 10));
  if (maj === 20 && (min > 19 || (min === 19 && patch >= 4))) return true;
  if (maj === 22 && min >= 13) return true;
  if (maj >= 24 && min >= 3) return true;
  if (maj > 24) return true;
  return false;
}

function withoutStripTypesFlag(value) {
  if (!value) return value;
  const next = value
    .split(/\s+/)
    .filter((flag) => flag && flag !== "--no-experimental-strip-types")
    .join(" ");
  return next || undefined;
}

const candidates = [process.execPath, localNodePath("node-v20")];
const nodeBin = candidates.find((bin) => {
  try {
    return fs.existsSync(bin) && isSupported(readVersion(bin));
  } catch {
    return false;
  }
});

if (!nodeBin) {
  console.error(
    `Expo 57 needs Node 20.19.4+, 22.13+, or 24.3+ (got ${process.versions.node}).`,
  );
  process.exit(1);
}

const cli = require.resolve("expo/bin/cli");
const env = { ...process.env };
const cleaned = withoutStripTypesFlag(env.NODE_OPTIONS);
if (cleaned) env.NODE_OPTIONS = cleaned;
else delete env.NODE_OPTIONS;
env.PATH = `${path.dirname(nodeBin)}${path.delimiter}${env.PATH || ""}`;

const child = spawn(nodeBin, [cli, ...process.argv.slice(2)], {
  stdio: "inherit",
  env,
});
child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 1);
});
