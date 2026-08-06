import { NavLink } from "react-router-dom";
import { Home, BookHeart, MessageCircle, User } from "lucide-react";

const TABS = [
  { to: "/paziente",             icon: Home,          label: "Home",       exact: true },
  { to: "/paziente/diario",      icon: BookHeart,     label: "Diario" },
  { to: "/paziente/chat",        icon: MessageCircle, label: "Chat" },
  { to: "/paziente/profilo",     icon: User,          label: "Profilo" },
];

export default function BottomNav() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-lg border-t border-[#0A0A0A]/8 pb-safe"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 8px)" }}
      data-testid="paziente-bottom-nav"
    >
      <ul className="flex items-center justify-around px-2 py-2">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <li key={t.to} className="flex-1">
              <NavLink
                to={t.to}
                end={t.exact}
                data-testid={`nav-${t.label.toLowerCase()}`}
                className={({ isActive }) =>
                  `flex flex-col items-center gap-1 py-2 rounded-2xl transition-all ${
                    isActive ? "text-[#F58A1F]" : "text-[#0A0A0A]/45 hover:text-[#0A0A0A]/70"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div
                      className={`w-10 h-10 rounded-2xl flex items-center justify-center transition-all ${
                        isActive ? "bg-[#0A0A0A]" : ""
                      }`}
                    >
                      <Icon className={`w-5 h-5 ${isActive ? "text-[#F58A1F]" : ""}`} />
                    </div>
                    <span className="text-[10px] font-medium">{t.label}</span>
                  </>
                )}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
