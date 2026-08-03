import LegalLayout from "@/components/public/LegalLayout";
import { TITOLARE } from "@/data/legalInfo";

export default function TerminiPage() {
  return (
    <LegalLayout title="Termini e Condizioni" lastUpdate="18 febbraio 2026" testId="termini-page">
      <p>
        I presenti Termini regolano l&apos;utilizzo di <strong>funzionabene.it</strong>, marchio di <strong>{TITOLARE.nome}</strong>{" "}
        (P.IVA {TITOLARE.pIva}, sede in {TITOLARE.via}, {TITOLARE.citta}) — piattaforma di intermediazione tra pazienti e
        professionisti sanitari iscritti agli Albi degli Psicologi/Medici.
      </p>

      <h2>1. Ruolo di BIDOC SRL — Mandato all&apos;incasso con Rappresentanza</h2>
      <p>
        {TITOLARE.nome} <strong>non è un&apos;azienda sanitaria</strong> e non eroga direttamente prestazioni cliniche.
        La Società opera in regime di <strong>mandato all&apos;incasso con rappresentanza</strong> (artt. 1703 e ss. c.c.):
        gestisce l&apos;agenda, l&apos;incasso e il rimborso delle sessioni <em>per conto</em> del professionista sanitario titolare
        della prestazione. Le sessioni terapeutiche restano un rapporto diretto tra paziente e terapeuta.
      </p>

      <h2>2. Oggetto del servizio</h2>
      <p>
        Attraverso la piattaforma il paziente può prenotare sessioni individuali o di coppia con psicologi/sessuologi iscritti
        agli Albi italiani e assicurati. Le sessioni si svolgono online tramite videochiamata sicura (Daily.co) o, dove indicato,
        in studio.
      </p>

      <h2>3. Accesso e registrazione</h2>
      <ul>
        <li>Il servizio è riservato a maggiorenni (18+).</li>
        <li>Per prenotare è necessario registrarsi fornendo dati veritieri e completi, verificati via OTP email e SMS.</li>
        <li>L&apos;utente è responsabile della riservatezza delle proprie credenziali.</li>
      </ul>

      <h2>4. Dati fiscali e fattura sanitaria</h2>
      <p>
        Prima del pagamento è obbligatorio fornire Codice Fiscale, residenza e luogo di nascita. La <strong>fattura sanitaria</strong>{" "}
        è emessa direttamente dal <strong>professionista sanitario</strong> in tuo nome — {TITOLARE.nome} agisce solo come
        rappresentante tecnico. La fattura è <strong>esente IVA ex art. 10 DPR 633/72 c.1 n.18</strong> e, se di importo pari o
        superiore a €77,47, riporta la marca da bollo di €2,00 come previsto dal DPR 642/1972.
      </p>

      <h2>5. Sistema Tessera Sanitaria — Opposizione</h2>
      <p>
        I dati della fattura sanitaria vengono trasmessi al <strong>Sistema TS</strong> per permettere la detrazione fiscale del 19%
        nel 730 precompilato (art. 15 TUIR). Puoi <strong>opporti</strong> alla trasmissione al momento della prenotazione (art. 3
        D.M. 31/07/2015): in tal caso la spesa non comparirà nel 730 precompilato ma potrai comunque detrarla presentando la
        fattura con il 730 ordinario.
      </p>

      <h2>6. Prenotazione, pagamento e disdetta</h2>
      <ul>
        <li>Le tariffe (indicativamente €49-€90 per 50 minuti) sono definite dal singolo terapeuta e visibili sul suo profilo.</li>
        <li>Il pagamento avviene tramite <strong>Stripe</strong> con crittografia bancaria. {TITOLARE.nome} non conserva dati di carta.</li>
        <li>La prenotazione è confermata al momento del pagamento.</li>
        <li><strong>Annullo/riprogrammazione gratuita fino a 24h prima</strong>. Entro le 24h la sessione è considerata effettuata.</li>
        <li>Impedimento del terapeuta: sessione riprogrammata o rimborsata integralmente.</li>
      </ul>

      <h2>7. Svolgimento della sessione</h2>
      <ul>
        <li>Il link della stanza video è disponibile in area personale 15 minuti prima dell&apos;orario.</li>
        <li>La sessione dura 50 minuti; ritardi del paziente non prolungano l&apos;orario.</li>
        <li>È vietata la registrazione audio/video senza consenso esplicito del terapeuta.</li>
        <li>Il terapeuta è tenuto al <strong>segreto professionale</strong> (art. 11 Codice Deontologico Psicologi).</li>
      </ul>

      <h2>8. Diritto di recesso</h2>
      <p>
        Ai sensi dell&apos;art. 59 lett. a) del Codice del Consumo, il diritto di recesso è escluso per servizi con data determinata
        una volta iniziata l&apos;erogazione. Per sessioni non ancora erogate vale la policy di disdetta.
      </p>

      <h2>9. Limitazione di responsabilità</h2>
      <p>
        {TITOLARE.nome} è un intermediario tecnologico e finanziario in mandato. La <strong>responsabilità clinica</strong> della
        sessione è integralmente del terapeuta assegnato, iscritto all&apos;Albo e assicurato.
        <br />
        <strong>In caso di emergenza psichiatrica o ideazione suicidaria contatta immediatamente il 112 o il Telefono Amico
        (02 2327 2327).</strong>
      </p>

      <h2>10. Proprietà intellettuale</h2>
      <p>
        Il marchio &laquo;Funzionabene&raquo; e tutti i contenuti del sito sono di proprietà di {TITOLARE.nome} o dei rispettivi
        autori, protetti da diritto d&apos;autore.
      </p>

      <h2>11. Legge applicabile e foro competente</h2>
      <p>
        Presenti Termini regolati dalla legge italiana. Foro esclusivo: Pordenone. Prima di agire in giudizio le parti si
        impegnano a tentare una mediazione ex D.Lgs. 28/2010.
      </p>

      <h2>12. Modifiche</h2>
      <p>
        {TITOLARE.nome} si riserva il diritto di modificare i presenti Termini. Gli utenti registrati riceveranno notifica via
        email almeno 15 giorni prima dell&apos;entrata in vigore di modifiche sostanziali.
      </p>
    </LegalLayout>
  );
}
