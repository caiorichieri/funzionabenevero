import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { CheckCircle, XCircle, Star, Clock, X } from "lucide-react";

function StarRow({ voto }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={`w-4 h-4 ${n <= voto ? "text-amber-500 fill-amber-500" : "text-[#0A0A0A]/20"}`}
        />
      ))}
      <span className="ml-2 text-sm font-semibold text-[#0A0A0A]">{voto}/5</span>
    </div>
  );
}

export default function AdminRecensioniPage() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rejectingId, setRejectingId] = useState(null);
  const [motivo, setMotivo] = useState("");
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    axios
      .get(`${API}/admin/reviews/pending`, { withCredentials: true })
      .then((r) => setReviews(r.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const approva = async (id) => {
    setBusyId(id);
    try {
      await axios.post(`${API}/admin/reviews/${id}/approve`, {}, { withCredentials: true });
      setReviews((prev) => prev.filter((r) => r.review_id !== id));
    } catch (e) {
      window.alert(e.response?.data?.detail || "Errore nell'approvazione");
    } finally {
      setBusyId(null);
    }
  };

  const openRifiuta = (id) => {
    setRejectingId(id);
    setMotivo("");
  };

  const confermaRifiuta = async () => {
    if (!rejectingId) return;
    setBusyId(rejectingId);
    try {
      await axios.post(
        `${API}/admin/reviews/${rejectingId}/reject`,
        { motivo },
        { withCredentials: true }
      );
      setReviews((prev) => prev.filter((r) => r.review_id !== rejectingId));
      setRejectingId(null);
      setMotivo("");
    } catch (e) {
      window.alert(e.response?.data?.detail || "Errore nel rifiuto");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div data-testid="admin-recensioni-page" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Recensioni</h1>
          <p className="text-[#0A0A0A]/65 mt-1">
            Modera le recensioni lasciate dai pazienti prima della pubblicazione sui profili dei terapisti.
          </p>
        </div>
      </div>

      {/* Alert conteggio */}
      {!loading && reviews.length > 0 && (
        <div
          data-testid="alert-pending-count"
          className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center gap-3"
        >
          <Clock className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <span className="text-amber-800 text-sm font-medium">
            {reviews.length}{" "}
            {reviews.length === 1 ? "recensione in attesa" : "recensioni in attesa"} di
            moderazione
          </span>
        </div>
      )}

      {/* Lista */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : reviews.length === 0 ? (
        <div
          data-testid="empty-state"
          className="text-center py-16 text-[#0A0A0A]/50 bg-white border border-[#0A0A0A]/10 rounded-2xl"
        >
          <CheckCircle className="w-10 h-10 mx-auto mb-3 text-green-500" />
          <div className="font-semibold text-[#0A0A0A]">Nessuna recensione in attesa</div>
          <div className="text-sm mt-1">Tutte le recensioni sono state moderate.</div>
        </div>
      ) : (
        <div className="space-y-3">
          {reviews.map((r) => (
            <div
              key={r.review_id}
              data-testid={`review-${r.review_id}`}
              className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-5 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap mb-2">
                    <StarRow voto={r.voto || 0} />
                    <span className="text-xs text-[#0A0A0A]/55">
                      {new Date(r.created_at).toLocaleString("it-IT", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>

                  <div className="text-sm text-[#0A0A0A]/70 mb-2">
                    <span>
                      Da <strong>{r.paziente?.nome || "Paziente"}</strong>{" "}
                      <span className="text-[#0A0A0A]/45">({r.paziente?.email})</span>
                    </span>
                    <span className="mx-2">·</span>
                    <span>
                      Per{" "}
                      <strong>
                        {r.terapista?.nome} {r.terapista?.cognome}
                      </strong>
                    </span>
                  </div>

                  {r.testo ? (
                    <p className="text-sm text-[#0A0A0A] leading-relaxed whitespace-pre-wrap bg-[#F8F5F0]/60 border border-[#0A0A0A]/5 rounded-xl p-3">
                      {r.testo}
                    </p>
                  ) : (
                    <p className="text-sm text-[#0A0A0A]/45 italic">
                      (Nessun testo, solo valutazione)
                    </p>
                  )}
                </div>

                {/* Azioni */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    data-testid={`btn-rifiuta-${r.review_id}`}
                    onClick={() => openRifiuta(r.review_id)}
                    disabled={busyId === r.review_id}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-red-200 text-red-600 hover:bg-red-50 text-sm font-medium disabled:opacity-50"
                    title="Rifiuta"
                  >
                    <XCircle className="w-4 h-4" /> Rifiuta
                  </button>
                  <button
                    data-testid={`btn-approva-${r.review_id}`}
                    onClick={() => approva(r.review_id)}
                    disabled={busyId === r.review_id}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-600 hover:bg-green-700 text-white text-sm font-medium disabled:opacity-50"
                    title="Approva e pubblica"
                  >
                    <CheckCircle className="w-4 h-4" /> Approva
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Rifiuta */}
      {rejectingId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div
            data-testid="modal-rifiuta"
            className="bg-white rounded-2xl shadow-xl w-full max-w-md"
          >
            <div className="flex items-center justify-between p-6 border-b border-[#0A0A0A]/10">
              <h2 className="text-lg font-bold text-[#0A0A0A] font-[Outfit]">
                Rifiuta recensione
              </h2>
              <button
                onClick={() => setRejectingId(null)}
                className="p-2 rounded-xl hover:bg-[#0A0A0A]/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-[#0A0A0A]/70">
                Indica un motivo (facoltativo) per il rifiuto. Non sarà visibile al paziente ma
                verrà registrato per audit.
              </p>
              <textarea
                data-testid="input-motivo-rifiuto"
                value={motivo}
                onChange={(e) => setMotivo(e.target.value.slice(0, 400))}
                rows={4}
                placeholder="Es. contenuto offensivo, spam, non pertinente..."
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] resize-none"
              />
              <div className="text-xs text-[#0A0A0A]/45 text-right">{motivo.length}/400</div>
            </div>
            <div className="flex justify-end gap-3 p-6 border-t border-[#0A0A0A]/10">
              <button
                onClick={() => setRejectingId(null)}
                className="px-5 py-2.5 border border-[#0A0A0A]/15 rounded-full text-[#0A0A0A] hover:bg-[#0A0A0A]/5"
              >
                Annulla
              </button>
              <button
                data-testid="btn-conferma-rifiuto"
                onClick={confermaRifiuta}
                disabled={busyId === rejectingId}
                className="px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-full font-medium disabled:opacity-50 inline-flex items-center gap-2"
              >
                <XCircle className="w-4 h-4" /> Conferma rifiuto
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
