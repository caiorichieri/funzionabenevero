import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";

// Auth / onboarding
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import CandidaturaTerapeutaPage from "@/pages/CandidaturaTerapeutaPage";
import OTPPage from "@/pages/OTPPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";

// Admin
import AdminDashboard from "@/pages/admin/AdminDashboard";
import AdminCalendarioPage from "@/pages/admin/AdminCalendarioPage";
import TerapistiPage from "@/pages/admin/TerapistiPage";
import PazientiPage from "@/pages/admin/PazientiPage";
import AppuntamentiPage from "@/pages/admin/AppuntamentiPage";
import BlogPage from "@/pages/admin/BlogPage";
import ContrattiPage from "@/pages/admin/ContrattiPage";
import PagamentiPage from "@/pages/admin/PagamentiPage";
import FatturePage from "@/pages/admin/FatturePage";
import RegistroTrattamentiPage from "@/pages/admin/RegistroTrattamentiPage";
import RecensioniPage from "@/pages/admin/RecensioniPage";
import AdminAmbassadorsPage from "@/pages/admin/AmbassadorsPage";
import SessualitaDisabilitaPage from "@/pages/public/SessualitaDisabilitaPage";

// Therapist
import TerapistaDashboard from "@/pages/therapist/TerapistaDashboard";
import TerapistaProfile from "@/pages/therapist/TerapistaProfile";
import TerapistaBlogPage from "@/pages/therapist/TerapistaBlogPage";
import TerapistaCalendarioPage from "@/pages/therapist/TerapistaCalendarioPage";
import TerapeutaDiarioPazientePage from "@/pages/therapist/TerapeutaDiarioPazientePage";
import FirmaDocumentiPage from "@/pages/therapist/FirmaDocumentiPage";
import TherapistDocsGate from "@/components/therapist/TherapistDocsGate";

// Patient
import PazienteDashboard from "@/pages/patient/PazienteDashboard";
import PazienteHome from "@/pages/patient/PazienteHome";
import ChatMobilePage from "@/pages/patient/ChatMobilePage";
import ProfiloPage from "@/pages/patient/ProfiloPage";
import DiarioPage from "@/pages/patient/DiarioPage";
import ReviewPage from "@/pages/patient/ReviewPage";
import PazienteAppShell from "@/components/paziente/PazienteAppShell";

// Public / marketing
import PublicLayout from "@/components/public/PublicLayout";
import HomePage from "@/pages/public/HomePage";
import QuestionnairePage from "@/pages/public/QuestionnairePage";
import MatchingResultsPage from "@/pages/public/MatchingResultsPage";
import TerapistaPublicPage from "@/pages/public/TerapistaPublicPage";
import BlogPublicPage from "@/pages/public/BlogPublicPage";
import BlogPostPage from "@/pages/public/BlogPostPage";
import FAQPage from "@/pages/public/FAQPage";
import PrivacyPage from "@/pages/public/PrivacyPage";
import CookiePage from "@/pages/public/CookiePage";
import TerminiPage from "@/pages/public/TerminiPage";
import SeduteImmersive from "@/pages/public/SeduteImmersive";
import AreeInterventoPage from "@/pages/public/AreeInterventoPage";
import EmergenzePage from "@/pages/public/EmergenzePage";
import ChiSiamoPage from "@/pages/public/ChiSiamoPage";
import IlNostroMondoPage from "@/pages/public/IlNostroMondoPage";
import LavoraConNoiPage from "@/pages/public/LavoraConNoiPage";
import ContattiPage from "@/pages/public/ContattiPage";
import PaymentSuccessPage from "@/pages/public/PaymentSuccessPage";
import PaymentCancelPage from "@/pages/public/PaymentCancelPage";
import MandatoLegalePage from "@/pages/public/MandatoLegalePage";
import PrivacyVisitatoriPage from "@/pages/public/PrivacyVisitatoriPage";
import PrivacyTerapeutiPage from "@/pages/public/PrivacyTerapeutiPage";
import ContrattoCollaborazionePage from "@/pages/public/ContrattoCollaborazionePage";
import LegalDeclinePage from "@/pages/public/LegalDeclinePage";
import ScaricaAppPage from "@/pages/public/ScaricaAppPage";
import ConsensoInformatoPage from "@/pages/public/ConsensoInformatoPage";
import NotFoundPage from "@/pages/public/NotFoundPage";

