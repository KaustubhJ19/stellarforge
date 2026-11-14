import type {
  Alert,
  Baseline,
  IndicatorId,
  MissionTime,
  Reading,
  ReplayFile,
  Task,
} from "../contracts";

const DAY = 86400;

/** What the crew sees at one Mission-clock time: the replay folded up to `t`. */
export interface MissionState {
  t: MissionTime;
  missionDay: number;
  latest: Map<IndicatorId, Reading>;
  alerts: Alert[];
  baselines: Map<IndicatorId, Baseline>;
  tasks: Task[];
}

export function replayRange(replay: ReplayFile): [MissionTime, MissionTime] {
  const ts = replay.events.map((e) => e.t);
  return ts.length ? [Math.min(...ts), Math.max(...ts)] : [0, 0];
}

export function missionStateAt(replay: ReplayFile, t: MissionTime): MissionState {
  const latest = new Map<IndicatorId, Reading>();
  const baselines = new Map<IndicatorId, Baseline>();
  const tasks = new Map<string, Task>();
  const alerts: Alert[] = [];
  for (const e of replay.events) {
    if (e.t > t) continue;
    switch (e.type) {
      case "reading": {
        const prev = latest.get(e.payload.indicator);
        if (!prev || prev.t <= e.t) latest.set(e.payload.indicator, e.payload);
        break;
      }
      case "alert":
        alerts.push(e.payload);
        break;
      case "baseline":
        baselines.set(e.payload.indicator, e.payload);
        break;
      case "task":
        tasks.set(e.payload.id, e.payload);
        break;
    }
  }
  return {
    t,
    missionDay: Math.floor(t / DAY) + 1,
    latest,
    alerts,
    baselines,
    tasks: [...tasks.values()],
  };
}

/** All Readings of one Indicator, oldest first. */
export function seriesOf(replay: ReplayFile, indicator: IndicatorId): Reading[] {
  return replay.events
    .flatMap((e) => (e.type === "reading" && e.payload.indicator === indicator ? [e.payload] : []))
    .sort((a, b) => a.t - b.t);
}
