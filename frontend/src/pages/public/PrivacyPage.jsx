import DynamicLegalPage from "@/components/public/DynamicLegalPage";
import SEO from "@/components/shared/SEO";

export default function PrivacyPage() {
  return (
    <>
      <SEO title="Informativa Privacy" description="Informativa privacy e trattamento dei dati personali di FunzionaBene, ai sensi del GDPR." path="/privacy" />
      <DynamicLegalPage
        kind="privacy_pazienti"
        fallbackTitle="Informativa Privacy — Pazienti Registrati"
        testId="privacy-page"
      />
    </>
  );
}
