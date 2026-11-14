// Copies the data lead's shared replays (../replay/*.json, tracked on workstream-1-data-service)
// into public/replay/shared/ so the app serves them: /?replay=/replay/shared/crew-A.json
// &cabin=/replay/shared/iss-cabin-dose-RR-1.json. The copy is git-ignored; replay/ is the source.
import { copyFileSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";

const from = new URL("../../replay/", import.meta.url);
const to = new URL("../public/replay/shared/", import.meta.url);
if (!existsSync(from)) {
  console.log("sync-replays: no ../replay folder, nothing to copy");
  process.exit(0);
}
rmSync(to, { recursive: true, force: true }); // drop copies of files renamed or removed upstream
mkdirSync(to, { recursive: true });
const files = readdirSync(from).filter((f) => f.endsWith(".json"));
for (const f of files) copyFileSync(new URL(f, from), new URL(f, to));
console.log(`sync-replays: ${files.length} files -> public/replay/shared/`);
