import { Outlet } from "react-router-dom";
import BottomNav from "./BottomNav";

/**
 * Mobile-first app shell for the paziente area.
 * Yellow/champagne background matching the mockup, no marketing header.
 * Content scrolls; BottomNav fixed at bottom.
 */
export default function PazienteAppShell() {
  return (
    <div
      className="min-h-screen text-[#0A0A0A] font-sans antialiased"
      style={{
        background:
          "linear-gradient(135deg, #F4CB78 0%, #ECDC74 40%, #F0E08A 70%, #F4EAA8 100%)",
      }}
      data-testid="paziente-app-shell"
    >
      <div className="max-w-md mx-auto pb-28 min-h-screen">
        <Outlet />
      </div>
      <BottomNav />
    </div>
  );
}
