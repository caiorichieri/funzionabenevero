# WhatsApp Business API — Migration Plan
> Piano completo per sostituire SMS reminders con WhatsApp Business su funzionabene.it
> Status: PLANNED (not implemented). Da eseguire quando WABA + templates saranno pronti.

## FASE 0 — Setup Meta / Twilio (fuori dal codice)

### Step 1. Comprare numero di telefono italiano dedicato
**Opzione A — Twilio Console (raccomandato)**:
1. Twilio Console → Phone Numbers → Buy a Number
2. Country: Italy · Capabilities: SMS + Voice · Type: Mobile
3. Filtra per prefisso italiano (es. Milano +39 02, o cellular +39 3xx)
4. Costo: ~€1,15/mese
5. Il numero è immediatamente disponibile

**IMPORTANTE**: questo numero diventerà "riservato" per WhatsApp Business. Non funzionerà più nell'app WhatsApp normale. Non usare un numero personale o già attivo su WhatsApp.

### Step 2. Creare Facebook Business Manager
1. Accedere a `business.facebook.com` con account Facebook (crearne uno se non esiste)
2. Click "Crea Account"
3. Inserire:
   - **Nome commerciale**: `Funzionabene`
   - **Il tuo nome**: nome completo del legale rappresentante
   - **Email lavoro**: `info@funzionabene.it`
4. Aggiungere dati fiscali completi:
   - **Nome legale attività**: [ragione sociale LLC/ditta]
   - **Indirizzo sede legale**
   - **P.IVA / Codice Fiscale**
   - **Paese**: Italia
   - **Sito web**: `https://funzionabene.it`
   - **Categoria**: `Servizi sanitari e medici`

### Step 3. Business Verification (Meta)
Meta chiederà di verificare il business prima di superare 250 conversazioni/giorno.

**Documenti richiesti**:
- Visura camerale (estratto Camera di Commercio) — mostra P.IVA + nome legale
- Documento di identità del legale rappresentante
- Prova di operatività: link al sito + email `@funzionabene.it` attiva

**Tempo di approvazione**: 3-7 giorni lavorativi.

