import { useEffect, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import { motion } from "framer-motion";
import { Award, BookOpen, Calendar, Clock, Globe, GraduationCap, MapPin, Star } from "lucide-react";
import BookingSheet from "@/components/public/BookingSheet";
import SEO from "@/components/shared/SEO";

const GIORNI_IT = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"];

function groupSlotsByDay(slots) {
  const map = {};
  slots.forEach((s) => {
    const key = s.data_ora.slice(0, 10); // YYYY-MM-DD
    if (!map[key]) map[key] = { date: key, slots: [] };
    map[key].slots.push(s);
  });
  return Object.values(map).slice(0, 14);
}

function formatDayHeader(isoDate) {
  try {
    const d = new Date(isoDate + "T00:00:00");
    const giorno = GIORNI_IT[(d.getDay() + 6) % 7];
    return `${giorno} ${d.getDate()}/${d.getMonth() + 1}`;
  } catch { return isoDate; }
}

export default function TerapistaPublicPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const [terapista, setTerapista] = useState(null);
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [bookingOpen, setBookingOpen] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState(null);

  useEffect(() => {
    axios.get(`${API}/public/terapisti/${id}`).then(r => setTerapista(r.data)).catch(() => {});
    axios.get(`${API}/terapisti/${id}/slots?settimane=2`).then(r => setSlots(r.data.slots || [])).catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  // Auto-open the booking sheet on the first available slot when ?prenota=1 is set
  useEffect(() => {
    if (searchParams.get("prenota") !== "1") return;
    if (!user || loading) return;
    // Find first available slot from the fetched list (already flat)
    const firstAvailable = (slots || []).find(s => s.disponibile);
    if (firstAvailable) {
      setSelectedSlot(firstAvailable);
      setBookingOpen(true);
    } else {
      // No slots available → open the booking sheet with no slot so user sees the "no slots" state
      // OR redirect to chat with the therapist. For now, keep it simple: alert-style scroll to slots.
      const el = document.querySelector('[data-testid="therapist-slots"]');
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [searchParams, slots, loading, user]);

  const handleSlotClick = (slot) => {
    if (!slot.disponibile) return;
    setSelectedSlot(slot);
    setBookingOpen(true);
  };

  if (loading) {
    return <main className="min-h-[calc(100vh-80px)] bg-transparent flex items-center justify-center text-[#0A0A0A]/40">Caricamento profilo...</main>;
  }

  if (!terapista) {
    return (
      <main className="min-h-[calc(100vh-80px)] bg-transparent flex items-center justify-center px-6">
        <div className="text-center">
          <h1 className="font-serif text-3xl text-[#0A0A0A] mb-4">Terapeuta non trovato</h1>
          <Link to="/questionario" className="text-[#0A0A0A] hover:text-[#0A0A0A]/70">← Trova un terapeuta</Link>
        </div>
      </main>
    );
  }

  const grouped = groupSlotsByDay(slots);
  const genderLabel = terapista.genere === "F" ? "Psicologa" : "Psicologo";
  const fullName = `${terapista.nome || ""} ${terapista.cognome || ""}`.trim();
  const seoDesc = terapista.bio
    ? terapista.bio.replace(/\s+/g, " ").trim().slice(0, 160)
    : `${genderLabel} sessuologa/o online. ${terapista.anni_esperienza ? `${terapista.anni_esperienza} anni di esperienza. ` : ""}Prenota online su FunzionaBene.`;

  return (
    <main className="min-h-[calc(100vh-80px)] bg-transparent" data-testid="therapist-public">
      <SEO
        title={`${fullName} — ${genderLabel} sessuologo/a`}
        description={seoDesc}
        path={`/terapeuti/${terapista._id || id}`}
        image={terapista.foto_url || undefined}
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "Person",
          "name": fullName,
          "jobTitle": genderLabel,
          "image": terapista.foto_url || undefined,
          "worksFor": { "@type": "Organization", "name": "FunzionaBene", "url": "https://funzionabene.it" },
          "knowsLanguage": Array.isArray(terapista.lingue) ? terapista.lingue : undefined,
          "hasCredential": terapista.albo_numero
            ? { "@type": "EducationalOccupationalCredential", "credentialCategory": "License", "name": `Albo ${terapista.albo_ordine || ""} n. ${terapista.albo_numero}` }
            : undefined,
          "url": `https://funzionabene.it/terapeuti/${terapista._id || id}`
        }}
      />
      {/* Hero */}
      <section className="relative border-b border-[#0A0A0A]/10 bg-gradient-to-br from-[#F4F1ED] via-[#EAE4D9] to-[#F4F1ED]">
        <div className="relative max-w-7xl mx-auto px-6 lg:px-10 py-16 lg:py-24">
          <div className="grid lg:grid-cols-12 gap-10 items-start">
            <div className="lg:col-span-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="aspect-square rounded-3xl overflow-hidden bg-gradient-to-br from-[#0A0A0A]/20 to-[#6B8FA3]/20 border border-[#0A0A0A]/15 flex items-center justify-center"
              >
                {terapista.foto_url ? (
                  <img src={terapista.foto_url} alt={`${terapista.nome} ${terapista.cognome}`} className="w-full h-full object-cover" />
                ) : (
                  <span className="font-serif text-8xl text-[#0A0A0A]">
                    {(terapista.nome || "?")[0]}{(terapista.cognome || "?")[0]}
                  </span>
                )}
              </motion.div>

              <div className="mt-6 space-y-3 p-6 brand-card">
                {terapista.albo_numero && (
                  <div className="flex items-center gap-3 text-sm">
                    <Award className="w-4 h-4 text-[#6B8FA3] flex-shrink-0" />
                    <div>
                      <div className="text-[#0A0A0A]">Albo n. {terapista.albo_numero}</div>
                      <div className="text-xs text-[#0A0A0A]/50">{terapista.albo_ordine}</div>
                    </div>
                  </div>
                )}
                {terapista.anni_esperienza && (
                  <div className="flex items-center gap-3 text-sm">
                    <Clock className="w-4 h-4 text-[#6B8FA3] flex-shrink-0" />
                    <span className="text-[#0A0A0A]">{terapista.anni_esperienza} anni di esperienza</span>
                  </div>
                )}
                {Array.isArray(terapista.lingue) && terapista.lingue.length > 0 && (
                  <div className="flex items-center gap-3 text-sm">
                    <Globe className="w-4 h-4 text-[#6B8FA3] flex-shrink-0" />
                    <span className="text-[#0A0A0A]">{terapista.lingue.join(", ")}</span>
                  </div>
                )}
                <div className="flex items-center gap-3 text-sm pt-3 border-t border-[#0A0A0A]/15">
                  <span className="font-serif text-3xl text-[#0A0A0A]">€{terapista.prezzo_sessione || 90}</span>
                  <span className="text-xs text-[#0A0A0A]/50">per sessione di 50 min</span>
                </div>
              </div>
            </div>

            <div className="lg:col-span-8">
              <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">{genderLabel}</span>
              <h1 className="mt-3 font-serif text-5xl lg:text-6xl text-[#0A0A0A] leading-tight">
                Dr. {terapista.nome} {terapista.cognome}
              </h1>

              {Array.isArray(terapista.specializzazioni) && terapista.specializzazioni.length > 0 && (
                <div className="mt-6 flex flex-wrap gap-2">
                  {terapista.specializzazioni.map((s) => (
                    <span key={s} className="text-xs px-3 py-1.5 rounded-full bg-[#0A0A0A]/5 text-[#0A0A0A]/75 border border-[#0A0A0A]/10">
                      {s}
                    </span>
                  ))}
                </div>
              )}

              {terapista.bio && (
                <blockquote className="mt-10 font-serif text-2xl lg:text-3xl text-[#0A0A0A] leading-relaxed italic border-l-2 border-[#0A0A0A] pl-6">
                  &quot;{terapista.bio}&quot;
                </blockquote>
              )}

              {terapista.approccio_terapeutico && (
                <div className="mt-8">
                  <h3 className="text-xs tracking-[0.25em] uppercase text-[#0A0A0A] mb-3">Approccio terapeutico</h3>
                  <p className="text-[#0A0A0A]/70 leading-relaxed">{terapista.approccio_terapeutico}</p>
                </div>
              )}

              {Array.isArray(terapista.formazione) && terapista.formazione.length > 0 && (
                <div className="mt-10">
                  <h3 className="text-xs tracking-[0.25em] uppercase text-[#0A0A0A] mb-4 flex items-center gap-2">
                    <GraduationCap className="w-4 h-4" /> Formazione
                  </h3>
                  <ul className="space-y-3">
                    {terapista.formazione.map((f, i) => (
                      <li key={i} className="flex items-start gap-4 text-sm">
                        <span className="font-serif text-[#0A0A0A]">{f.anno || "—"}</span>
                        <div>
                          <div className="text-[#0A0A0A]">{f.titolo}</div>
                          <div className="text-[#0A0A0A]/50 text-xs">{f.istituto}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Booking section */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 py-16 lg:py-24" data-testid="booking-section">
        <div className="max-w-2xl mb-12">
          <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Disponibilità</span>
          <h2 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight">
            Scegli il tuo primo incontro.
          </h2>
          <p className="mt-4 text-[#0A0A0A]/60">
            Sessioni da 50 minuti online. Puoi annullare fino a 24h prima.
          </p>
        </div>

        {grouped.length === 0 ? (
          <div className="py-16 text-center border border-dashed border-[#0A0A0A]/15 rounded-3xl">
            <Calendar className="w-10 h-10 text-[#6B8FA3] mx-auto mb-4" />
            <p className="text-[#0A0A0A]/60">Nessun slot disponibile nelle prossime 2 settimane.</p>
            <p className="text-sm text-[#0A0A0A]/40 mt-2">Riprova più tardi o contatta il nostro supporto.</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {grouped.map((d) => (
              <div
                key={d.date}
                data-testid={`slot-day-${d.date}`}
                className="p-5 brand-card"
              >
                <div className="text-xs tracking-[0.2em] uppercase text-[#0A0A0A] mb-4">
                  {formatDayHeader(d.date)}
                </div>
                <div className="space-y-2">
                  {d.slots.slice(0, 6).map((s, i) => {
                    const time = s.data_ora.slice(11, 16);
                    return (
                      <button
                        key={i}
                        data-testid={`slot-btn-${s.data_ora}`}
                        onClick={() => handleSlotClick(s)}
                        disabled={!s.disponibile}
                        className={`w-full py-2.5 rounded-xl text-sm font-medium transition-all ${
                          s.disponibile
                            ? "bg-white/30 text-[#0A0A0A] hover:bg-[#0A0A0A] hover:text-white border border-[#0A0A0A]/30"
                            : "bg-white/5 text-[#0A0A0A]/30 cursor-not-allowed line-through"
                        }`}
                      >
                        {time}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <BookingSheet
        open={bookingOpen}
        onClose={() => setBookingOpen(false)}
        terapista={terapista}
        slot={selectedSlot}
        currentUser={user}
      />
    </main>
  );
}