// Shared
import Layout from "@/components/shared/Layout";
import PrivacyUtentePage from "@/pages/shared/PrivacyUtentePage";
import RiprogrammaPage from "@/pages/RiprogrammaPage";
import VideoCallPage from "@/pages/VideoCallPage";

// Standalone-mode helpers
import useStandalone from "@/hooks/useStandalone";

const ADMIN_ROLES = ["admin"];
const THERAPIST_ROLES = ["terapeuta"];
const PATIENT_ROLES = ["paziente"];

/** Auth gate: renders children only for allowed roles, otherwise redirects. */
function ProtectedRoute({ children, roles }) {
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="min-h-screen bg-[#111111] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#D4A017] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (user === false) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

/** Paziente area: installed PWA → dedicated mobile app shell, otherwise legacy Layout. */
function PazienteLayoutSwitch() {
  const standalone = useStandalone();
  return standalone ? <PazienteAppShell /> : <Layout />;
}

/** Paziente home: standalone shows mockup-style Home, browser shows legacy dashboard. */
function PazienteHomeSwitch() {
  const standalone = useStandalone();
  return standalone ? <PazienteHome /> : <PazienteDashboard />;
}

/**
 * When running as installed PWA, keep users focused inside /paziente/*.
 * Whitelisted paths still work (login, registration, video session, etc).
 * Marketing pages redirect to the role-aware home.
 */
export function StandaloneRedirector() {
  const standalone = useStandalone();
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    if (!standalone) return;
    const p = location.pathname;
    const allowed = (
      p.startsWith("/paziente") ||
      p.startsWith("/terapeuta") ||
      p.startsWith("/admin") ||
      p.startsWith("/terapeuti") ||
      p.startsWith("/questionario") ||
      p.startsWith("/login") ||
      p.startsWith("/registrati") ||
      p.startsWith("/candidatura-terapeuta") ||
      p.startsWith("/sessualita-e-disabilita") ||
      p.startsWith("/disabilita") ||
      p.startsWith("/verifica-otp") ||
      p.startsWith("/recupera-password") ||
      p.startsWith("/reset-password") ||
      p.startsWith("/seduta/") ||
      p.startsWith("/payment/")
    );
    const home =
      user?.role === "admin" ? "/admin" :
      user?.role === "terapeuta" ? "/terapeuta" :
      "/paziente";
    if (!allowed) {
      navigate(home, { replace: true });
    } else if (p === "/") {
      navigate(home, { replace: true });
    }
  }, [standalone, location.pathname, navigate, user]);

  return null;
}

