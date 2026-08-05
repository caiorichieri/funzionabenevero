import DynamicLegalPage from "@/components/public/DynamicLegalPage";

export default function TerminiPage() {
  return (
    <DynamicLegalPage
      kind="termini_pazienti"
      fallbackTitle="Termini e Condizioni — Pazienti"
      testId="termini-page"
    />
  );
}
