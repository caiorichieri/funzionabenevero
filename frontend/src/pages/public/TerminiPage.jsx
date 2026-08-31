import DynamicLegalPage from "@/components/public/DynamicLegalPage";
import SEO from "@/components/shared/SEO";

export default function TerminiPage() {
  return (
    <>
      <SEO title="Termini e Condizioni" description="Termini e condizioni di utilizzo della piattaforma FunzionaBene per pazienti e utenti registrati." path="/termini" />
      <DynamicLegalPage
        kind="termini_pazienti"
        fallbackTitle="Termini e Condizioni — Pazienti"
        testId="termini-page"
      />
    </>
  );
}
