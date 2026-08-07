import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { useAuth, API } from "@/contexts/AuthContext";
import {
  Video, Sparkles, Battery, BookHeart, Clock, Calendar, MessageCircle, Search,
} from "lucide-react";

/**
 * Mobile home page for the paziente PWA — matches the site mockup.
 * If the paziente already has a therapist, we steer them toward that
 * therapist's calendar instead of the general browse experience.
 */
export default function PazienteHome() {
  const { user } = useAuth();
  const [next, setNext] = useState(null);
  const [mio, setMio] = useState(null); // { has_terapeuta, terapeuta, next_slot, slots_next_30d_count, unread_messages }
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [appts, mine] = await Promise.all([
          axios.get(`${API}/appuntamenti`, { withCredentials: true }),
          axios.get(`${API}/paziente/mio-terapeuta`, { withCredentials: true }).catch(() => ({ data: { has_terapeuta: false } })),
        ]);
        const now = new Date();
        const upcoming = (appts.data || [])
          .filter((a) => a.stato !== "annullato" && a.stato !== "cancellato" && new Date(a.data_ora) >= now)
          .sort((a, b) => new Date(a.data_ora) - new Date(b.data_ora));
        if (!cancelled) {
          setNext(upcoming[0] || null);
          setMio(mine.data || null);
        }
      } catch {
        if (!cancelled) { setNext(null); setMio({ has_terapeuta: false }); }
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

      {/* Primary card — next session OR "il tuo terapeuta" */}
      <section className="mt-6">
        {loading ? (
          <div className="h-32 rounded-3xl bg-white/40 animate-pulse" />
        ) : next ? (
          <NextSessionCard app={next} />
        ) : mio?.has_terapeuta ? (
          <MioTerapeutaCard mio={mio} />
        ) : (
          <NoTerapeutaCard />
        )}
      </section>

      {/* Coach Sessuale — placeholder */}
      <CoachPreview />

      {/* Diario shortcut */}
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

function MioTerapeutaCard({ mio }) {
  const t = mio.terapeuta || {};
  const hasSlots = (mio.slots_next_30d_count || 0) > 0;
  const nextSlot = mio.next_slot ? new Date(mio.next_slot) : null;
  const initials = `${(t.nome || "").charAt(0)}${(t.cognome || "").charAt(0)}`.toUpperCase() || "T";

  return (
    <div className="rounded-3xl p-5 text-white shadow-xl" style={{ background: "#0A0A0A" }} data-testid="home-mio-terapeuta">
      <div className="text-[10px] tracking-[0.22em] uppercase font-semibold text-[#F5D419]">Il tuo terapeuta</div>
      <div className="mt-3 flex items-center gap-3">
        {t.foto_url ? (
          <img src={t.foto_url} alt={`${t.nome} ${t.cognome}`} className="w-12 h-12 rounded-2xl object-cover flex-shrink-0" />
        ) : (
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-bold flex items-center justify-center flex-shrink-0">
            {initials}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="font-bold text-base text-white truncate">Dr. {t.nome} {t.cognome}</div>
          <div className="text-xs text-white/60 truncate">
            {(t.specializzazioni || [])[0] || "Sessuologo"} · € {t.prezzo_seduta}/seduta
          </div>
        </div>
      </div>

      {hasSlots ? (
        <div className="mt-4">
          {nextSlot && (
            <div className="text-xs text-white/70 mb-2">
              Prossimo slot: <strong className="text-white">{nextSlot.toLocaleDateString("it-IT", { day: "2-digit", month: "long" })} · {nextSlot.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}</strong>
            </div>
          )}
          <Link
            to={`/terapeuti/${t.id}?prenota=1`}
            data-testid="home-prenota-mio-terapeuta"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold text-sm"
          >
            <Calendar className="w-4 h-4" /> Prenota una seduta
          </Link>
        </div>
      ) : (
        <div className="mt-4">
          <div className="text-xs text-white/70 mb-2 leading-relaxed">
            Nessuna disponibilità nei prossimi 30 giorni. Contattalo per fissare un appuntamento.
          </div>
          <Link
            to="/paziente/chat"
            data-testid="home-messaggio-mio-terapeuta"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold text-sm"
          >
            <MessageCircle className="w-4 h-4" /> Manda un messaggio
            {mio.unread_messages > 0 && (
              <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] rounded-full bg-[#0A0A0A] text-white text-[10px] font-bold px-1">
                {mio.unread_messages}
              </span>
            )}
          </Link>
        </div>
      )}

      {/* Discreet "Cerca un altro" footer */}
      <div className="mt-4 pt-3 border-t border-white/10">
        <Link
          to="/questionario"
          data-testid="home-cerca-altro"
          className="text-[11px] text-white/40 hover:text-white/70 inline-flex items-center gap-1"
        >
          <Search className="w-3 h-3" /> Cerca un altro terapeuta
        </Link>
      </div>
    </div>
  );
}

function NoTerapeutaCard() {
  return (
    <div className="rounded-3xl p-6 text-white text-center shadow-xl" style={{ background: "#0A0A0A" }} data-testid="home-no-terapeuta">
      <div className="text-[10px] tracking-[0.22em] uppercase font-semibold text-[#F5D419] mb-2">Inizia il tuo percorso</div>
      <p className="text-sm text-white/70 max-w-xs mx-auto leading-relaxed">
        Trova il terapeuta giusto per te tra i nostri professionisti verificati.
      </p>
      <Link
        to="/questionario"
        data-testid="home-questionario-btn"
        className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold text-sm"
      >
        <Sparkles className="w-4 h-4" /> Trova il tuo terapeuta
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