### Step 4. Creare WhatsApp Business Account (WABA)
**Via Twilio Console (più semplice)**:
1. Twilio Console → Messaging → Try WhatsApp → "Connect Meta Business"
2. OAuth con Meta Business Manager (login con l'account creato allo Step 2)
3. Twilio crea automaticamente il WABA collegato a Twilio
4. Selezionare "Twilio Sender" come integration

### Step 5. Registrare il numero di telefono nel WABA
1. Ancora in Twilio Console → WhatsApp → Register a Phone Number
2. Selezionare il numero comprato allo Step 1
3. Meta invia SMS/chiamata OTP al numero
4. Inserire OTP → numero verificato e attivo su WhatsApp Business

⚠️ **Dopo questo step, il numero non funziona più nell'app WhatsApp regolare**. È dedicato al Business.

### Step 6. Creare e submeter i template messaggi
Servono **4 template**, tutti categoria `UTILITY` (transazionale, non marketing):

#### Template 1: `appuntamento_confermato`
```
Ciao {{1}}, la tua seduta con Dr. {{2}} è confermata per {{3}} alle {{4}}.

Riceverai un promemoria 24h prima e 1h prima. Se hai bisogno di modificare o cancellare, rispondi a questo messaggio.

Funzionabene
```
- Variabili: 4 (nome, dr_cognome, data, ora)
- Header: nessuno
- Footer: nessuno
- Bottoni: opzionale "Vedi dettagli" (URL button → `/paziente/appuntamenti`)

#### Template 2: `promemoria_24h`
```
Ciao {{1}}, ti ricordiamo la tua seduta con Dr. {{2}} domani alle {{3}}.

Entra da qui 20 minuti prima: {{4}}

Se non puoi partecipare, avvisaci rispondendo a questo messaggio. Funzionabene
```
- Variabili: 4 (nome, dr_cognome, ora, magic_link)

#### Template 3: `promemoria_1h`
```
Ciao {{1}}, la tua seduta con Dr. {{2}} inizia tra 1 ora.

Entra qui: {{3}}

Funzionabene
```
- Variabili: 3 (nome, dr_cognome, magic_link)
- Bottone: "Entra nella videocall" URL button dinamico

#### Template 4: `fattura_disponibile`
```
Ciao {{1}}, la fattura {{2}} per la tua seduta è disponibile.

Importo: €{{3}}
Scarica dalla tua area: {{4}}

Funzionabene
```
- Variabili: 4 (nome, numero_fattura, importo, dashboard_url)

**Submeter via Twilio Console**: Messaging → Content Template Builder → "New Template" → incollare, selezionare categoria "Utility", salvare, "Submit for Approval".

**Tempo di approvazione**: 24-48h.

### Step 7. Test in Sandbox
Twilio fornisce un numero WhatsApp sandbox (`+1 415 523 8886`) per testare senza aspettare l'approvazione dei template. Utile per validare il codice prima del go-live.

Comando join sandbox: `join <sandbox-code>` dal proprio WhatsApp verso il numero sandbox.

---

## FASE 1 — Implementazione codice (~4h di lavoro)

### Nuovi file

#### `/app/backend/whatsapp_service.py`
```python
"""WhatsApp Business via Twilio — utility notifications with SMS fallback."""
import asyncio, os, logging
from typing import Optional
from twilio.rest import Client

_client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
WA_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")  # "whatsapp:+39..."

async def send_whatsapp_template(to: str, content_sid: str, variables: dict) -> Optional[str]:
    """Send an approved WhatsApp Business template. Returns message SID on success, None on failure."""
    if not WA_FROM or not to:
        return None
    try:
        msg = await asyncio.to_thread(
            _client.messages.create,
            from_=WA_FROM,
            to=f"whatsapp:{to}" if not to.startswith("whatsapp:") else to,
            content_sid=content_sid,
            content_variables=str(variables).replace("'", '"'),  # JSON string
        )
        logging.info(f"[WA] {content_sid} → {to} sid={msg.sid}")
        return msg.sid
    except Exception as e:
        logging.error(f"[WA] send failed: {e}")
        return None
```

#### File modificati

**`/app/backend/booking_service.py`** — sostituire tutte le `send_sms_reminder` con logica cascade:
```python
# nuovo helper
async def send_notification(phone: str, whatsapp_template: str, template_vars: dict, sms_body: str):
    """Try WhatsApp first, fall back to SMS if it fails."""
    from whatsapp_service import send_whatsapp_template
    from sms_service import send_sms_reminder
    
    if whatsapp_template:
        sid = await send_whatsapp_template(phone, whatsapp_template, template_vars)
        if sid:
            return "whatsapp", sid
    # Fallback → SMS
    ok = await send_sms_reminder(phone, sms_body)
    return "sms" if ok else "failed", None
```

Chiamate esistenti tipo:
```python
await send_sms_reminder(phone, "Ciao Caio, ti ricordiamo...")
```
diventano:
```python
await send_notification(
    phone,
    whatsapp_template=os.environ["TWILIO_TEMPLATE_PROMEMORIA_1H"],
    template_vars={"1": nome, "2": dr_cognome, "3": magic_link},
    sms_body="Ciao Caio, ti ricordiamo la tua seduta ...",  # fallback text
)
```

**`.env` aggiunte**:
```env
TWILIO_WHATSAPP_FROM=whatsapp:+39...
TWILIO_TEMPLATE_CONFERMA=HXaaaaaaaa
TWILIO_TEMPLATE_PROMEMORIA_24H=HXbbbbbbbb
TWILIO_TEMPLATE_PROMEMORIA_1H=HXcccccccc
TWILIO_TEMPLATE_FATTURA=HXdddddddd
```

**Webhook di status (opzionale ma raccomandato)**:
```python
@api_router.post("/webhooks/twilio-status")
async def twilio_status_callback(request: Request):
    """Twilio hits this on every message state change (queued → sent → delivered → read)."""
    form = await request.form()
    sid = form.get("MessageSid")
    status = form.get("MessageStatus")
    if sid:
        await db.notifications_log.update_one(
            {"provider_sid": sid},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    return {"ok": True}
```

Poi configurare Twilio → WhatsApp Sender → Status callback URL → `https://funzionabene.it/api/webhooks/twilio-status`.

### Test
- Unit test in `/app/backend/tests/test_whatsapp_service.py` mockando `_client.messages.create`
- E2E manuale: script simile al `e2e_email_smoke.py` che chiama `send_whatsapp_template` con ogni template su `+393518230667`
- Fallback test: temporaneamente rompere `WA_FROM` per forzare fallback → verificare che SMS parta

### Frontend
- **Nessuna modifica richiesta** per far funzionare il fallback.
- **Miglioria opzionale** (Fase 2): aggiungere in `PazienteProfile.jsx` una preferenza `notifica_preferita: 'whatsapp' | 'sms' | 'email'` che il paziente può cambiare. Serve rispetto GDPR + UX.

---

## COSTI COMPLETI

| Voce | Costo |
|---|---|
| Numero Twilio +39 | €1,15/mese |
| WhatsApp WABA Meta | Gratis |
| Business Verification Meta | Gratis |
| Template approvation | Gratis |
| **Prime 1000 conversazioni/mese** | **Gratis (Meta Free Tier)** |
| Conversazioni utility oltre 1000 | ~€0,03/conv |
| Twilio markup | +€0,01/conv |
| **Totale per conversazione oltre free tier** | **~€0,04** |

**Volume stimato Funzionabene**:
- 20 pazienti/settimana × 3 promemoria (conferma + 24h + 1h) = 60 conversazioni/settimana
- ~240 conversazioni/mese → **dentro il free tier**
- Costo effettivo mensile: **solo €1,15 del numero**

---

## TIMELINE REALISTICA

| Task | Chi | Tempo |
|---|---|---|
| Comprare numero Twilio | Tu | 5 min |
| Creare Facebook Business Manager | Tu (guidato) | 15 min |
| Business Verification (attesa Meta) | Meta | **3-7 giorni** |
| Creare WABA + collegare numero | Tu (guidato) | 20 min |
| Scrivere & submeter 4 template | Io scrivo, tu incolli in Twilio Console | 30 min |
| Approvazione template (attesa Meta) | Meta | **24-48h** |
| Implementazione `whatsapp_service.py` + rewire di `booking_service.py` | Io | 2-3h |
| Test in sandbox | Io | 30 min |
| Deploy in produzione | Io + tu | 30 min |

**Tempo totale realistico dal via**: **1-2 settimane** (blocked dai tempi di Meta).

---

## MIGRAZIONE GRADUALE (raccomandata)

Non fare "big bang" — accende per un sottogruppo prima:

**Sprint 1**: fallback automatico. Se il paziente ha `notifica_preferita: 'whatsapp'` esplicito, prova WhatsApp. Altrimenti SMS.

**Sprint 2**: opt-in di massa. Manda a tutti gli utenti attivi un SMS: *"Vuoi ricevere i promemoria su WhatsApp? Rispondi SI"*.

**Sprint 3**: default WhatsApp. Nuovi utenti hanno `whatsapp` come default. Il paziente può cambiare in profilo.

**Sprint 4**: retire SMS reminder path se il tasso di delivery WhatsApp raggiunge ≥95% (mantieni SMS solo per OTP di verifica telefono, dove serve immediatezza garantita).

---

## Domande aperte da confermare quando iniziamo l'esecuzione

1. Il legale rappresentante di Funzionabene ha già account Facebook personale? (necessario per creare Business Manager)
2. Quale email vuole usare come primary del Business Manager? (raccomando `info@funzionabene.it`)
3. Vuoi bottoni interattivi nei template (es. "Entra alla videocall" come URL button vs. link inline nel body)?
4. Vuoi che i pazienti possano rispondere ai promemoria (customer service) o è solo one-way outbound?
5. GDPR: aggiungere clausola specifica al consenso paziente per "invio notifiche via WhatsApp Business" o basta l'attuale consenso "invio comunicazioni relative alla prestazione"?

---

_Documento generato 2026-09-24 · funzionabene.it_
