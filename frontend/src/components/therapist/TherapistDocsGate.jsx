import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import { Loader2 } from "lucide-react";

/**
 * Blocks a terapeuta from accessing any /terapeuta/* route until they've
 * signed ALL mandatory legal documents (contratto_collaborazione, privacy_terapeuti,
 * termini_pazienti, cookie_policy).
 *
 * If pending documents exist → force redirect to /terapeuta/firma-documenti.
 * Applied at the therapist Layout level; the signature page itself lives OUTSIDE
 * this gate so the user can actually sign.
 */
export default function TherapistDocsGate({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  const [state, setState] = useState({ loading: true, pendingCount: 0 });

  useEffect(() => {
    let cancelled = false;
    if (!user || user === false || user.role !== "terapeuta") {
      setState({ loading: false, pendingCount: 0 });
      return;
    }
    (async () => {
      try {
        const { data } = await axios.get(`${API}/contracts/pending/mine`, { withCredentials: true });
        if (!cancelled) setState({ loading: false, pendingCount: (data?.pending || []).length });
      } catch {
        // On error, don't block — fail open so we never lock users out due to transient errors.
        if (!cancelled) setState({ loading: false, pendingCount: 0 });
      }
    })();
    return () => { cancelled = true; };
    // Re-check when route changes (so leaving signature page → returning to dashboard re-validates)
  }, [user, location.pathname]);

  if (state.loading) {
    return (
      <div className="min-h-screen bg-[#111111] flex items-center justify-center" data-testid="therapist-docs-gate-loader">
        <Loader2 className="w-8 h-8 text-[#D4A017] animate-spin" />
      </div>
    );
  }

  if (state.pendingCount > 0) {
    return <Navigate to="/terapeuta/firma-documenti" replace />;
  }

  return children;
}
