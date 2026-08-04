import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import {
  Users, UserCheck, Calendar, AlertTriangle, FileText, ShieldX,
  Euro, Wallet, TrendingUp, TrendingDown, Award, CreditCard
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const eur = (cents) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format((cents || 0) / 100);

function StatCard({ icon: Icon, label, value, color, sub, testId }) {
  return (
    <div data-testid={testId} className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[#0A0A0A]/55 text-sm font-medium">{label}</span>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">{value ?? "—"}</div>
      {sub && <div className="text-xs text-[#0A0A0A]/55 mt-1">{sub}</div>}
    </div>
  );
}

function DeltaBadge({ percent }) {
  if (percent == null) return <span className="text-xs text-[#0A0A0A]/45">vs mese scorso: n/d</span>;
  const positive = percent >= 0;
  const Icon = positive ? TrendingUp : TrendingDown;
  return (
    <span className={`text-xs font-medium inline-flex items-center gap-1 ${positive ? "text-green-700" : "text-red-700"}`}>
      <Icon className="w-3 h-3" />
      {positive ? "+" : ""}{percent}% vs mese scorso
    </span>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [cruscotto, setCruscotto] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([
        axios.get(`${API}/dashboard/stats`, { withCredentials: true }),
        axios.get(`${API}/admin/cruscotto`, { withCredentials: true }),
      ]);
      setStats(s.data);
      setCruscotto(c.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const currentRev = cruscotto?.revenue?.current_month?.gross_cents || 0;
  const pending = cruscotto?.pending_payouts || { total_cents: 0, count: 0 };
  const sess = cruscotto?.sessions_month || { completed: 0, booked: 0, completion_rate: 0 };
  const chartData = (cruscotto?.revenue_6m || []).map(m => ({
    label: m.label,
    ricavi: Math.round((m.gross_cents || 0) / 100),
    sessioni: m.count,
  }));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Cruscotto</h1>
        <p className="text-[#0A0A0A]/65 mt-1">Panoramica esecutiva — FunzionaBene</p>
      </div>

      {/* Executive KPIs */}
      <div data-testid="cruscotto-kpis" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div data-testid="kpi-fatturato-mese" className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[#0A0A0A]/55 text-sm font-medium">Fatturato Mese</span>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-green-100 text-green-700">
              <Euro className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">{eur(currentRev)}</div>
          <div className="mt-1"><DeltaBadge percent={cruscotto?.revenue?.delta_percent} /></div>
        </div>

        <StatCard
          testId="kpi-payout-pendenti"
          icon={Wallet}
          label="Payout Pendenti"
          value={eur(pending.total_cents)}
          color="bg-orange-100 text-orange-700"
          sub={`${pending.count} transazioni da bonificare (70%)`}
        />

        <StatCard
          testId="kpi-sessioni-mese"
          icon={Calendar}
          label="Sessioni Mese"
          value={`${sess.completed} / ${sess.booked}`}
          color="bg-[#6B8FA3]/10 text-[#6B8FA3]"
          sub={`Tasso completamento: ${sess.completion_rate}%`}
        />

        <StatCard
          testId="kpi-terapisti-attivi"
          icon={UserCheck}
          label="Terapisti Attivi"
          value={stats?.terapisti}
          color="bg-white/30 text-[#0A0A0A]"
          sub={`${stats?.pazienti ?? 0} pazienti totali`}
        />
      </div>

      {/* Revenue chart + Top therapists */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div data-testid="chart-ricavi-6m" className="lg:col-span-2 bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[#0A0A0A] font-[Outfit]">Ricavi Ultimi 6 Mesi</h3>
            <span className="text-xs text-[#0A0A0A]/55">in € (incassi lordi)</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(10,10,10,0.08)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#0A0A0A99" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: "#0A0A0A99" }} axisLine={false} tickLine={false} />
              <Tooltip
                formatter={(v, name) => name === "ricavi" ? [`€ ${v}`, "Ricavi"] : [v, "Sessioni"]}
                contentStyle={{ borderRadius: 12, border: "1px solid rgba(10,10,10,0.1)", fontSize: 12 }}
              />
              <Bar dataKey="ricavi" fill="#6B8FA3" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div data-testid="top-terapisti" className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4 flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-500" />
            Top 5 Terapisti
          </h3>
          {(cruscotto?.top_therapists || []).length === 0 ? (
            <div className="text-sm text-[#0A0A0A]/55">Nessun dato disponibile.</div>
          ) : (
            <ol className="space-y-3">
              {cruscotto.top_therapists.map((t, i) => (
                <li key={t.terapeuta_id} className="flex items-center justify-between py-2 border-b border-[rgba(28,28,28,0.06)] last:border-0">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-full bg-[#0A0A0A]/5 flex items-center justify-center text-xs font-semibold">{i + 1}</div>
                    <div>
                      <div className="text-sm font-medium text-[#0A0A0A]">{t.nome}</div>
                      <div className="text-xs text-[#0A0A0A]/55">{t.sessions} sessioni</div>
                    </div>
                  </div>
                  <div className="text-sm font-semibold text-[#0A0A0A]">{eur(t.gross_cents)}</div>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>

      {/* IBAN missing alert */}
      {(cruscotto?.iban_missing || []).length > 0 && (
        <div data-testid="alert-iban-mancante" className="bg-red-50 border border-red-200 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-red-800 font-[Outfit] mb-3 flex items-center gap-2">
            <CreditCard className="w-5 h-5" />
            IBAN Mancante — {cruscotto.iban_missing.length} terapist{cruscotto.iban_missing.length === 1 ? "a" : "i"}
          </h3>
          <p className="text-sm text-red-700 mb-4">Questi professionisti hanno sessioni pagate ma non hanno un IBAN registrato. Non è possibile procedere al bonifico del 70%.</p>
          <div className="space-y-2">
            {cruscotto.iban_missing.map(t => (
              <div key={t.terapeuta_id} className="flex items-center justify-between py-2 border-b border-red-200 last:border-0">
                <div>
                  <div className="text-sm font-medium text-red-900">{t.nome}</div>
                  <div className="text-xs text-red-700">{t.sessions} sessioni · {eur(t.pending_cents)} da bonificare</div>
                </div>
                <a href="/admin/terapisti" className="text-xs font-semibold text-red-800 underline hover:no-underline">Aggiungi IBAN</a>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Operational alerts (existing) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {stats?.articoli_in_revisione > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-start gap-4">
            <FileText className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-amber-800">{stats.articoli_in_revisione} articoli in attesa di approvazione</div>
              <div className="text-sm text-amber-600 mt-1">Accedi alla sezione Blog per revisionarli</div>
            </div>
          </div>
        )}
        {stats?.terapisti_senza_autocertificazione > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-5 flex items-start gap-4">
            <ShieldX className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-red-800">{stats.terapisti_senza_autocertificazione} terapisti senza autocertificazione</div>
              <div className="text-sm text-red-600 mt-1">Richiedi la firma dell&apos;autocertificazione</div>
            </div>
          </div>
        )}
        {stats?.terapisti_pendenti > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-2xl p-5 flex items-start gap-4">
            <AlertTriangle className="w-6 h-6 text-orange-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-orange-800">{stats.terapisti_pendenti} terapisti in attesa di approvazione</div>
              <div className="text-sm text-orange-600 mt-1">Accedi a Terapisti per approvarli</div>
            </div>
          </div>
        )}
      </div>

      {/* Insurance expiry alerts */}
      {stats?.scadenze_assicurazione?.length > 0 && (
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            Scadenze Assicurazione in Arrivo
          </h3>
          <div className="space-y-3">
            {stats.scadenze_assicurazione.map((s) => (
              <div key={`${s.terapeuta}-${s.scadenza}`} className="flex items-center justify-between py-2 border-b border-[rgba(28,28,28,0.06)] last:border-0">
                <div>
                  <div className="font-medium text-[#0A0A0A] text-sm">{s.terapeuta}</div>
                  <div className="text-xs text-[#0A0A0A]/55">Scade: {new Date(s.scadenza).toLocaleDateString("it-IT")}</div>
                </div>
                <span className={`text-xs font-semibold px-3 py-1 rounded-full ${
                  s.giorni_rimanenti < 0 ? "bg-red-100 text-red-700" :
                  s.giorni_rimanenti < 30 ? "bg-red-100 text-red-700" :
                  "bg-orange-100 text-orange-700"
                }`}>
                  {s.giorni_rimanenti < 0 ? "SCADUTA" : `${s.giorni_rimanenti} giorni`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
        <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4">Azioni Rapide</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Gestione Terapisti", href: "/admin/terapisti", color: "bg-white/30 text-[#0A0A0A]" },
            { label: "Pagamenti & Payout", href: "/admin/pagamenti", color: "bg-green-100 text-green-700" },
            { label: "Nuovo Appuntamento", href: "/admin/appuntamenti", color: "bg-[#6B8FA3]/10 text-[#6B8FA3]" },
            { label: "Rivedi Blog", href: "/admin/blog", color: "bg-purple-100 text-purple-700" },
          ].map(action => (
            <a key={action.label} href={action.href}
              data-testid={`quick-action-${action.href.split("/").pop()}`}
              className={`${action.color} rounded-xl p-4 text-sm font-medium text-center hover:opacity-80 transition-opacity cursor-pointer`}>
              {action.label}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
