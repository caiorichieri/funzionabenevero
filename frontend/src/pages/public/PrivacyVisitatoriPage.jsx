import DynamicLegalPage from "@/components/public/DynamicLegalPage";

/**
 * Public informativa Privacy for site visitors (not registered users).
 */
export default function PrivacyVisitatoriPage() {
  return (
    <DynamicLegalPage
      kind="privacy_visitatori"
      fallbackTitle="Informativa Privacy — Visitatori del Sito"
      testId="privacy-visitatori-page"
    />
  );
}
