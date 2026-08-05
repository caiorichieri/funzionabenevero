import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { BookHeart, Plus, X, Trash2, Loader2, Check, EyeOff, Sparkles } from "lucide-react";

const MOODS = [
  { key: "felice",     emoji: "😊", label: "Felice",     color: "from-emerald-400 to-teal-400" },
  { key: "sereno",     emoji: "🙂", label: "Sereno",     color: "from-sky-400 to-cyan-400" },
  { key: "neutro",     emoji: "😐", label: "Neutro",     color: "from-stone-300 to-stone-400" },
  { key: "ansioso",    emoji: "😟", label: "Ansioso",    color: "from-amber-400 to-yellow-500" },
  { key: "triste",     emoji: "😢", label: "Triste",     color: "from-blue-500 to-indigo-500" },
  { key: "arrabbiato", emoji: "😠", label: "Arrabbiato", color: "from-red-500 to-orange-500" },
];

const QUICK_TAGS = ["lavoro", "coppia", "famiglia", "sonno", "corpo", "energia", "solitudine", "gratitudine"];

const formatDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const same = d.toDateString() === now.toDateString();
  const y = new Date(now); y.setDate(now.getDate() - 1);
  const yest = d.toDateString() === y.toDateString();
  const time = d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
  if (same) return `Oggi · ${time}`;
  if (yest) return `Ieri · ${time}`;
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "long" }) + ` · ${time}`;
};

