import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { useAuth, API } from "@/contexts/AuthContext";
import {
  LayoutDashboard, Users, UserCheck, Calendar,
  FileText, X, Heart, ScrollText, Wallet, CalendarDays, Shield, Receipt, BookHeart, Star
} from "lucide-react";

const ADMIN_MENU = [
  { to: "/admin", icon: LayoutDashboard, label: "Panoramica", exact: true },
  { to: "/admin/calendario", icon: CalendarDays, label: "Calendario Terapisti" },
  { to: "/admin/terapisti", icon: UserCheck, label: "Terapisti" },
  { to: "/admin/pazienti", icon: Users, label: "Pazienti" },
  { to: "/admin/appuntamenti", icon: Calendar, label: "Appuntamenti" },
  { to: "/admin/pagamenti", icon: Wallet, label: "Pagamenti" },
  { to: "/admin/fatture", icon: Receipt, label: "Fatture" },
  { to: "/admin/recensioni", icon: Star, label: "Recensioni", badgeKey: "reviews" },
  { to: "/admin/ambassadors", icon: Heart, label: "Ambassador" },
  { to: "/admin/blog", icon: FileText, label: "Blog" },
  { to: "/admin/contratti", icon: ScrollText, label: "Documenti Legali" },
  { to: "/admin/registro-trattamenti", icon: Shield, label: "Registro Trattamenti" },
];

const THERAPIST_MENU = [
  { to: "/terapeuta", icon: LayoutDashboard, label: "Dashboard", exact: true },
  { to: "/terapeuta/calendario", icon: CalendarDays, label: "Calendario Disponibilità" },
  { to: "/terapeuta/profilo", icon: UserCheck, label: "Il mio Profilo" },
  { to: "/terapeuta/fatture", icon: Receipt, label: "Fatture" },
  { to: "/terapeuta/blog", icon: FileText, label: "Blog" },
  { to: "/terapeuta/privacy", icon: Shield, label: "I miei dati" },
];

const PATIENT_MENU = [
  { to: "/paziente", icon: LayoutDashboard, label: "Dashboard", exact: true },
  { to: "/paziente/diario", icon: BookHeart, label: "Diario emozionale" },
  { to: "/paziente/fatture", icon: Receipt, label: "Le mie fatture" },
  { to: "/paziente/privacy", icon: Shield, label: "I miei dati" },
];

export default function Sidebar({ onClose }) {
  const { user } = useAuth();
  const location = useLocation();
  const [badges, setBadges] = useState({ reviews: 0 });

  useEffect(() => {
    if (user?.role !== "admin") return;
    let cancelled = false;
    const fetchBadges = () => {
      axios
        .get(`${API}/admin/reviews/count-pending`, { withCredentials: true })
        .then((r) => {
          if (!cancelled) setBadges((b) => ({ ...b, reviews: r.data?.count || 0 }));
        })
        .catch(() => {});
    };
    fetchBadges();
    const id = setInterval(fetchBadges, 60000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [user?.role, location.pathname]);

  const menu = user?.role === "admin" ? ADMIN_MENU :
               user?.role === "terapeuta" ? THERAPIST_MENU : PATIENT_MENU;

  const isActive = (item) => item.exact
    ? location.pathname === item.to
    : location.pathname.startsWith(item.to);

  return (
    <div className="w-64 h-full bg-[#0A0A0A] flex flex-col">
      {/* Logo */}
      <div className="p-6 flex items-center justify-between border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-[#E9D628] flex items-center justify-center">
            <Heart className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="text-white font-bold font-[Outfit] leading-none">FunzionaBene</div>
            <div className="text-[rgba(253,251,247,0.4)] text-xs mt-0.5 capitalize">{user?.role}</div>
          </div>
        </div>
        <button onClick={onClose} className="lg:hidden text-[rgba(253,251,247,0.4)] hover:text-white">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {menu.map((item) => {
          const Icon = item.icon;
          const active = isActive(item);
          return (
            <Link
              key={item.to}
              data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
              to={item.to}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all
                ${active
                  ? "bg-[#E9D628] text-[#0A0A0A]"
                  : "text-[rgba(253,251,247,0.6)] hover:text-white hover:bg-white/10"
                }
              `}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span className="flex-1">{item.label}</span>
              {item.badgeKey && badges[item.badgeKey] > 0 && (
                <span
                  data-testid={`badge-${item.badgeKey}`}
                  className={`ml-auto min-w-[20px] h-5 px-1.5 rounded-full text-[10px] font-bold flex items-center justify-center ${
                    active ? "bg-[#0A0A0A] text-[#E9D628]" : "bg-red-500 text-white"
                  }`}
                >
                  {badges[item.badgeKey]}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-full bg-[#E9D628] flex items-center justify-center text-[#0A0A0A] text-xs font-semibold">
            {`${user?.nome?.[0] || ""}${user?.cognome?.[0] || ""}`.toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="text-[rgba(253,251,247,0.9)] text-sm font-medium truncate">{user?.nome} {user?.cognome}</div>
            <div className="text-[rgba(253,251,247,0.4)] text-xs truncate">{user?.email}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
