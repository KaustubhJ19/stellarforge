/** What the Emergency and Help buttons ask the emergency flow (Spec 4) to open. */
export type EmergencyRequest = "emergency" | "help-crewmate";

export function ActionButtons({ onEmergency }: { onEmergency: (request: EmergencyRequest) => void }) {
  return (
    <div className="actions">
      <button className="actions__emergency" onClick={() => onEmergency("emergency")}>
        Emergency
      </button>
      <button className="actions__help" onClick={() => onEmergency("help-crewmate")}>
        Help a crewmate
      </button>
    </div>
  );
}