export default function DiarioPage() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [composerOpen, setComposerOpen] = useState(false);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/diario/mine`, { withCredentials: true });
      setEntries(r.data?.items || []);
    } catch (e) {
      setError(e.response?.data?.detail || "Errore caricamento diario");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNew = () => {
    setDraft({ mood: "sereno", contenuto: "", tags: [], condividi_con_terapeuta: true });
    setComposerOpen(true);
    setError("");
  };
  const openEdit = (e) => {
    if (e.letto_da_terapeuta) return;
    setDraft({ id: e.id, mood: e.mood, contenuto: e.contenuto, tags: e.tags || [], condividi_con_terapeuta: e.condividi_con_terapeuta });
    setComposerOpen(true);
    setError("");
  };
  const toggleTag = (tag) => {
    setDraft(d => ({ ...d, tags: d.tags.includes(tag) ? d.tags.filter(t => t !== tag) : [...d.tags, tag].slice(0, 8) }));
  };

  const save = async () => {
    if (!draft.contenuto.trim()) { setError("Scrivi qualcosa prima di salvare"); return; }
    setSaving(true);
    setError("");
    try {
      const payload = {
        mood: draft.mood, contenuto: draft.contenuto.trim(),
        tags: draft.tags, condividi_con_terapeuta: draft.condividi_con_terapeuta,
      };
      if (draft.id) {
        await axios.put(`${API}/diario/${draft.id}`, payload, { withCredentials: true });
      } else {
        await axios.post(`${API}/diario`, payload, { withCredentials: true });
      }
      setComposerOpen(false); setDraft(null);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || "Errore salvataggio");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    if (!confirm("Vuoi eliminare questa nota?")) return;
    await axios.delete(`${API}/diario/${id}`, { withCredentials: true });
    await load();
  };

  return (
    <div className="min-h-screen bg-[#F4F1ED] pb-24" data-testid="diario-page">
      {/* Header */}
      <div className="bg-gradient-to-br from-[#F58A1F] via-[#F5A419] to-[#F5D419] px-5 pt-8 pb-14 rounded-b-3xl relative overflow-hidden">
        <div className="absolute -right-8 -top-8 w-40 h-40 bg-white/10 rounded-full blur-2xl" />
        <div className="relative">
          <div className="flex items-center gap-2 text-[#0A0A0A]/60 text-xs uppercase tracking-widest font-medium">
            <BookHeart className="w-3.5 h-3.5" /> Il tuo diario emozionale
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-[#0A0A0A] font-[Outfit] mt-2 leading-tight">
            Come ti senti oggi?
          </h1>
          <p className="text-sm text-[#0A0A0A]/70 mt-2 max-w-md">
            Annota un momento, un pensiero, un&apos;emozione. Il tuo terapeuta potrà leggere le note che scegli di condividere prima della prossima sessione.
          </p>
        </div>
      </div>

      {/* New entry button */}
      <div className="px-5 -mt-8 relative z-10">
        <button
          onClick={openNew}
          data-testid="diario-new-btn"
          className="w-full bg-[#0A0A0A] text-white rounded-2xl py-4 shadow-xl flex items-center justify-center gap-2 font-semibold hover:opacity-90 transition-opacity"
        >
          <Plus className="w-5 h-5" /> Nuova nota
        </button>
      </div>

      {/* Entries timeline */}
      <div className="px-5 mt-6 space-y-3">
        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-[#F58A1F]" /></div>
        ) : entries.length === 0 ? (
          <div className="py-14 text-center" data-testid="diario-empty">
            <Sparkles className="w-10 h-10 mx-auto text-[#F58A1F]/40 mb-3" />
            <p className="text-[#0A0A0A]/60 text-sm max-w-xs mx-auto leading-relaxed">
              Il tuo diario è vuoto. Anche una singola parola può aiutarti a capirti meglio.
            </p>
          </div>
        ) : (
          entries.map((e) => {
            const mood = MOODS.find(m => m.key === e.mood) || MOODS[2];
            return (
              <div
                key={e.id}
                className="bg-white rounded-2xl p-4 shadow-sm border border-[#0A0A0A]/5"
                data-testid={`diario-entry-${e.id}`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-11 h-11 rounded-2xl bg-gradient-to-br ${mood.color} flex items-center justify-center text-2xl flex-shrink-0 shadow-sm`}>
                    {mood.emoji}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-medium text-[#0A0A0A]/80">{mood.label}</span>
                      <span className="text-[10px] text-[#0A0A0A]/40">·</span>
                      <span className="text-xs text-[#0A0A0A]/55">{formatDate(e.created_at)}</span>
                      {!e.condividi_con_terapeuta && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-[#0A0A0A]/50 bg-[#0A0A0A]/5 px-2 py-0.5 rounded-full">
                          <EyeOff className="w-2.5 h-2.5" /> Privato
                        </span>
                      )}
                      {e.letto_da_terapeuta && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                          <Check className="w-2.5 h-2.5" /> Letto dal terapeuta
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-[#0A0A0A] leading-relaxed mt-1.5 whitespace-pre-wrap">{e.contenuto}</p>
                    {e.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {e.tags.map(t => (
                          <span key={t} className="text-[10px] px-2 py-0.5 bg-[#F58A1F]/10 text-[#F58A1F] rounded-full">
                            #{t}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center gap-3 mt-3">
                      {!e.letto_da_terapeuta && (
                        <button
                          onClick={() => openEdit(e)}
                          className="text-xs text-[#F58A1F] font-medium hover:underline"
                          data-testid={`diario-edit-${e.id}`}
                        >
                          Modifica
                        </button>
                      )}
                      <button
                        onClick={() => remove(e.id)}
                        className="text-xs text-red-600/80 hover:text-red-700 inline-flex items-center gap-1"
                        data-testid={`diario-delete-${e.id}`}
                      >
                        <Trash2 className="w-3 h-3" /> Elimina
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Composer sheet */}
      {composerOpen && draft && (
        <div className="fixed inset-0 z-40 bg-black/50 flex items-end sm:items-center justify-center" data-testid="diario-composer">
          <div className="bg-white w-full sm:max-w-lg sm:rounded-3xl rounded-t-3xl max-h-[90vh] overflow-hidden flex flex-col animate-slide-up">
            <div className="p-4 border-b border-[#0A0A0A]/10 flex items-center justify-between">
              <h2 className="font-bold text-[#0A0A0A]">{draft.id ? "Modifica nota" : "Nuova nota"}</h2>
              <button onClick={() => { setComposerOpen(false); setDraft(null); }} className="p-2 hover:bg-[#0A0A0A]/5 rounded-xl">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 overflow-y-auto flex-1 space-y-5">
              {/* Mood picker */}
              <div>
                <div className="text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-2 font-medium">Come ti senti</div>
                <div className="grid grid-cols-3 gap-2">
                  {MOODS.map(m => (
                    <button
                      key={m.key}
                      onClick={() => setDraft(d => ({ ...d, mood: m.key }))}
                      data-testid={`diario-mood-${m.key}`}
                      className={`p-3 rounded-2xl border-2 transition-all ${
                        draft.mood === m.key
                          ? "border-[#F58A1F] bg-gradient-to-br " + m.color + " shadow-md scale-105"
                          : "border-[#0A0A0A]/10 bg-white hover:border-[#0A0A0A]/30"
                      }`}
                    >
                      <div className="text-2xl">{m.emoji}</div>
                      <div className="text-[10px] font-medium mt-1 text-[#0A0A0A]/80">{m.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Textarea */}
              <div>
                <div className="text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-2 font-medium">La tua nota</div>
                <textarea
                  value={draft.contenuto}
                  onChange={e => setDraft(d => ({ ...d, contenuto: e.target.value.slice(0, 1000) }))}
                  data-testid="diario-content-input"
                  placeholder="Cosa è successo? Come ti sei sentito?"
                  rows={5}
                  className="w-full p-3 border border-[#0A0A0A]/15 rounded-2xl text-sm leading-relaxed focus:border-[#F58A1F] outline-none resize-none"
                />
                <div className="text-[10px] text-[#0A0A0A]/40 mt-1 text-right">{draft.contenuto.length}/1000</div>
              </div>

              {/* Tags */}
              <div>
                <div className="text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-2 font-medium">Tag (max 8)</div>
                <div className="flex flex-wrap gap-2">
                  {QUICK_TAGS.map(t => (
                    <button
                      key={t}
                      onClick={() => toggleTag(t)}
                      data-testid={`diario-tag-${t}`}
                      className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                        draft.tags.includes(t)
                          ? "bg-[#F58A1F] text-white"
                          : "bg-[#0A0A0A]/5 text-[#0A0A0A]/70 hover:bg-[#0A0A0A]/10"
                      }`}
                    >
                      #{t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Share toggle */}
              <label className="flex items-center gap-3 p-3 bg-[#0A0A0A]/[0.03] rounded-2xl cursor-pointer">
                <input
                  type="checkbox"
                  checked={draft.condividi_con_terapeuta}
                  onChange={e => setDraft(d => ({ ...d, condividi_con_terapeuta: e.target.checked }))}
                  data-testid="diario-share-toggle"
                  className="w-5 h-5 accent-[#F58A1F]"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-[#0A0A0A]">Condividi con il terapeuta</div>
                  <div className="text-xs text-[#0A0A0A]/60">
                    {draft.condividi_con_terapeuta
                      ? "Il tuo terapeuta potrà leggere questa nota prima della sessione."
                      : "Questa nota resterà privata, solo tu la vedrai."}
                  </div>
                </div>
              </label>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-800" data-testid="diario-error">
                  {error}
                </div>
              )}
            </div>
            <div className="p-4 border-t border-[#0A0A0A]/10 flex gap-3 bg-white">
              <button
                onClick={() => { setComposerOpen(false); setDraft(null); }}
                className="flex-1 py-3 rounded-full border border-[#0A0A0A]/15 font-medium text-sm"
                data-testid="diario-cancel-btn"
              >
                Annulla
              </button>
              <button
                onClick={save}
                disabled={saving}
                data-testid="diario-save-btn"
                className="flex-1 py-3 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold text-sm inline-flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Salva"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
