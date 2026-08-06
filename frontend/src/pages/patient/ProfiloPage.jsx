import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth, API } from "@/contexts/AuthContext";
import { LogOut, Receipt, Shield, ChevronRight, User } from "lucide-react";

export default function ProfiloPage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
    } finally {
      setUser?.(null);
      navigate("/login");
    }
  };

  return (
    <div className="px-5 pt-8 pb-6" data-testid="paziente-profilo">
      <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Profilo</h1>
      <p className="text-sm text-[#0A0A0A]/60 mt-1">Il tuo account</p>

      <div className="mt-6 bg-white rounded-3xl p-5 shadow-sm border border-[#0A0A0A]/5" data-testid="profile-info">
        <div className="flex items-center gap-3">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#F58A1F] to-[#F5D419] flex items-center justify-center text-[#0A0A0A]">
            <User className="w-7 h-7" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-bold text-[#0A0A0A] truncate">{user?.nome} {user?.cognome}</div>
            <div className="text-xs text-[#0A0A0A]/55 truncate">{user?.email}</div>
          </div>
        </div>
      </div>

      <nav className="mt-4 space-y-2">
        <ProfileLink to="/paziente/fatture" icon={Receipt} label="Le mie fatture" testid="link-fatture" />
        <ProfileLink to="/paziente/privacy" icon={Shield} label="I miei dati (Privacy GDPR)" testid="link-privacy" />
      </nav>

      <button
        onClick={logout}
        data-testid="logout-btn"
        className="mt-8 w-full py-3 rounded-2xl bg-white border border-red-200 text-red-600 font-semibold text-sm inline-flex items-center justify-center gap-2 hover:bg-red-50"
      >
        <LogOut className="w-4 h-4" /> Esci
      </button>

      <p className="mt-6 text-[10px] text-center text-[#0A0A0A]/40 leading-relaxed">
        Funzionabene · BIDOC SRL · P.IVA 01985930930<br />
        Versione app 1.0.0
      </p>
    </div>
  );
}

function ProfileLink({ to, icon: Icon, label, testid }) {
  return (
    <Link
      to={to}
      data-testid={testid}
      className="flex items-center gap-3 p-4 bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="w-10 h-10 rounded-xl bg-[#0A0A0A]/5 flex items-center justify-center flex-shrink-0">
        <Icon className="w-5 h-5 text-[#0A0A0A]" />
      </div>
      <div className="flex-1 font-medium text-sm text-[#0A0A0A]">{label}</div>
      <ChevronRight className="w-4 h-4 text-[#0A0A0A]/40" />
    </Link>
  );
}
