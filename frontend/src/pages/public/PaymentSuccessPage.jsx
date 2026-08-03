import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Check, Loader2, XCircle } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

const MAX_POLLS = 20;

export default function PaymentSuccessPage() {
  const [params] = useSearchParams();
  const session_id = params.get("session_id");
  const [state, setState] = useState({ status: "polling", attempts: 0, data: null });

  useEffect(() => {
    if (!session_id) {
      setState({ status: "error", attempts: 0, data: null });
      return;
    }
    let cancelled = false;
    let attempts = 0;
    const tick = async () => {
      if (cancelled) return;
      attempts += 1;
      try {
        const r = await axios.get(`${API}/payments/status/${session_id}`);
        if (r.data?.payment_status === "paid") {
          setState({ status: "paid", attempts, data: r.data });
          return;
        }
        if (["failed", "expired", "refunded"].includes(r.data?.payment_status)) {
          setState({ status: "failed", attempts, data: r.data });
          return;
        }
        if (attempts >= MAX_POLLS) {
          setState({ status: "timeout", attempts, data: r.data });
          return;
        }
        setState({ status: "polling", attempts, data: r.data });
        setTimeout(tick, 2000);
      } catch {
        if (attempts >= MAX_POLLS) {
          setState({ status: "timeout", attempts, data: null });
          return;
        }
        setTimeout(tick, 2500);
      }
    };
    tick();
    return () => { cancelled = true; };
  }, [session_id]);

  return (
    <main className="min-h-[70vh] flex items-center justify-center px-6 py-24" data-testid="payment-success-page">
      <div className="brand-card max-w-lg w-full text-center p-10">
        {state.status === "polling" && (
          <>
            <Loader2 className="w-10 h-10 text-[#F58A1F] mx-auto animate-spin" />
            <h1 className="font-serif text-2xl text-[#0A0A0A] mt-6">Stiamo confermando il tuo pagamento…</h1>
            <p className="text-[#0A0A0A]/65 mt-2 text-sm">
              Non chiudere questa pagina. Riceverai la conferma tra un istante.
            </p>
            <p className="text-[#0A0A0A]/40 mt-4 text-xs">Tentativo {state.attempts}/{MAX_POLLS}</p>
          </>
        )}

        {state.status === "paid" && (
          <>
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto">
              <Check className="w-8 h-8 text-green-600" strokeWidth={3} />
            </div>
            <h1 className="font-serif text-3xl text-[#0A0A0A] mt-6">Pagamento confermato</h1>
            <p className="text-[#0A0A0A]/70 mt-3">
              La tua sessione è prenotata. Ti abbiamo inviato la conferma via email con il link della videochiamata.
            </p>
            <div className="my-8 flex justify-center">
              <Mascotte name="abbraccio" theme="light" size={120} animation="breathe" />
            </div>
            <Link
              to="/paziente"
              className="inline-flex items-center justify-center rounded-full px-6 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-medium hover:opacity-90 transition"
              data-testid="go-to-dashboard-btn"
            >
              Vai alla tua area
            </Link>
          </>
        )}

        {state.status === "failed" && (
          <>
            <XCircle className="w-14 h-14 text-red-500 mx-auto" />
            <h1 className="font-serif text-2xl text-[#0A0A0A] mt-6">Pagamento non completato</h1>
            <p className="text-[#0A0A0A]/70 mt-3">
              Il pagamento non è andato a buon fine. Riprova o contattaci se il problema persiste.
            </p>
            <Link to="/" className="inline-block mt-6 text-[#F58A1F] hover:underline">Torna alla home</Link>
          </>
        )}

        {state.status === "timeout" && (
          <>
            <Loader2 className="w-10 h-10 text-[#0A0A0A]/40 mx-auto" />
            <h1 className="font-serif text-2xl text-[#0A0A0A] mt-6">Conferma in corso…</h1>
            <p className="text-[#0A0A0A]/70 mt-3">
              Il pagamento è stato registrato ma la conferma sta impiegando più tempo del previsto. Ti abbiamo comunque inviato una mail — controlla la tua casella.
            </p>
            <Link to="/paziente" className="inline-block mt-6 text-[#F58A1F] hover:underline">Vai alla tua area</Link>
          </>
        )}

        {state.status === "error" && (
          <>
            <XCircle className="w-14 h-14 text-red-500 mx-auto" />
            <h1 className="font-serif text-2xl text-[#0A0A0A] mt-6">Sessione non trovata</h1>
            <p className="text-[#0A0A0A]/70 mt-3">
              Non riusciamo a leggere l&apos;identificativo del pagamento.
            </p>
            <Link to="/" className="inline-block mt-6 text-[#F58A1F] hover:underline">Torna alla home</Link>
          </>
        )}
      </div>
    </main>
  );
}