/** All application routes centralized in one place. */
export default function AppRoutes() {
  return (
    <Routes>
      {/* Public site */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/questionario" element={<QuestionnairePage />} />
        <Route path="/risultati" element={<MatchingResultsPage />} />
        <Route path="/terapeuti/:id" element={<TerapistaPublicPage />} />
        <Route path="/terapeuti" element={<Navigate to="/questionario" replace />} />
        <Route path="/blog" element={<BlogPublicPage />} />
        <Route path="/blog/:id" element={<BlogPostPage />} />
        <Route path="/faq" element={<FAQPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/privacy-pazienti" element={<PrivacyPage />} />
        <Route path="/privacy-visitatori" element={<PrivacyVisitatoriPage />} />
        <Route path="/privacy-terapeuti" element={<PrivacyTerapeutiPage />} />
        <Route path="/cookie" element={<CookiePage />} />
        <Route path="/cookie-policy" element={<CookiePage />} />
        <Route path="/termini" element={<TerminiPage />} />
        <Route path="/termini-pazienti" element={<TerminiPage />} />
        <Route path="/contratto-collaborazione" element={<ContrattoCollaborazionePage />} />
        <Route path="/sedute-immersive" element={<SeduteImmersive />} />
        <Route path="/aree-intervento" element={<AreeInterventoPage />} />
        <Route path="/emergenze" element={<EmergenzePage />} />
        <Route path="/chi-siamo" element={<ChiSiamoPage />} />
        <Route path="/il-nostro-mondo" element={<IlNostroMondoPage />} />
        <Route path="/lavora-con-noi" element={<LavoraConNoiPage />} />
        <Route path="/contatti" element={<ContattiPage />} />
        <Route path="/scarica-app" element={<ScaricaAppPage />} />
        <Route path="/payment/success" element={<PaymentSuccessPage />} />
        <Route path="/payment/cancel" element={<PaymentCancelPage />} />
        <Route path="/mandato-legale" element={<MandatoLegalePage />} />
      </Route>

      {/* Auth flows */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/registrati" element={<RegisterPage />} />
      <Route path="/register" element={<Navigate to="/registrati" replace />} />
      <Route path="/candidatura-terapeuta" element={<CandidaturaTerapeutaPage />} />
      <Route path="/lavora-con-noi" element={<Navigate to="/candidatura-terapeuta" replace />} />
      <Route path="/sessualita-e-disabilita" element={<SessualitaDisabilitaPage />} />
      <Route path="/disabilita" element={<Navigate to="/sessualita-e-disabilita" replace />} />
      <Route path="/verifica-otp" element={<OTPPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      {/* Admin */}
      <Route path="/admin" element={<ProtectedRoute roles={ADMIN_ROLES}><Layout /></ProtectedRoute>}>
        <Route index element={<AdminDashboard />} />
        <Route path="calendario" element={<AdminCalendarioPage />} />
        <Route path="terapisti" element={<TerapistiPage />} />
        <Route path="pazienti" element={<PazientiPage />} />
        <Route path="appuntamenti" element={<AppuntamentiPage />} />
        <Route path="blog" element={<BlogPage />} />
        <Route path="contratti" element={<ContrattiPage />} />
        <Route path="fatture" element={<FatturePage isAdmin={true} />} />
        <Route path="registro-trattamenti" element={<RegistroTrattamentiPage />} />
        <Route path="pagamenti" element={<PagamentiPage />} />
        <Route path="recensioni" element={<RecensioniPage />} />
        <Route path="ambassadors" element={<AdminAmbassadorsPage />} />
      </Route>

      {/* Therapist */}
      <Route path="/terapeuta" element={
        <ProtectedRoute roles={THERAPIST_ROLES}>
          <TherapistDocsGate>
            <Layout />
          </TherapistDocsGate>
        </ProtectedRoute>
      }>
        <Route index element={<TerapistaDashboard />} />
        <Route path="calendario" element={<TerapistaCalendarioPage />} />
        <Route path="profilo" element={<TerapistaProfile />} />
        <Route path="blog" element={<TerapistaBlogPage />} />
        <Route path="fatture" element={<FatturePage isAdmin={false} />} />
        <Route path="privacy" element={<PrivacyUtentePage />} />
        <Route path="pazienti/:pazienteId/diario" element={<TerapeutaDiarioPazientePage />} />
      </Route>
      <Route path="/terapeuta/firma-documenti" element={
        <ProtectedRoute roles={THERAPIST_ROLES}>
          <FirmaDocumentiPage />
        </ProtectedRoute>
      } />

      {/* Patient */}
      <Route path="/paziente" element={
        <ProtectedRoute roles={PATIENT_ROLES}>
          <PazienteLayoutSwitch />
        </ProtectedRoute>
      }>
        <Route index element={<PazienteHomeSwitch />} />
        <Route path="diario" element={<DiarioPage />} />
        <Route path="chat" element={<ChatMobilePage />} />
        <Route path="profilo" element={<ProfiloPage />} />
        <Route path="fatture" element={<FatturePage isAdmin={false} />} />
        <Route path="privacy" element={<PrivacyUtentePage />} />
      </Route>

      {/* Public magic-link / token-authenticated pages */}
      <Route path="/legal-decline/:token" element={<LegalDeclinePage />} />
      <Route path="/riprogramma/:appuntamentoId" element={<RiprogrammaPage />} />
      <Route path="/consenso-informato/:consentId" element={<ConsensoInformatoPage />} />
      <Route path="/recensione/:appuntamentoId" element={<ReviewPage />} />
      <Route path="/videocall/:appuntamentoId" element={<VideoCallPage />} />

      {/* Fullscreen authenticated video call */}
      <Route path="/seduta/:appuntamentoId" element={
        <ProtectedRoute roles={["paziente", "terapeuta", "admin"]}>
          <VideoCallPage />
        </ProtectedRoute>
      } />

      {/* 404 */}
      <Route path="*" element={<PublicLayout />}>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
