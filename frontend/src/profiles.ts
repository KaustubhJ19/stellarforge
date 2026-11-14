/**
 * Mission profiles by id (ReplayFile.profile, CrewRecord.missionProfile).
 * Team values until Spec 5's profiles (content/profiles/) replace this table.
 */
export interface MissionProfile {
  name: string;
  /** One-way Earth signal delay used by the team, in minutes. */
  groundDelayMin: number;
}

export const PROFILES: Record<string, MissionProfile> = {
  mars_transit: { name: "Mars transit", groundDelayMin: 28.5 },
};

/** A known profile, or the raw id with no delay. */
export function profileFor(id: string): { name: string; groundDelayMin: number | null } {
  return PROFILES[id] ?? { name: id, groundDelayMin: null };
}
