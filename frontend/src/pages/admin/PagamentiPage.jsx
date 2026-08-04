import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Wallet, Download, Check, Euro, Users, FileText, Loader2, RotateCcw } from "lucide-react";
import { toast } from "sonner";

const eur = (cents) => `€ ${((cents || 0) / 100).toFixed(2).replace(".", ",")}`;

const STATUS_BADGE = {
  pending: "bg-amber-100 text-amber-800",
  paid: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

export default function PagamentiPage() {
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());
  const [filter, setFilter] = useState("pending"); // pending | paid | ""
  const [bonificoRef, setBonificoRef] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const apiBase = API;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const q = filter ? `?payout_status=${filter}` : "";
      const r = await axios.get(`${apiBase}/admin/payouts${q}`, { withCredentials: true });
      setItems(r.data.items || []);
      setSummary(r.data.summary || []);
      setSelected(new Set());
    } catch (e) {
      setError("Impossibile caricare i pagamenti.");
    } finally {
      setLoading(false);
    }
  }, [filter, apiBase]);

  useEffect(() => { load(); }, [load]);

  const toggle = (id) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  const selectableItems = items.filter(i => i.payout_status === "pending");
  const allSelected = selectableItems.length > 0 && selectableItems.every(i => selected.has(i.id));
  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(selectableItems.map(i => i.id)));
  };

  const markPaid = async () => {
    if (selected.size === 0) return;
    setSaving(true);
    setError("");
    try {
      await axios.post(`${apiBase}/admin/payouts/mark-paid`, {
        transaction_ids: [...selected],
        payout_reference: bonificoRef.trim() || null,
      }, { withCredentials: true });
      setBonificoRef("");
      await load();
    } catch (e) {
      setError("Errore nel salvataggio. Verifica i permessi admin.");
    } finally {
      setSaving(false);
    }
  };

  const downloadPdf = (url, filename) => {
    // open in new tab; backend returns Content-Disposition: inline
    window.open(`${apiBase}${url}`, "_blank");
  };

  const refund = async (transactionId) => {
    const nota = window.prompt(
      "Motivo del rimborso (visibile solo internamente):",
      "",
    );
    if (nota === null) return; // cancelled
    if (!window.confirm(
      "⚠️ Confermi il rimborso? L'importo verrà restituito sulla carta del paziente e l'appuntamento sarà cancellato. Operazione irreversibile."
    )) return;
    try {
      await axios.post(`${apiBase}/admin/refunds`, {
        transaction_id: transactionId,
        reason: "requested_by_customer",
        admin_note: nota || "",
      }, { withCredentials: true });
      toast.success("Rimborso eseguito con successo");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Errore durante il rimborso");
    }
  };

  const now = new Date();
  const currentMonth = now.getMonth() + 1;
  const currentYear = now.getFullYear();

  return (
    <div className="space-y-8" data-testid="admin-pagamenti-page">
      <div>
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Pagamenti & Fatture</h1>
        <p className="text-[#0A0A0A]/65 mt-1">
          Gestisci i bonifici ai terapeuti (70% delle sessioni pagate) e scarica le fatture (sanitarie + di commissione).
        </p>
      </div>

      {/* Summary per therapist */}
      {summary.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="brand-card p-5">
            <div className="flex items-center gap-2 text-[#0A0A0A]/55 text-xs uppercase tracking-widest mb-2">
              <Euro className="w-4 h-4" /> Da pagare (tot.)
            </div>
            <div className="font-serif text-3xl text-[#0A0A0A]">
              {eur(summary.reduce((s, r) => s + r.pending_amount, 0))}
            </div>
          </div>
          <div className="brand-card p-5">
            <div className="flex items-center gap-2 text-[#0A0A0A]/55 text-xs uppercase tracking-widest mb-2">
              <Check className="w-4 h-4" /> Già pagato
            </div>
            <div className="font-serif text-3xl text-[#0A0A0A]">
              {eur(summary.reduce((s, r) => s + r.paid_amount, 0))}
            </div>
          </div>
          <div className="brand-card p-5">
            <div className="flex items-center gap-2 text-[#0A0A0A]/55 text-xs uppercase tracking-widest mb-2">
              <Users className="w-4 h-4" /> Terapeuti
            </div>
            <div className="font-serif text-3xl text-[#0A0A0A]">{summary.length}</div>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex items-center gap-2 border-b border-[#0A0A0A]/10 pb-2">
        {[
          ["pending", "Da pagare"],
          ["paid", "Pagati"],
          ["", "Tutti"],
        ].map(([val, lbl]) => (
          <button
            key={val || "all"}
            data-testid={`filter-${val || "all"}`}
            onClick={() => setFilter(val)}
            className={`px-4 py-2 text-sm rounded-full transition-colors ${
              filter === val ? "bg-[#0A0A0A] text-white" : "text-[#0A0A0A]/65 hover:bg-[#0A0A0A]/5"
            }`}
          >{lbl}</button>
        ))}
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-800">{error}</div>
      )}

      {/* Bulk action bar */}
      {filter === "pending" && selectableItems.length > 0 && (
        <div className="brand-card p-4 flex flex-col sm:flex-row items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-[#0A0A0A]/75">
            <input type="checkbox" checked={allSelected} onChange={toggleAll} data-testid="select-all-check"/>
            Seleziona tutti ({selectableItems.length})
          </label>
          <input
            data-testid="bonifico-ref-input"
            type="text"
            placeholder="Riferimento bonifico (opzionale)"
            value={bonificoRef}
            onChange={(e) => setBonificoRef(e.target.value)}
            className="flex-1 px-3 py-2 border border-[#0A0A0A]/15 rounded-xl text-sm"
          />
          <button
            data-testid="mark-paid-btn"
            onClick={markPaid}
            disabled={saving || selected.size === 0}
            className="px-5 py-2.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-medium rounded-full text-sm disabled:opacity-40 inline-flex items-center gap-2"
          >
            <Check className="w-4 h-4" /> Segna {selected.size} pagati
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-2xl border border-[#0A0A0A]/10 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-[#0A0A0A]/60"><Loader2 className="w-6 h-6 mx-auto animate-spin"/></div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-[#0A0A0A]/55">
            <Wallet className="w-10 h-10 mx-auto opacity-40" />
            <p className="mt-3 text-sm">Nessuna transazione in questa vista.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-[#0A0A0A]/[0.03] text-[#0A0A0A]/60 text-xs uppercase tracking-widest">
              <tr>
                <th className="p-3 w-8"></th>
                <th className="p-3 text-left">Data pagamento</th>
                <th className="p-3 text-left">Terapeuta</th>
                <th className="p-3 text-left">Paziente</th>
                <th className="p-3 text-right">Lordo</th>
                <th className="p-3 text-right">Commissione</th>
                <th className="p-3 text-right">Al terapeuta</th>
                <th className="p-3 text-center">Stato</th>
                <th className="p-3 text-right">Fattura</th>
              </tr>
            </thead>
            <tbody>
              {items.map(it => (
                <tr key={it.id} className="border-t border-[#0A0A0A]/10 hover:bg-[#0A0A0A]/[0.02]">
                  <td className="p-3">
                    {it.payout_status === "pending" && (
                      <input type="checkbox" checked={selected.has(it.id)} onChange={() => toggle(it.id)} data-testid={`select-${it.id}`}/>
                    )}
                  </td>
                  <td className="p-3">{it.paid_at ? new Date(it.paid_at).toLocaleDateString("it-IT") : "—"}</td>
                  <td className="p-3">Dr. {it.terapeuta.nome} {it.terapeuta.cognome}</td>
                  <td className="p-3">{it.paziente_initials}</td>
                  <td className="p-3 text-right">{eur(it.amount)}</td>
                  <td className="p-3 text-right text-[#0A0A0A]/70">{eur(it.platform_fee_amount)}</td>
                  <td className="p-3 text-right font-semibold">{eur(it.therapist_amount)}</td>
                  <td className="p-3 text-center">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${STATUS_BADGE[it.payout_status] || "bg-gray-100"}`}>
                      {it.payout_status === "paid" ? "Pagato" : "In attesa"}
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex items-center gap-2 justify-end">
                      <button
                        data-testid={`fs-btn-${it.id}`}
                        onClick={() => downloadPdf(`/admin/fattura-sanitaria/${it.id}`, `fattura-sanitaria-${it.id.slice(0,8)}.pdf`)}
                        className="inline-flex items-center gap-1 text-xs text-[#F58A1F] hover:underline"
                        title="Fattura sanitaria (paziente)"
                      >
                        <FileText className="w-3.5 h-3.5" /> Sanitaria
                      </button>
                      {it.payout_status === "pending" && (
                        <button
                          data-testid={`refund-btn-${it.id}`}
                          onClick={() => refund(it.id)}
                          className="inline-flex items-center gap-1 text-xs text-red-600 hover:underline"
                          title="Rimborsa (annulla la sessione e restituisce al paziente)"
                        >
                          <RotateCcw className="w-3.5 h-3.5" /> Rimborsa
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Monthly commission invoices per therapist */}
      {summary.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#0A0A0A]/10 p-5">
          <h3 className="text-lg font-semibold text-[#0A0A0A] mb-3">Fatture di commissione mensile</h3>
          <p className="text-xs text-[#0A0A0A]/55 mb-4">
            Genera la fattura di commissione BIDOC → terapeuta per il mese corrente ({currentMonth}/{currentYear}).
            IVA al 22%. Emessa ex art. 21 DPR 633/72.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {summary.map(s => (
              <div key={s.terapeuta.id} className="border border-[#0A0A0A]/10 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <div className="font-medium">Dr. {s.terapeuta.nome} {s.terapeuta.cognome}</div>
                  <div className="text-xs text-[#0A0A0A]/55">{s.sessions_count} sessioni</div>
                </div>
                <button
                  data-testid={`fc-btn-${s.terapeuta.id}`}
                  onClick={() => downloadPdf(`/admin/fattura-commissione/${s.terapeuta.id}/${currentYear}/${currentMonth}`, `fattura-commissione.pdf`)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#0A0A0A] text-white text-xs rounded-full hover:opacity-90"
                >
                  <Download className="w-3.5 h-3.5" /> PDF
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
