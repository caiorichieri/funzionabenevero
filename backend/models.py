"""Pydantic models — shared across server.py and router modules."""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    nome: str
    cognome: str
    role: str = "paziente"
    consenso_privacy: bool = True


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class OTPInput(BaseModel):
    email: EmailStr
    otp_code: str


class FormazioneItem(BaseModel):
    titolo: str
    istituto: str
    anno: Optional[int] = None


class DisponibilitaItem(BaseModel):
    giorno: str
    ora_inizio: str
    ora_fine: str


class TerapistaProfileInput(BaseModel):
    nome: Optional[str] = None
    cognome: Optional[str] = None
    telefono: Optional[str] = None
    bio: Optional[str] = None
    anni_esperienza: Optional[int] = None
    specializzazioni: Optional[List[str]] = []
    formazione: Optional[List[FormazioneItem]] = []
    approccio_terapeutico: Optional[str] = None
    genere: Optional[str] = None
    # Dati fiscali (per fatturazione sanitaria + payout)
    codice_fiscale: Optional[str] = None
    data_nascita: Optional[str] = None
    nato_all_estero: Optional[bool] = False
    luogo_nascita_provincia: Optional[str] = None
    luogo_nascita_comune: Optional[str] = None
    paese_nascita: Optional[str] = None
    # Residenza
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    cap: Optional[str] = None
    provincia_residenza: Optional[str] = None
    # Albo / Assicurazione
    albo_numero: Optional[str] = None
    albo_ordine: Optional[str] = None
    albo_iscrizione_data: Optional[str] = None
    assicurazione_compagnia: Optional[str] = None
    assicurazione_numero_polizza: Optional[str] = None
    assicurazione_scadenza: Optional[str] = None
    prezzo_sessione: Optional[float] = None
    lingue: Optional[List[str]] = []
    disponibilita: Optional[List[DisponibilitaItem]] = []
    iban: Optional[str] = None

    @field_validator("iban", mode="before")
    @classmethod
    def _validate_iban(cls, v):
        if v is None:
            return None
        s = str(v).upper().replace(" ", "").strip()
        if s == "":
            return ""
        import re as _re
        if not _re.match(r"^IT\d{2}[A-Z0-9]{23}$", s):
            raise ValueError("IBAN italiano non valido: deve iniziare con IT + 2 cifre + 23 caratteri alfanumerici (27 in totale, no spazi).")
        return s


class PazienteProfileInput(BaseModel):
    nome: Optional[str] = None
    cognome: Optional[str] = None
    data_nascita: Optional[str] = None
    genere: Optional[str] = None
    codice_fiscale: Optional[str] = None
    telefono: Optional[str] = None
    nato_all_estero: Optional[bool] = False
    luogo_nascita_provincia: Optional[str] = None
    luogo_nascita_comune: Optional[str] = None
    paese_nascita: Optional[str] = None
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    cap: Optional[str] = None
    provincia_residenza: Optional[str] = None
    note_cliniche: Optional[str] = None
    terapeuta_assegnato: Optional[str] = None
    dati_fiscali_completi: Optional[bool] = None


class AppuntamentoInput(BaseModel):
    terapeuta_id: str
    paziente_id: str
    data_ora: str
    durata_minuti: int = 50
    tipo: str = "online"
    note: Optional[str] = None


class AppuntamentoStatoInput(BaseModel):
    stato: str


class ArticoloInput(BaseModel):
    titolo: str
    contenuto: str
    categoria: Optional[str] = None
    tags: Optional[List[str]] = []
    immagine_url: Optional[str] = None


class ConsentPrefs(BaseModel):
    essential: bool = True
    analytics: bool = False
    marketing: bool = False


class ConsentLogInput(BaseModel):
    prefs: ConsentPrefs
    policy_version: str
    language: Optional[str] = None
    page_url: Optional[str] = None


class ContractInput(BaseModel):
    kind: str
    title: str
    content_html: str
    effective_date: Optional[str] = None


class ContractAcceptInput(BaseModel):
    contract_id: str
    scrolled_to_end: bool = False


class CheckoutBookingRequest(BaseModel):
    terapeuta_id: str
    paziente_id: str
    data_ora: str
    durata_minuti: int
    tipologia: Optional[str] = "individuale"
    modalita: Optional[str] = "classica"
    note: Optional[str] = None
    origin_url: str
    opposizione_ts: bool = False


class MarkPayoutPaidRequest(BaseModel):
    transaction_ids: List[str]
    payout_reference: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=40, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class FAQInput(BaseModel):
    domanda: str
    risposta: str
    ordine: Optional[int] = 0
