import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { useAuth } from "@/contexts/AuthContext";
import { Save, Plus, Trash2, CheckCircle } from "lucide-react";
import OnboardingSection from "@/components/therapist/OnboardingSection";

const GIORNI = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"];
const GENERI_T = [{ v:"M",l:"Uomo" },{ v:"F",l:"Donna" },{ v:"Altro",l:"Non binario/Altro" }];

export default function TerapistaProfile() {
  const { user, refreshUser } = useAuth();
  const [profilo, setProfilo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    nome:"", cognome:"", telefono:"", bio:"", anni_esperienza:"",
    genere:"", albo_numero:"", albo_ordine:"", albo_iscrizione_data:"",
    assicurazione_compagnia:"", assicurazione_numero_polizza:"", assicurazione_scadenza:"",
    prezzo_sessione:"", approccio_terapeutico:"",
    specializzazioni:"", lingue:"", disponibilita:[],
    // Dati fiscali + residenza + IBAN
    partita_iva:"", codice_fiscale:"", data_nascita:"", nato_all_estero:false,
    luogo_nascita_comune:"", luogo_nascita_provincia:"", paese_nascita:"",
    indirizzo:"", citta:"", cap:"", provincia_residenza:"",
    iban:"",
  });

  const fetchProfilo = useCallback(() => {
    axios.get(`${API}/terapisti/profilo/me`, { withCredentials: true })
      .then(r => {
        const p = r.data;
        setProfilo(p);
        setForm({
          nome: p.nome||"", cognome: p.cognome||"", telefono: p.telefono||"",
          bio: p.bio||"", anni_esperienza: p.anni_esperienza||"",
          genere: p.genere||"", albo_numero: p.albo_numero||"",
          albo_ordine: p.albo_ordine||"", albo_iscrizione_data: p.albo_iscrizione_data||"",
          assicurazione_compagnia: p.assicurazione_compagnia||"",
          assicurazione_numero_polizza: p.assicurazione_numero_polizza||"",
          assicurazione_scadenza: p.assicurazione_scadenza||"",
          prezzo_sessione: p.prezzo_sessione||"",
          approccio_terapeutico: p.approccio_terapeutico||"",
          specializzazioni: (p.specializzazioni||[]).join(", "),
          lingue: (p.lingue||[]).join(", "),
          disponibilita: p.disponibilita||[],
          partita_iva: p.partita_iva||"",
          codice_fiscale: p.codice_fiscale||"",
          data_nascita: p.data_nascita||"",
          nato_all_estero: !!p.nato_all_estero,
          luogo_nascita_comune: p.luogo_nascita_comune||"",
          luogo_nascita_provincia: p.luogo_nascita_provincia||"",
          paese_nascita: p.paese_nascita||"",
          indirizzo: p.indirizzo||"", citta: p.citta||"", cap: p.cap||"",
          provincia_residenza: p.provincia_residenza||"",
          iban: p.iban||"",
        });
      }).catch(console.error).finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchProfilo(); }, [fetchProfilo]);

  const handleSave = async (e) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      const payload = {
        ...form,
        anni_esperienza: form.anni_esperienza ? Number(form.anni_esperienza) : null,
        prezzo_sessione: form.prezzo_sessione ? Number(form.prezzo_sessione) : null,
        specializzazioni: form.specializzazioni ? form.specializzazioni.split(",").map(s=>s.trim()).filter(Boolean) : [],
        lingue: form.lingue ? form.lingue.split(",").map(s=>s.trim()).filter(Boolean) : []
      };
      const res = await axios.put(`${API}/terapisti/profilo/me`, payload, { withCredentials: true });
      setProfilo(res.data); setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || "Errore nel salvataggio");
    } finally { setSaving(false); }
  };

  const addDisponibilita = () => setForm(f => ({ ...f, disponibilita: [...f.disponibilita, { giorno:"Lunedì", ora_inizio:"09:00", ora_fine:"18:00" }] }));
  const removeDisponibilita = (i) => setForm(f => ({ ...f, disponibilita: f.disponibilita.filter((_,idx)=>idx!==i) }));
  const updateDisp = (i, k, v) => setForm(f => ({ ...f, disponibilita: f.disponibilita.map((d,idx)=>idx===i?{...d,[k]:v}:d) }));

  if (loading) return <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Il mio Profilo</h1>
        <p className="text-[#0A0A0A]/65 mt-1">Gestisci le tue informazioni professionali</p>
      </div>

      {/* Onboarding: documenti + SMS OTP + DPR 445 */}
      <OnboardingSection
        profilo={profilo}
        currentUser={user}
        onRefresh={async () => { await refreshUser(); fetchProfilo(); }}
      />

      {error && <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>}
      {saved && <div data-testid="profile-saved" className="p-3 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm flex items-center gap-2"><CheckCircle className="w-4 h-4" /> Profilo salvato con successo!</div>}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Dati personali */}
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4">Dati Personali</h3>
          <div className="grid grid-cols-2 gap-4">
            {[["nome","Nome*"],["cognome","Cognome*"],["telefono","Telefono"],].map(([k,l]) => (
              <div key={k} className={k==="telefono"?"col-span-2 sm:col-span-1":""}>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">{l}</label>
                <input data-testid={`profilo-${k}`} type="text" value={form[k]}
                  onChange={e => setForm({...form,[k]:e.target.value})} required={k==="nome"||k==="cognome"}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>
            ))}
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Genere</label>
              <select value={form.genere} onChange={e => setForm({...form,genere:e.target.value})}
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] bg-white">
                <option value="">Seleziona</option>
                {GENERI_T.map(g => <option key={g.v} value={g.v}>{g.l}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Biografia</label>
            <textarea data-testid="profilo-bio" value={form.bio} onChange={e => setForm({...form,bio:e.target.value})} rows={4}
              placeholder="Presenta te stesso ai pazienti: esperienza, approccio, valori..."
              className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] resize-none" />
          </div>
        </div>

        {/* Dati Fiscali (per fatturazione sanitaria + bonifici) */}
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-1">Dati Fiscali</h3>
          <p className="text-xs text-[#0A0A0A]/60 mb-4">Necessari per emettere fatture sanitarie e ricevere i bonifici del 70%.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Partita IVA <span className="text-red-600">*</span></label>
              <input data-testid="profilo-piva" type="text" value={form.partita_iva}
                onChange={e => setForm({...form, partita_iva: e.target.value.replace(/[^0-9]/g,"").slice(0,11)})}
                maxLength={11} placeholder="12345678903" required
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] font-mono tracking-wider" />
              <p className="text-xs text-[#0A0A0A]/55 mt-1">Obbligatoria per emettere fattura sanitaria al paziente.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Codice Fiscale <span className="text-red-600">*</span></label>
              <input data-testid="profilo-cf" type="text" value={form.codice_fiscale}
                onChange={e => setForm({...form, codice_fiscale: e.target.value.toUpperCase().replace(/\s/g,"")})}
                maxLength={16} placeholder="RSSMRA80A01H501U" required
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] uppercase" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Data di Nascita</label>
              <input type="date" value={form.data_nascita} onChange={e => setForm({...form, data_nascita: e.target.value})}
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div className="flex items-center pt-6">
              <label className="inline-flex items-center gap-2 text-sm text-[#0A0A0A]">
                <input type="checkbox" checked={form.nato_all_estero} onChange={e => setForm({...form, nato_all_estero: e.target.checked})} />
                Nato/a all&apos;estero
              </label>
            </div>
            {form.nato_all_estero ? (
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Paese di Nascita</label>
                <input type="text" value={form.paese_nascita} onChange={e => setForm({...form, paese_nascita: e.target.value})}
                  placeholder="Es. Francia"
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Comune di Nascita</label>
                  <input type="text" value={form.luogo_nascita_comune} onChange={e => setForm({...form, luogo_nascita_comune: e.target.value})}
                    placeholder="Roma"
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Provincia di Nascita</label>
                  <input type="text" value={form.luogo_nascita_provincia} onChange={e => setForm({...form, luogo_nascita_provincia: e.target.value.toUpperCase()})}
                    maxLength={2} placeholder="RM"
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] uppercase" />
                </div>
              </>
            )}
          </div>
          <div className="mt-6 pt-4 border-t border-[#0A0A0A]/10">
            <label className="block text-sm font-medium text-[#0A0A0A] mb-1">IBAN <span className="text-xs text-[#0A0A0A]/50">(per ricevere i bonifici 70%)</span></label>
            <input data-testid="profilo-iban" type="text" value={form.iban}
              onChange={e => setForm({...form, iban: e.target.value.toUpperCase().replace(/\s/g,"")})}
              maxLength={34} placeholder="IT60 X054 2811 1010 0000 0123 456"
              className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] uppercase font-mono tracking-wider" />
            <p className="text-xs text-[#0A0A0A]/55 mt-1">Formato italiano: IT + 2 cifre + 23 caratteri. Verifica la correttezza — usiamo questo IBAN per accreditarti il 70% dei pagamenti dei tuoi pazienti.</p>
          </div>
        </div>

        {/* Residenza */}
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4">Residenza</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-4">
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Indirizzo</label>
              <input type="text" value={form.indirizzo} onChange={e => setForm({...form, indirizzo: e.target.value})}
                placeholder="Via / Piazza / Numero civico"
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Città</label>
              <input type="text" value={form.citta} onChange={e => setForm({...form, citta: e.target.value})}
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">CAP</label>
              <input type="text" value={form.cap} onChange={e => setForm({...form, cap: e.target.value.replace(/\D/g,"").slice(0,5)})}
                maxLength={5} placeholder="00100"
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Provincia</label>
              <input type="text" value={form.provincia_residenza} onChange={e => setForm({...form, provincia_residenza: e.target.value.toUpperCase().slice(0,2)})}
                maxLength={2} placeholder="RM"
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] uppercase" />
            </div>
          </div>
        </div>

        {/* Albo */}
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4">Iscrizione Albo Italiano</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Numero Albo</label>
              <input data-testid="profilo-albo" type="text" value={form.albo_numero} onChange={e => setForm({...form,albo_numero:e.target.value})}
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Data Iscrizione</label>
              <input type="date" value={form.albo_iscrizione_data} onChange={e => setForm({...form,albo_iscrizione_data:e.target.value})}
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Anni di Esperienza</label>
              <input type="number" value={form.anni_esperienza} onChange={e => setForm({...form,anni_esperienza:e.target.value})} min="0"
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Ordine di appartenenza</label>
            <input type="text" value={form.albo_ordine} onChange={e => setForm({...form,albo_ordine:e.target.value})}
              placeholder="Es. Ordine degli Psicologi della Lombardia"
              className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
          </div>
        </div>

        {/* Assicurazione */}
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4">Assicurazione Professionale</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Compagnia</label>
              <input type="text" value={form.assicurazione_compagnia} onChange={e => setForm({...form,assicurazione_compagnia:e.target.value})}
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Numero Polizza</label>
              <input type="text" value={form.assicurazione_numero_polizza} onChange={e => setForm({...form,assicurazione_numero_polizza:e.target.value})}
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Data Scadenza</label>
              <input data-testid="profilo-assic-scadenza" type="date" value={form.assicurazione_scadenza} onChange={e => setForm({...form,assicurazione_scadenza:e.target.value})}
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
          </div>
        </div>

        {/* Competenze */}
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4">Competenze e Servizi</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Specializzazioni (separare con virgola)</label>
              <input type="text" value={form.specializzazioni} onChange={e => setForm({...form,specializzazioni:e.target.value})}
                placeholder="Sessuologia, Terapia di coppia, Disfunzioni sessuali"
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Lingue (separare con virgola)</label>
              <input type="text" value={form.lingue} onChange={e => setForm({...form,lingue:e.target.value})}
                placeholder="Italiano, Inglese, Spagnolo"
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Approccio Terapeutico</label>
              <input type="text" value={form.approccio_terapeutico} onChange={e => setForm({...form,approccio_terapeutico:e.target.value})}
                placeholder="Es. Cognitivo-Comportamentale integrato"
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Prezzo per Sessione (€)</label>
              <input data-testid="profilo-prezzo" type="number" value={form.prezzo_sessione} onChange={e => setForm({...form,prezzo_sessione:e.target.value})} min="0" step="5"
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
          </div>
        </div>

        {/* Disponibilità */}
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[#0A0A0A] font-[Outfit]">Disponibilità Settimanale</h3>
            <button type="button" onClick={addDisponibilita}
              className="flex items-center gap-1 text-sm text-[#0A0A0A] hover:text-[#0A0A0A]/70">
              <Plus className="w-4 h-4" /> Aggiungi
            </button>
          </div>
          {form.disponibilita.length === 0 && (
            <p className="text-sm text-[#0A0A0A]/55 text-center py-4">Nessuna disponibilità impostata. Clicca &quot;Aggiungi&quot; per iniziare.</p>
          )}
          <div className="space-y-3">
            {form.disponibilita.map((d, i) => (
              <div key={`${d.giorno}-${d.ora_inizio}-${i}`} className="flex items-center gap-3">
                <select value={d.giorno} onChange={e => updateDisp(i,"giorno",e.target.value)}
                  className="flex-1 px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] bg-white">
                  {GIORNI.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
                <input type="time" value={d.ora_inizio} onChange={e => updateDisp(i,"ora_inizio",e.target.value)}
                  className="w-28 px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                <span className="text-[#0A0A0A]/55 text-sm">→</span>
                <input type="time" value={d.ora_fine} onChange={e => updateDisp(i,"ora_fine",e.target.value)}
                  className="w-28 px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                <button type="button" onClick={() => removeDisponibilita(i)}
                  className="p-2 rounded-xl hover:bg-red-50 text-[#0A0A0A]/50 hover:text-red-600">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <button data-testid="save-profilo-btn" type="submit" disabled={saving}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg transition-colors disabled:opacity-50">
          <Save className="w-4 h-4" />
          {saving ? "Salvataggio..." : "Salva Profilo"}
        </button>
      </form>
    </div>
  );
}
