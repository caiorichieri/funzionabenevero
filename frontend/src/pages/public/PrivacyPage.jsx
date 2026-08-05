import DynamicLegalPage from "@/components/public/DynamicLegalPage";

export default function PrivacyPage() {
  return (
    <DynamicLegalPage
      kind="privacy_pazienti"
      fallbackTitle="Informativa Privacy — Pazienti Registrati"
      testId="privacy-page"
    />
  );
}
