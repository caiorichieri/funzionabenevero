/**
 * Lightweight Yoast-style SEO analyzer for the admin blog editor.
 * Runs client-side on every keystroke. No dependencies.
 *
 * Usage:
 *   <BlogSeoAnalyzer titolo={...} contenuto={...} categoria={...} />
 */
import { useMemo, useState } from "react";
import { CheckCircle2, AlertCircle, XCircle, Search } from "lucide-react";

// ─── Analysis primitives ─────────────────────────────────────────────────
const stripHtml = (s = "") => s.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
const wordCount = (s = "") => (s.match(/\b[\p{L}]+\b/gu) || []).length;
const countMatches = (text, kw) => {
  if (!kw) return 0;
  const escaped = kw.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`\\b${escaped}\\b`, "gi");
  return (text.match(re) || []).length;
};

const STATUS_STYLES = {
  ok: { color: "text-green-700", icon: CheckCircle2, dot: "bg-green-500" },
  warn: { color: "text-amber-700", icon: AlertCircle, dot: "bg-amber-500" },
  bad: { color: "text-red-700", icon: XCircle, dot: "bg-red-500" },
};

function analyze({ titolo = "", contenuto = "", excerpt = "", keyword = "" }) {
  const plainContent = stripHtml(contenuto);
  const words = wordCount(plainContent);
  const kw = keyword.trim().toLowerCase();
  const kwWords = kw.split(/\s+/).filter(Boolean);

  const firstParagraph = (contenuto.match(/<p[^>]*>([\s\S]*?)<\/p>/i) || [null, plainContent.slice(0, 200)])[1];
  const firstParaText = stripHtml(firstParagraph).toLowerCase();

  const h2s = (contenuto.match(/<h2[^>]*>[\s\S]*?<\/h2>/gi) || []).map(stripHtml);
  const h3s = (contenuto.match(/<h3[^>]*>[\s\S]*?<\/h3>/gi) || []).length;
  const imgs = contenuto.match(/<img[^>]+>/gi) || [];
  const imgsWithAlt = imgs.filter((t) => /\balt\s*=\s*"([^"]+)"/i.test(t)).length;
  const links = (contenuto.match(/<a[^>]+href/gi) || []).length;
  const kwOccurrences = countMatches(plainContent, kw);
  const density = words > 0 ? (kwOccurrences / words) * 100 : 0;

  const checks = [];

  // ── Focus keyword group ────────────────────────────────────────────────
  if (!kw) {
    checks.push({ id: "kw-empty", status: "warn", weight: 0, label: 'Aggiungi una "focus keyword" per abilitare l\'analisi.' });
  } else {
    // 1) Keyword in title (weight 15)
    const inTitle = titolo.toLowerCase().includes(kw);
    checks.push({
      id: "kw-title",
      status: inTitle ? "ok" : "bad",
      weight: 15,
      score: inTitle ? 15 : 0,
      label: inTitle ? "La focus keyword è nel titolo." : "La focus keyword non è nel titolo.",
    });

    // 2) Keyword in first paragraph (weight 10)
    const inFirstPara = kwWords.every((w) => firstParaText.includes(w));
    checks.push({
      id: "kw-first-para",
      status: inFirstPara ? "ok" : "warn",
      weight: 10,
      score: inFirstPara ? 10 : 3,
      label: inFirstPara ? "La focus keyword è nel primo paragrafo." : "Prova a inserire la keyword nella prima frase.",
    });

    // 3) Keyword in at least one H2 (weight 10)
    const inH2 = h2s.some((h) => h.toLowerCase().includes(kw));
    checks.push({
      id: "kw-h2",
      status: inH2 ? "ok" : h2s.length ? "warn" : "bad",
      weight: 10,
      score: inH2 ? 10 : h2s.length ? 4 : 0,
      label: inH2
        ? "La focus keyword compare in un titolo H2."
        : h2s.length
        ? "Nessun H2 contiene la focus keyword."
        : "Nessun titolo H2 nel contenuto.",
    });

    // 4) Density 0.5% - 2.5% (weight 15)
    let densStatus = "bad", densScore = 0, densLabel = "";
    if (density >= 0.5 && density <= 2.5) {
      densStatus = "ok"; densScore = 15;
      densLabel = `Densità della keyword ottimale (${density.toFixed(1)}%).`;
    } else if (density > 0 && density < 0.5) {
      densStatus = "warn"; densScore = 6;
      densLabel = `Densità troppo bassa (${density.toFixed(1)}%). Aggiungi qualche menzione della keyword.`;
    } else if (density > 2.5) {
      densStatus = "warn"; densScore = 6;
      densLabel = `Densità troppo alta (${density.toFixed(1)}%). Sembra keyword-stuffing.`;
    } else {
      densLabel = "La focus keyword non compare mai nel contenuto.";
    }
    checks.push({ id: "kw-density", status: densStatus, weight: 15, score: densScore, label: densLabel });
  }

  // ── Length group ──────────────────────────────────────────────────────
  // 5) Title length 30-60 (weight 10)
  const tl = titolo.trim().length;
  let tStatus = "bad", tScore = 0, tLabel = "";
  if (tl >= 30 && tl <= 60) { tStatus = "ok"; tScore = 10; tLabel = `Lunghezza del titolo ottima (${tl} caratteri).`; }
  else if (tl >= 20 && tl < 30) { tStatus = "warn"; tScore = 5; tLabel = `Titolo un po' corto (${tl} caratteri). Meglio 30-60.`; }
  else if (tl > 60 && tl <= 75) { tStatus = "warn"; tScore = 5; tLabel = `Titolo un po' lungo (${tl}). Google può troncarlo dopo 60.`; }
  else if (tl > 75) { tStatus = "bad"; tScore = 2; tLabel = `Titolo troppo lungo (${tl}). Sarà troncato nei risultati.`; }
  else { tLabel = tl === 0 ? "Manca il titolo." : `Titolo troppo corto (${tl}).`; }
  checks.push({ id: "title-len", status: tStatus, weight: 10, score: tScore, label: tLabel });

  // 6) Meta description (excerpt or first paragraph) length 120-160 (weight 10)
  const desc = (excerpt && excerpt.trim()) || firstParaText.slice(0, 200);
  const dl = desc.length;
  let dStatus = "bad", dScore = 0, dLabel = "";
  if (dl >= 120 && dl <= 160) { dStatus = "ok"; dScore = 10; dLabel = `Meta description perfetta (${dl}).`; }
  else if (dl >= 80 && dl < 120) { dStatus = "warn"; dScore = 5; dLabel = `Meta description un po' corta (${dl}). Meglio 120-160.`; }
  else if (dl > 160 && dl <= 200) { dStatus = "warn"; dScore = 5; dLabel = `Meta description un po' lunga (${dl}).`; }
  else if (dl > 200) { dStatus = "bad"; dScore = 2; dLabel = `Meta description troppo lunga (${dl}).`; }
  else { dLabel = "Meta description troppo corta o mancante."; }
  checks.push({ id: "desc-len", status: dStatus, weight: 10, score: dScore, label: dLabel });

  // 7) Content length >= 300 words (weight 15)
  let wStatus = "bad", wScore = 0, wLabel = "";
  if (words >= 600) { wStatus = "ok"; wScore = 15; wLabel = `Ottima lunghezza (${words} parole).`; }
  else if (words >= 300) { wStatus = "ok"; wScore = 12; wLabel = `Buona lunghezza (${words} parole). Con 600+ ranki meglio.`; }
  else if (words >= 150) { wStatus = "warn"; wScore = 6; wLabel = `Contenuto un po' corto (${words} parole). Punta a 300+.`; }
  else { wLabel = `Contenuto troppo corto (${words} parole).`; }
  checks.push({ id: "content-len", status: wStatus, weight: 15, score: wScore, label: wLabel });

  // ── Structure group ──────────────────────────────────────────────────
  // 8) Headings (H2) present (weight 10)
  checks.push({
    id: "structure-h2",
    status: h2s.length >= 2 ? "ok" : h2s.length === 1 ? "warn" : "bad",
    weight: 10,
    score: h2s.length >= 2 ? 10 : h2s.length === 1 ? 5 : 0,
    label:
      h2s.length >= 2
        ? `Struttura chiara (${h2s.length} H2, ${h3s} H3).`
        : h2s.length === 1
        ? "Solo un H2. Prova ad aggiungerne almeno 2."
        : "Nessun titolo H2. Aggiungi sezioni per aiutare la lettura.",
  });

  // 9) At least one image with alt (weight 10)
  checks.push({
    id: "img-alt",
    status: imgsWithAlt >= 1 ? "ok" : imgs.length ? "warn" : "bad",
    weight: 10,
    score: imgsWithAlt >= 1 ? 10 : imgs.length ? 4 : 0,
    label:
      imgsWithAlt >= 1
        ? `${imgsWithAlt} immagine/i con alt text.`
        : imgs.length
        ? `${imgs.length} immagine/i ma senza attributo alt.`
        : "Aggiungi almeno un'immagine (con alt text descrittivo).",
  });

  // 10) At least one link (weight 5)
  checks.push({
    id: "links",
    status: links >= 1 ? "ok" : "warn",
    weight: 5,
    score: links >= 1 ? 5 : 0,
    label: links >= 1 ? `${links} link nel contenuto.` : "Nessun link. Aggiungine almeno uno (interno o esterno).",
  });

  const totalScore = checks.reduce((sum, c) => sum + (c.score || 0), 0);
  const maxScore = checks.reduce((sum, c) => sum + (c.weight || 0), 0);
  const pct = maxScore ? Math.round((totalScore / maxScore) * 100) : 0;

  return { checks, score: pct, words };
}

