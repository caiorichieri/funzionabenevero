import LegalLayout from "@/components/public/LegalLayout";
import { TITOLARE, DPO, PRIVACY_EMAIL } from "@/data/legalInfo";

export default function PrivacyPage() {
  return (
    <LegalLayout title="Privacy Policy" lastUpdate="18 febbraio 2026" testId="privacy-page">
      <p>
        La presente informativa descrive le modalità di trattamento dei dati personali degli utenti del sito
        <strong> funzionabene.it</strong>, ai sensi del Regolamento (UE) 2016/679 (<strong>GDPR</strong>) e del D.Lgs. 196/2003
        aggiornato dal D.Lgs. 101/2018.
      </p>

      <h2>1. Titolare del trattamento</h2>
      <p>
        <strong>{TITOLARE.nome}</strong> — <em>{TITOLARE.brand}</em> è un marchio registrato di {TITOLARE.nome}.<br />
        Sede legale: {TITOLARE.via}, {TITOLARE.citta}, {TITOLARE.paese}.<br />
        P.IVA {TITOLARE.pIva}.<br />
        Contatto privacy: <a href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</a>
      </p>

      <h2>2. Responsabile della protezione dei dati (DPO)</h2>
      <p>
        Il Titolare ha nominato un Responsabile della protezione dei dati ai sensi degli artt. 37-39 GDPR:<br />
        <strong>{DPO.nome}</strong><br />
        Sede: {DPO.via}, {DPO.citta}, {DPO.paese}<br />
        C.F. {DPO.codiceFiscale} · P.IVA {DPO.pIva}<br />
        Contatto: <a href={`mailto:${DPO.email}`}>{DPO.email}</a>
      </p>

      <h2>3. Dati raccolti</h2>
      <h3>Categorie</h3>
      <ul>
        <li><strong>Dati anagrafici:</strong> nome, cognome, data di nascita, genere, luogo di nascita.</li>
        <li><strong>Dati di contatto:</strong> email, numero di telefono, indirizzo di residenza.</li>
        <li><strong>Dati fiscali:</strong> Codice Fiscale (necessario per fatturazione sanitaria).</li>
        <li><strong>Dati sanitari</strong> (categoria speciale ex art. 9 GDPR): informazioni fornite al terapeuta durante
          la sessione, questionario di matching, note cliniche.</li>
        <li><strong>Dati di navigazione:</strong> indirizzo IP, log di accesso, cookie tecnici.</li>
        <li><strong>Dati di pagamento:</strong> trattati esclusivamente dal provider Nexi XPay; FunzionaBene non conserva
          i dati della carta.</li>
      </ul>

      <h2>4. Finalità del trattamento</h2>
      <ul>
        <li>Erogazione del servizio clinico di psicoterapia e sessuologia.</li>
        <li>Fatturazione e adempimenti fiscali.</li>
        <li>Gestione prenotazioni, reminder e comunicazioni relative alle sessioni.</li>
        <li>Marketing e newsletter (solo con consenso separato e revocabile).</li>
        <li>Sicurezza informatica e prevenzione frodi.</li>
      </ul>

      <h2>5. Base giuridica</h2>
      <ul>
        <li><strong>Consenso esplicito</strong> (art. 6.1.a e art. 9.2.a) per dati sanitari.</li>
        <li><strong>Esecuzione del contratto</strong> (art. 6.1.b) per erogazione del servizio.</li>
        <li><strong>Obbligo di legge</strong> (art. 6.1.c) per fatturazione e adempimenti fiscali.</li>
        <li><strong>Legittimo interesse</strong> (art. 6.1.f) per sicurezza e prevenzione frodi.</li>
      </ul>

      <h2>6. Modalità di trattamento</h2>
      <p>
        I dati sono trattati con strumenti elettronici e cifratura SSL in transito e at-rest.
        I dati sanitari sono accessibili esclusivamente al terapeuta assegnato e al paziente.
        Il personale tecnico ha accesso solo a dati operativi (log, email) e mai alle note cliniche.
      </p>

      <h2>7. Conservazione</h2>
      <ul>
        <li>Dati anagrafici e fiscali: <strong>10 anni</strong> dalla chiusura del rapporto (obbligo fiscale).</li>
        <li>Note cliniche: <strong>10 anni</strong> ex codice deontologico psicologi.</li>
        <li>Log tecnici: <strong>12 mesi</strong>.</li>
        <li>Dati marketing: fino a revoca del consenso.</li>
      </ul>

      <h2>8. Destinatari dei dati</h2>
      <p>I dati possono essere comunicati ai seguenti responsabili esterni del trattamento:</p>
      <ul>
        <li><strong>Resend</strong> (servizi email transazionali) — USA, con clausole contrattuali standard UE.</li>
        <li><strong>Daily.co</strong> (videochiamate sicure) — USA, con clausole contrattuali standard UE.</li>
        <li><strong>Stripe</strong> (gestione pagamenti) — Irlanda/USA, con clausole contrattuali standard UE.</li>
        <li><strong>Skebby</strong> (invio SMS di verifica) — Italia.</li>
        <li><strong>Sistema Tessera Sanitaria</strong> (MEF — Ministero dell&apos;Economia e delle Finanze) — Italia. Vedi paragrafo successivo.</li>
        <li><strong>Hosting:</strong> server nell&apos;Unione Europea.</li>
      </ul>

      <h2>8.bis Trasmissione al Sistema Tessera Sanitaria (Sistema TS)</h2>
      <p>
        I dati relativi a spese sanitarie sostenute presso i professionisti operanti sulla piattaforma vengono
        <strong>trasmessi automaticamente al Sistema Tessera Sanitaria</strong> del MEF ai fini della predisposizione della
        dichiarazione dei redditi precompilata (art. 3 D.M. 31/07/2015).
      </p>
      <p>
        <strong>Diritto di opposizione:</strong> il paziente può opporsi a questa trasmissione in ogni momento, direttamente al
        momento della prenotazione tramite l&apos;apposita casella o successivamente tramite il portale
        <a href="https://sistemats1.sanita.finanze.it" target="_blank" rel="noreferrer"> sistemats1.sanita.finanze.it</a>.
        L&apos;opposizione non impedisce la detrazione fiscale del 19% (art. 15 TUIR): in quel caso occorre presentare il 730
        ordinario allegando la fattura.
      </p>

      <h2>9. Diritti dell&apos;interessato (artt. 15-22 GDPR)</h2>
      <ul>
        <li>Accesso ai dati personali.</li>
        <li>Rettifica dati inesatti.</li>
        <li>Cancellazione (diritto all&apos;oblio), compatibilmente con obblighi di legge.</li>
        <li>Limitazione del trattamento.</li>
        <li>Portabilità dei dati.</li>
        <li>Opposizione al trattamento.</li>
        <li>Revoca del consenso in qualsiasi momento.</li>
        <li>Reclamo al Garante Privacy (<a href="https://www.garanteprivacy.it" target="_blank" rel="noreferrer">garanteprivacy.it</a>).</li>
      </ul>

      <h2>10. Come esercitare i diritti</h2>
      <p>
        Invia una richiesta a <a href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</a> oppure direttamente al DPO a {" "}
        <a href={`mailto:${DPO.email}`}>{DPO.email}</a>, allegando un documento di identità.
        Risponderemo entro 30 giorni.
      </p>
    </LegalLayout>
  );
}
