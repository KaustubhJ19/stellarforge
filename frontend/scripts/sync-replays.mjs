// Copies the data lead's shared replays (../replay/*.json, tracked on workstream-1-data-service)
// into public/replay/shared/ so the app serves them: /?replay=/replay/shared/crew-A.json
// &cabin=/replay/shared/iss-cabin-dose-RR-1.json, and recorded replays under /replay/shared/recorded/.
// The copy is git-ignored; replay/ is the source.
import { copyFileSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";

const from = new URL("../../replay/", import.meta.url);
const to = new URL("../public/replay/shared/", import.meta.url);
if (!existsSync(from)) {
  console.log("sync-replays: no ../replay folder, nothing to copy");
  process.exit(0);
}
rmSync(to, { recursive: true, force: true }); // drop copies of files renamed or removed upstream
mkdirSync(to, { recursive: true });
let count = 0;
// replay/*.json, and Spec 3's recorded replays in replay/recorded/*.json.
for (const sub of ["", "recorded/"]) {
  const src = new URL(sub, from);
  if (!existsSync(src)) continue;
  const dest = new URL(sub, to);
  mkdirSync(dest, { recursive: true });
  for (const f of readdirSync(src).filter((n) => n.endsWith(".json"))) {
    copyFileSync(new URL(f, src), new URL(f, dest));
    count++;
  }
}
console.log(`sync-replays: ${count} files -> public/replay/shared/`);