export default function BlogSeoAnalyzer({ titolo = "", contenuto = "", excerpt = "" }) {
  const [keyword, setKeyword] = useState("");
  const [expanded, setExpanded] = useState(true);

  const { checks, score, words } = useMemo(
    () => analyze({ titolo, contenuto, excerpt, keyword }),
    [titolo, contenuto, excerpt, keyword]
  );

  const scoreColor = score >= 70 ? "text-green-600" : score >= 50 ? "text-amber-600" : "text-red-600";
  const scoreBg = score >= 70 ? "bg-green-100" : score >= 50 ? "bg-amber-100" : "bg-red-100";
  const scoreLabel = score >= 70 ? "Ottimo" : score >= 50 ? "Da migliorare" : "Da rivedere";

  return (
    <div className="border border-[#0A0A0A]/10 rounded-2xl bg-white overflow-hidden" data-testid="seo-analyzer">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between p-4 hover:bg-[#0A0A0A]/5"
      >
        <div className="flex items-center gap-3">
          <div className={`w-11 h-11 rounded-full ${scoreBg} flex items-center justify-center ${scoreColor} font-bold`}>
            {score}
          </div>
          <div className="text-left">
            <div className="text-sm font-semibold text-[#0A0A0A]">SEO Score</div>
            <div className={`text-xs ${scoreColor}`}>{scoreLabel} · {words} parole</div>
          </div>
        </div>
        <span className="text-xs text-[#0A0A0A]/50">{expanded ? "Nascondi" : "Dettagli"}</span>
      </button>

      {expanded && (
        <div className="border-t border-[#0A0A0A]/10 p-4 space-y-3">
          <div>
            <label className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-1">Focus keyword</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#0A0A0A]/40" />
              <input
                data-testid="seo-focus-keyword"
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder='es. "disfunzione erettile"'
                className="w-full pl-9 pr-3 py-2 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
              />
            </div>
          </div>

          <ul className="space-y-1.5">
            {checks.map((c) => {
              const st = STATUS_STYLES[c.status] || STATUS_STYLES.warn;
              const Icon = st.icon;
              return (
                <li key={c.id} className="flex items-start gap-2 text-xs" data-testid={`seo-check-${c.id}`}>
                  <Icon className={`w-3.5 h-3.5 flex-shrink-0 mt-0.5 ${st.color}`} />
                  <span className="text-[#0A0A0A]/80 leading-snug">{c.label}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
