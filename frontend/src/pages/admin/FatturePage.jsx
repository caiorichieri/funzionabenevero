import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Download, FileText, Search, RefreshCw, Play, Loader2 } from "lucide-react";

const KIND_LABELS = { sanitaria: "Sanitaria (paziente)", commissione: "Commissione B2B" };
const KIND_COLORS = {
  sanitaria: "bg-blue-50 text-blue-700 border-blue-200",
  commissione: "bg-orange-50 text-orange-700 border-orange-200",
};

/**
 * Admin Cassetto Fiscale — vista completa di tutte le fatture emesse dalla
 * piattaforma (sia sanitarie in nome dei terapeuti che commissioni BIDOC).
 * `/admin/fatture` accessibile solo da role=admin.
 *
 * `isAdmin=false` prop → mostra vista terapeuta (mine only).
 */
export default function FatturePage({ isAdmin = true }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterKind, setFilterKind] = useState("");
  const [search, setSearch] = useState("");
  const [busyJob, setBusyJob] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const url = isAdmin
        ? `${API}/admin/fatture${filterKind ? `?kind=${filterKind}` : ""}`
        : `${API}/fatture/mine`;
      const r = await axios.get(url, { withCredentials: true });
      setItems(r.data?.items || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterKind, isAdmin]);

  const runJob = async (endpoint, label) => {
    if (!confirm(`Esegui: ${label}?`)) return;
    setBusyJob(endpoint);
    try {
      const r = await axios.post(`${API}${endpoint}`, {}, { withCredentials: true });
      alert(`OK: ${JSON.stringify(r.data).slice(0, 200)}`);
      await load();
    } catch (e) {
      alert(`Errore: ${e.response?.data?.detail || e.message}`);
    } finally { setBusyJob(null); }
  };

  const filtered = search
    ? items.filter(i => (i.numero || "").toLowerCase().includes(search.toLowerCase()))
    : items;

  const totals = filtered.reduce((acc, f) => {
    acc[f.kind] = (acc[f.kind] || 0) + (f.importo_totale || 0);
    return acc;
  }, {});

  const exportCsv = () => {
    const header = ["Numero", "Tipo", "Data", "Imponibile", "IVA%", "IVA €", "Totale €", "Bollo", "Terapeuta ID", "Anno Rif", "Mese Rif"];
    const rows = filtered.map(f => [
      f.numero, f.kind, f.data, f.importo_imponibile, f.aliquota_iva,
      f.importo_iva, f.importo_totale, f.marca_bollo ? "Sì" : "No",
      f.terapeuta_user_id, f.anno_riferimento || "", f.mese_riferimento || "",
    ]);
    const csv = [header, ...rows].map(r => r.map(v => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url;
    a.download = `fatture_export_${new Date().toISOString().split("T")[0]}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6" data-testid="admin-fatture-page">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#0A0A0A] font-[Outfit]">
            {isAdmin ? "Cassetto Fiscale (Admin)" : "Le mie fatture"}
          </h1>
          <p className="text-[#0A0A0A]/65 mt-1 text-sm">
            {isAdmin
              ? "Tutte le fatture emesse dalla piattaforma. Le sanitarie sono in nome del terapeuta, le commissioni B2B sono emesse da BIDOC SRL."
              : "Fatture emesse ai tuoi pazienti + fatture di commissione ricevute da BIDOC."
            }
          </p>
        </div>
        {isAdmin && (
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => runJob("/api/admin/jobs/weekly-fatture/run", "Invia riepilogo settimanale ai terapeuti")}
              disabled={busyJob !== null}
              data-testid="run-weekly-btn"
              className="px-3 py-2 border border-[#0A0A0A]/15 rounded-full text-xs hover:bg-[#0A0A0A]/5 inline-flex items-center gap-1.5"
            >
              {busyJob === "/api/admin/jobs/weekly-fatture/run" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              Invia email settimanale
            </button>
            <button
              onClick={() => runJob("/api/admin/jobs/monthly-commissioni/run", "Genera commissioni B2B del mese precedente")}
              disabled={busyJob !== null}
              data-testid="run-monthly-btn"
              className="px-3 py-2 border border-[#0A0A0A]/15 rounded-full text-xs hover:bg-[#0A0A0A]/5 inline-flex items-center gap-1.5"
            >
              {busyJob === "/api/admin/jobs/monthly-commissioni/run" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              Genera commissioni mensili
            </button>
          </div>
        )}
      </div>

      {/* Banner detrazione 730 — solo per paziente (isAdmin=false) */}
      {!isAdmin && (
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-2xl p-4 flex items-start gap-3" data-testid="banner-detrazione-730">
          <span className="text-2xl">💚</span>
          <div className="text-sm text-green-900">
            <div className="font-semibold mb-1">Detraibile al 730 come spesa sanitaria</div>
            <div className="text-green-800/85 leading-relaxed">
              Queste fatture per prestazioni psicologiche sono detraibili al <strong>19%</strong> dell&apos;importo nella tua dichiarazione dei redditi
              (art. 15 TUIR — Spese sanitarie). Conservale per almeno 5 anni. Il tuo terapeuta le trasmetterà al Sistema TS per l&apos;inserimento automatico nel 730 precompilato.
            </div>
          </div>
        </div>
      )}

      {/* Filters + KPI */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="col-span-2 flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/40" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Cerca per numero (es. FZ-2026-0001)"
              data-testid="fatture-search"
              className="w-full pl-9 pr-3 py-2 border border-[#0A0A0A]/15 rounded-full text-sm"
            />
          </div>
          {isAdmin && (
            <select
              value={filterKind}
              onChange={e => setFilterKind(e.target.value)}
              data-testid="fatture-filter-kind"
              className="px-3 py-2 border border-[#0A0A0A]/15 rounded-full text-sm bg-white"
            >
              <option value="">Tutti i tipi</option>
              <option value="sanitaria">Sanitaria</option>
              <option value="commissione">Commissione B2B</option>
            </select>
          )}
          <button onClick={load} className="px-3 py-2 border border-[#0A0A0A]/15 rounded-full text-sm hover:bg-[#0A0A0A]/5">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        <div className="bg-blue-50 rounded-xl p-3 border border-blue-100">
          <div className="text-xs text-blue-700">Totale Sanitarie</div>
          <div className="text-lg font-bold text-blue-900">€ {(totals.sanitaria || 0).toFixed(2)}</div>
        </div>
        <div className="bg-orange-50 rounded-xl p-3 border border-orange-100">
          <div className="text-xs text-orange-700">Totale Commissioni BIDOC</div>
          <div className="text-lg font-bold text-orange-900">€ {(totals.commissione || 0).toFixed(2)}</div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-[#0A0A0A]/60">{filtered.length} fatture</div>
        <button
          onClick={exportCsv}
          disabled={!filtered.length}
          data-testid="export-csv-btn"
          className="px-3 py-1.5 text-xs border border-[#0A0A0A]/15 rounded-full hover:bg-[#0A0A0A]/5 inline-flex items-center gap-1.5"
        >
          <Download className="w-3.5 h-3.5" /> Export CSV
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-[#0A0A0A]/10 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-[#0A0A0A]/55"><Loader2 className="w-6 h-6 animate-spin inline-block" /></div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-[#0A0A0A]/55" data-testid="fatture-empty">
            Nessuna fattura da mostrare.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#0A0A0A]/[0.03] border-b border-[#0A0A0A]/10">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-[#0A0A0A]/70">Numero</th>
                  <th className="text-left px-4 py-3 font-medium text-[#0A0A0A]/70">Tipo</th>
                  <th className="text-left px-4 py-3 font-medium text-[#0A0A0A]/70">Data</th>
                  <th className="text-right px-4 py-3 font-medium text-[#0A0A0A]/70">Imponibile</th>
                  <th className="text-right px-4 py-3 font-medium text-[#0A0A0A]/70">IVA</th>
                  <th className="text-right px-4 py-3 font-medium text-[#0A0A0A]/70">Totale</th>
                  <th className="text-center px-4 py-3 font-medium text-[#0A0A0A]/70">Bollo</th>
                  <th className="text-center px-4 py-3 font-medium text-[#0A0A0A]/70">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#0A0A0A]/5">
                {filtered.map(f => (
                  <tr key={f.id} className="hover:bg-[#0A0A0A]/[0.02]" data-testid={`fattura-row-${f.numero}`}>
                    <td className="px-4 py-3 font-mono text-xs">{f.numero}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium border ${KIND_COLORS[f.kind]}`}>
                        {KIND_LABELS[f.kind]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#0A0A0A]/70">{f.data}</td>
                    <td className="px-4 py-3 text-right">€ {(f.importo_imponibile || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 text-right text-[#0A0A0A]/60">
                      {f.aliquota_iva > 0 ? `€ ${(f.importo_iva || 0).toFixed(2)}` : "esente"}
                    </td>
                    <td className="px-4 py-3 text-right font-medium">€ {(f.importo_totale || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 text-center text-xs">{f.marca_bollo ? "€2" : "—"}</td>
                    <td className="px-4 py-3 text-center">
                      <div className="inline-flex gap-1">
                        {f.has_xml && (
                          <a href={`${API}/fatture/${f.id}/xml`}
                             data-testid={`download-xml-${f.numero}`}
                             className="p-1.5 hover:bg-[#0A0A0A]/5 rounded" title="Scarica XML">
                            <FileText className="w-4 h-4 text-blue-600" />
                          </a>
                        )}
                        {f.has_pdf && (
                          <a href={`${API}/fatture/${f.id}/pdf`}
                             data-testid={`download-pdf-${f.numero}`}
                             className="p-1.5 hover:bg-[#0A0A0A]/5 rounded" title="Scarica PDF">
                            <Download className="w-4 h-4 text-[#F58A1F]" />
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
