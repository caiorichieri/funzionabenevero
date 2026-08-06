import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { useAuth, API } from "@/contexts/AuthContext";
import {
  Video, Sparkles, Battery, Waves, MessageSquareHeart, BookHeart, Clock,
} from "lucide-react";

/**
 * Mobile home page for the paziente PWA — matches the site mockup:
 * - "Buongiorno {nome}" greeting
 * - Dark card with the next appointment + Entra CTA
 * - Yellow floating "Consigliato" side-card
 * - Coach Sessuale preview card (placeholder — real chat lands Fase 19)
 */
export default function PazienteHome() {
  const { user } = useAuth();
  const [next, setNext] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(`${API}/appuntamenti`, { withCredentials: true });
        const now = new Date();
        const upcoming = (r.data || [])
          .filter((a) => a.stato !== "annullato" && new Date(a.data_ora) >= now)
          .sort((a, b) => new Date(a.data_ora) - new Date(b.data_ora));
        if (!cancelled) setNext(upcoming[0] || null);
      } catch {
        if (!cancelled) setNext(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const firstName = user?.nome || "";

  return (
    <div className="px-5 pt-8" data-testid="paziente-home">
      {/* Greeting */}
      <header className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] tracking-[0.22em] uppercase font-semibold text-[#0A0A0A]/55">Buongiorno,</div>
          <h1 className="text-4xl font-bold text-[#0A0A0A] font-[Outfit] leading-tight mt-1">
            {firstName || "amico"}
          </h1>
        </div>
        <div className="flex-shrink-0 w-14 h-14 rounded-full bg-white/70 flex items-center justify-center text-2xl shadow-sm" title="Il tuo compagno">
          🌱
        </div>
      </header>

      {/* Next session card */}
      <section className="mt-6 relative">
        {loading ? (
          <div className="h-32 rounded-3xl bg-white/40 animate-pulse" />
        ) : next ? (
          <NextSessionCard app={next} />
        ) : (
          <NoSessionCard />
        )}

        {/* Side floating "Consigliato" chip */}
        <div className="absolute -right-2 top-4 bg-white rounded-l-2xl px-3 py-2.5 shadow-lg max-w-[145px]" data-testid="home-consigliato-chip">
          <div className="text-[9px] tracking-widest uppercase text-[#0A0A0A]/55 font-semibold">Consigliato</div>
          <div className="text-xs font-semibold text-[#0A0A0A] leading-tight mt-0.5 flex items-center gap-1">
            <Waves className="w-3 h-3 text-[#F58A1F]" /> Esercizio resp…
          </div>
        </div>
      </section>

      {/* Coach Sessuale — placeholder */}
      <CoachPreview />

      {/* Diario shortcut floating side card */}
      <section className="mt-4">
        <Link
          to="/paziente/diario"
          data-testid="home-diario-shortcut"
          className="block bg-white rounded-2xl p-4 shadow-sm border border-[#0A0A0A]/5 hover:shadow-md transition-shadow"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[#F58A1F] to-[#F5D419] flex items-center justify-center flex-shrink-0">
              <BookHeart className="w-5 h-5 text-[#0A0A0A]" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-sm text-[#0A0A0A]">Diario emozionale</div>
              <p className="text-xs text-[#0A0A0A]/60 mt-0.5 leading-snug">Anche una parola. Il tuo terapeuta lo legge prima della sessione.</p>
            </div>
          </div>
        </Link>
      </section>
    </div>
  );
}

function NextSessionCard({ app }) {
  const when = new Date(app.data_ora);
  const now = new Date();
  const sameDay = when.toDateString() === now.toDateString();
  const y = new Date(now); y.setDate(now.getDate() + 1);
  const isTomorrow = when.toDateString() === y.toDateString();
  const dayLabel = sameDay ? "OGGI" : isTomorrow ? "DOMANI" : when.toLocaleDateString("it-IT", { weekday: "short", day: "2-digit", month: "short" }).toUpperCase();
  const time = when.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
  const canJoin = (when.getTime() - now.getTime()) <= 15 * 60 * 1000 && (now.getTime() - when.getTime()) <= 60 * 60 * 1000;

  return (
    <div className="rounded-3xl p-5 text-white shadow-xl" style={{ background: "#0A0A0A" }} data-testid="home-next-session">
      <div className="text-[10px] tracking-[0.22em] uppercase font-semibold text-[#F5D419]">
        {dayLabel} · {time}
      </div>
      <h2 className="text-xl font-bold text-white mt-1 leading-tight">
        Sessione con {app.terapeuta_nome || "il tuo terapeuta"}
      </h2>
      <div className="flex items-center gap-1.5 mt-1.5 text-xs text-white/60">
        <Video className="w-3.5 h-3.5" />
        <span>Online · {app.durata_minuti || 50} minuti</span>
      </div>
      {canJoin ? (
        <Link
          to={`/seduta/${app._id}`}
          data-testid="home-join-session-btn"
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold text-sm"
        >
          <Video className="w-4 h-4" /> Entra
        </Link>
      ) : (
        <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 text-white/70 text-xs">
          <Clock className="w-3.5 h-3.5" /> Il link Entra si attiva 15 min prima
        </div>
      )}
    </div>
  );
}

function NoSessionCard() {
  return (
    <div className="rounded-3xl p-6 text-white text-center shadow-xl" style={{ background: "#0A0A0A" }}>
      <div className="text-[10px] tracking-[0.22em] uppercase font-semibold text-[#F5D419] mb-2">Nessuna seduta in programma</div>
      <p className="text-sm text-white/70 max-w-xs mx-auto leading-relaxed">
        Puoi prenotare una nuova sessione con il tuo terapeuta.
      </p>
      <Link
        to="/terapeuti"
        data-testid="home-book-btn"
        className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold text-sm"
      >
        <Sparkles className="w-4 h-4" /> Prenota
      </Link>
    </div>
  );
}

function CoachPreview() {
  return (
    <section className="mt-4 bg-white rounded-3xl p-4 shadow-sm border border-[#0A0A0A]/5" data-testid="home-coach-preview">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#E89B9F] to-[#F58A1F] flex items-center justify-center text-white font-bold text-xs">CS</div>
          <div>
            <div className="text-sm font-semibold text-[#0A0A0A]">Coach Sessuale</div>
            <div className="text-[10px] text-[#0A0A0A]/45">In arrivo · anteprima</div>
          </div>
        </div>
        <span className="text-[9px] px-2 py-1 rounded-full bg-[#F58A1F]/10 text-[#F58A1F] font-semibold uppercase tracking-widest">Presto</span>
      </div>
      <div className="space-y-2">
        <div className="text-xs text-[#0A0A0A]/70 leading-relaxed">
          Come ti senti oggi rispetto a ieri?
        </div>
        <div className="flex justify-end">
          <div className="max-w-[80%] rounded-2xl rounded-br-md bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] px-3 py-2 text-xs leading-relaxed">
            Meglio, anche se ho avuto un momento difficile in pausa pranzo.
          </div>
        </div>
        <div className="text-xs text-[#0A0A0A]/70 leading-relaxed">
          Vuoi annotarlo nel diario? Lo leggeremo insieme stasera.
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-[#0A0A0A]/5 flex items-center gap-1.5 text-[10px] text-[#0A0A0A]/45">
        <Battery className="w-3 h-3" />
        <span>Il Coach Sessuale non sostituisce il terapeuta.</span>
      </div>
    </section>
  );
}
