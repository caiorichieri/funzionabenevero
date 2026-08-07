import { sanitizeHtml } from "@/utils/safeHtml";
import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import LegalLayout from "@/components/public/LegalLayout";
import { TITOLARE } from "@/data/legalInfo";

/**
 * Public page showing the full text of the current "Mandato all'incasso con
 * Rappresentanza" contract signed by therapists on the platform. Useful for
 * patients who want to understand the legal role of BIDOC SRL.
 * Modelled after miodottore.it's public "Contratto Quadro".
 */
export default function MandatoLegalePage() {
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/contracts/current/mandato_all_incasso`)
      .then(r => setContract(r.data))
      .catch(() => setContract(null))
      .finally(() => setLoading(false));
  }, []);

  const lastUpdate = contract?.effective_date
    ? new Date(contract.effective_date).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" })
    : null;

  return (
    <LegalLayout
      title={contract?.title || "Mandato all'incasso"}
      lastUpdate={lastUpdate}
      testId="mandato-legale-page"
    >
      <div className="mb-8 p-5 rounded-2xl bg-white/40 border border-[#0A0A0A]/10">
        <p className="text-sm text-[#0A0A0A]/80 mb-0">
          Questa pagina riproduce il <strong>contratto quadro</strong> che regola il rapporto tra <strong>{TITOLARE.nome}</strong>
          {" "}(marchio <em>{TITOLARE.brand}</em>) e i professionisti sanitari che operano sulla piattaforma. Ogni terapeuta
          accetta questo mandato al momento del suo primo accesso — solo così può ricevere prenotazioni e pagamenti tramite {TITOLARE.brand}.
          {" "}Se sei un paziente, questa pagina ti spiega esattamente <strong>chi ti fornisce la prestazione sanitaria</strong>{" "}
          (il terapeuta, non {TITOLARE.brand}) e <strong>chi gestisce il pagamento per suo conto</strong> ({TITOLARE.nome}).
        </p>
      </div>

      {loading && (
        <div className="p-8 text-center text-[#0A0A0A]/55" data-testid="mandato-loading">
          Caricamento del testo del mandato…
        </div>
      )}

      {!loading && !contract && (
        <div className="p-6 bg-red-50 border border-red-200 rounded-2xl text-red-800 text-sm">
          Il contratto non è momentaneamente disponibile. Riprova più tardi o scrivici a
          {" "}<a href="mailto:info@funzionabene.it">info@funzionabene.it</a>.
        </div>
      )}

      {!loading && contract && (
        <>
          <div className="text-xs text-[#0A0A0A]/50 mb-4 flex flex-wrap gap-x-4 gap-y-1" data-testid="mandato-meta">
            <span>Versione: <strong>#{contract.version}</strong></span>
            <span>Hash SHA-256: <span className="font-mono text-[10px]">{contract.content_hash?.slice(0, 32)}…</span></span>
          </div>
          <div
            className="text-[#0A0A0A]/85"
            dangerouslySetInnerHTML={{ __html: sanitizeHtml(contract.content_html) }}
            data-testid="mandato-content-html"
          />
        </>
      )}

      <p className="mt-10 text-xs text-[#0A0A0A]/50 italic">
        Il presente testo è dinamico. Se il mandato viene aggiornato, la nuova versione appare qui e ogni terapeuta
        deve ri-accettarla al successivo accesso. Le versioni precedenti sono conservate immutabili come traccia legale.
      </p>
    </LegalLayout>
  );
}
