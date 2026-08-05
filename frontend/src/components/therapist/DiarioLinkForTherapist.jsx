import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { BookHeart } from "lucide-react";

/**
 * Compact link for the therapist to jump to a patient's diario emozionale.
 * Shows an unread-count badge when there are new notes.
 */
export default function DiarioLinkForTherapist({ pazienteId }) {
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!pazienteId) return;
    let cancelled = false;
    axios
      .get(`${API}/diario/paziente/${pazienteId}/count`, { withCredentials: true })
      .then((r) => { if (!cancelled) setUnread(r.data?.unread || 0); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [pazienteId]);

  return (
    <Link
      to={`/terapeuta/pazienti/${pazienteId}/diario`}
      data-testid={`diario-link-${pazienteId}`}
      className="inline-flex items-center gap-1.5 text-xs text-[#F58A1F] hover:text-[#F58A1F]/80 font-medium relative"
      title="Diario emozionale del paziente"
    >
      <BookHeart className="w-3.5 h-3.5" />
      <span>Diario</span>
      {unread > 0 && (
        <span className="ml-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-[#F58A1F] text-white text-[10px] font-bold">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}
