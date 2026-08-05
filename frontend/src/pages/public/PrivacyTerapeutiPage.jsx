import { useAuth } from "@/contexts/AuthContext";
import { Navigate } from "react-router-dom";
import DynamicLegalPage from "@/components/public/DynamicLegalPage";

/**
 * Informativa Privacy for therapists — includes the DPA (art. 28 GDPR).
 * Access restricted to authenticated therapists and admin only.
 */
export default function PrivacyTerapeutiPage() {
  const { user } = useAuth();

  // Loading state
  if (user === null) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center" data-testid="privacy-terapeuti-loading">
        <div className="w-8 h-8 border-2 border-[#F58A1F] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Unauthenticated or wrong role → redirect to login
  if (!user || !["terapeuta", "admin"].includes(user.role)) {
    return <Navigate to="/login?redirect=/privacy-terapeuti" replace />;
  }

  return (
    <DynamicLegalPage
      kind="privacy_terapeuti"
      fallbackTitle="Informativa Privacy — Terapeuti (+ DPA)"
      testId="privacy-terapeuti-page"
    />
  );
}
