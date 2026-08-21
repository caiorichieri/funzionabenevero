# CHANGELOG — funzionabene.it

## 2026-02 — Bug Fix: Checkout Registration Consent (P0)
- **File**: `/app/frontend/src/components/public/BookingSheet.jsx`
- **Issue**: Nuovi utenti che si registravano dal BookingSheet pubblico ricevevano l'errore backend "I consensi obbligatori (privacy e termini) sono richiesti" anche spuntando il checkbox.
- **Root cause**: Il payload di `POST /api/auth/register` inviava solo `consenso_privacy:true`, senza `consenso_termini:true`. Il backend `auth.py` esige entrambi.
- **Fix**:
  1. `handleRegister` ora invia sia `consenso_privacy:true` sia `consenso_termini:true`.
  2. Label del checkbox aggiornato: include link a Privacy Policy e Termini di Servizio.
  3. Messaggio d'errore locale aggiornato: "Devi accettare Privacy Policy e Termini di Servizio".
- **Test**: Verificato end-to-end via `bug_testing_agent` (iteration_25) — 100% backend + 100% frontend, flusso avanza allo step OTP.

## 2026-02 — Blocco 1: Legal Architecture + Informed Consent
- **File**: `/app/backend/routers/informed_consents.py`, `/app/frontend/src/pages/public/ConsensoInformatoPage.jsx`
- **New feature**: Informed Consent to psychological/sexological treatment via magic-link email.
- Consent is issued PATIENT → THERAPIST (not to Bidoc SRL, which is only marketplace/intermediary).
- Automatic email trigger on first booking with a new therapist.
- One consent per (paziente, terapeuta) pair. New therapist → new consent required.
- Video call access blocked (HTTP 412) if no active consent for that therapist.
- Footer updated: Bidoc SRL = "piattaforma tecnologica di intermediazione", not healthcare provider.
- DPO registered: Caio Silvestre Richieri (SLVCAI76D16Z602F, caio@friulion.it).
- Admin email renamed: admin@ → hr@funzionabene.it (seed handles graceful rename).

## 2026-02 — Blocco 2: Cancellations + Refunds + Reviews
- **Files**: `/app/backend/routers/cancellations.py`, `/app/backend/routers/reviews.py`, `/app/frontend/src/pages/patient/ReviewPage.jsx`
- **Cancellation policy** (configurable via env vars CANCEL_HOURS_FULL/CANCEL_HOURS_PARTIAL/CANCEL_PARTIAL_PCT):
  - ≥24h → 100% refund
  - 12-24h → 50% refund
  - <12h → 0% (no-show)
- **Patient endpoint** `POST /api/appuntamenti/{id}/cancella` with automatic Stripe refund.
- **Reviews with admin moderation**: patient submits → status=pending → admin approve/reject → only approved visible on public profile.
- Auto email invite 30 min after session end to leave a review.

## 2026-02 — Blocco 3: Tech Debt Cleanup
- **Fix lint errors**: 4 apostrofi non-escaped, 1 unused eslint disable directive. Project code: 0 lint errors.
- **New tests**: 17 pytest tests for Blocco 1+2 features (consent, cancellations, reviews).
- **pytest.ini** with markers (smoke/integration/slow).
- **run_smoke_tests.sh**: fast smoke suite (18 tests, ~3s) for CI.
- **.github/workflows/ci.yml**: GitHub Actions for lint + smoke tests.
- **Automated MongoDB backup**: `backup_service.py` + scheduler (daily 03:00 UTC, monthly on day 1, cleanup weekly). Requires B2_KEY_ID/B2_APP_KEY/B2_BUCKET_NAME env vars (Backblaze B2).
