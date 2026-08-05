import { useAuth } from "@/contexts/AuthContext";
import { Navigate } from "react-router-dom";
import DynamicLegalPage from "@/components/public/DynamicLegalPage";

/**
 * Contratto di Collaborazione Professionale tra BIDOC SRL e il Terapeuta.
 * Access restricted to authenticated therapists and admin only (per user request).
 */
export default function ContrattoCollaborazionePage() {
  const { user } = useAuth();

  if (user === null) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center" data-testid="contratto-collaborazione-loading">
        <div className="w-8 h-8 border-2 border-[#F58A1F] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user || !["terapeuta", "admin"].includes(user.role)) {
    return <Navigate to="/login?redirect=/contratto-collaborazione" replace />;
  }

  return (
    <DynamicLegalPage
      kind="contratto_collaborazione"
      fallbackTitle="Contratto di Collaborazione Professionale"
      testId="contratto-collaborazione-page"
    />
  );
}
