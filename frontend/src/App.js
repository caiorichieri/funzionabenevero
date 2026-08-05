import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";

const ADMIN_ROLES = ["admin"];
const THERAPIST_ROLES = ["terapeuta"];
const PATIENT_ROLES = ["paziente"];

import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import OTPPage from "@/pages/OTPPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import AdminDashboard from "@/pages/admin/AdminDashboard";
import TerapistiPage from "@/pages/admin/TerapistiPage";
import PazientiPage from "@/pages/admin/PazientiPage";
import AppuntamentiPage from "@/pages/admin/AppuntamentiPage";
import BlogPage from "@/pages/admin/BlogPage";
import ContrattiPage from "@/pages/admin/ContrattiPage";
import PagamentiPage from "@/pages/admin/PagamentiPage";
import TerapistaDashboard from "@/pages/therapist/TerapistaDashboard";
import TerapistaProfile from "@/pages/therapist/TerapistaProfile";
import TerapistaBlogPage from "@/pages/therapist/TerapistaBlogPage";
import TerapistaCalendarioPage from "@/pages/therapist/TerapistaCalendarioPage";
import AdminCalendarioPage from "@/pages/admin/AdminCalendarioPage";
import RiprogrammaPage from "@/pages/RiprogrammaPage";
import PazienteDashboard from "@/pages/patient/PazienteDashboard";
import VideoCallPage from "@/pages/VideoCallPage";
import Layout from "@/components/shared/Layout";
import ScrollToTop from "@/components/shared/ScrollToTop";
import MagicCursor from "@/components/shared/MagicCursor";
import CookieBanner from "@/components/public/CookieBanner";

// Public site
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
import FirmaDocumentiPage from "@/pages/therapist/FirmaDocumentiPage";
import TherapistDocsGate from "@/components/therapist/TherapistDocsGate";
import PrivacyUtentePage from "@/pages/shared/PrivacyUtentePage";
import FatturePage from "@/pages/admin/FatturePage";
import NotFoundPage from "@/pages/public/NotFoundPage";

import "@/App.css";

function ProtectedRoute({ children, roles }) {
  const { user } = useAuth();
  if (user === null) return <div className="min-h-screen bg-[#111111] flex items-center justify-center"><div className="w-8 h-8 border-2 border-[#D4A017] border-t-transparent rounded-full animate-spin"/></div>;
  if (user === false) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ScrollToTop />
        <MagicCursor />
        <Routes>
          {/* Public site */}
          <Route element={<PublicLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/questionario" element={<QuestionnairePage />} />
            <Route path="/risultati" element={<MatchingResultsPage />} />
            <Route path="/terapeuti/:id" element={<TerapistaPublicPage />} />
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
            <Route path="/payment/success" element={<PaymentSuccessPage />} />
            <Route path="/payment/cancel" element={<PaymentCancelPage />} />
            <Route path="/mandato-legale" element={<MandatoLegalePage />} />
          </Route>

          <Route path="/login" element={<LoginPage />} />
          <Route path="/registrati" element={<RegisterPage />} />
          <Route path="/verifica-otp" element={<OTPPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          {/* Admin routes */}
          <Route path="/admin" element={<ProtectedRoute roles={ADMIN_ROLES}><Layout /></ProtectedRoute>}>
            <Route index element={<AdminDashboard />} />
            <Route path="calendario" element={<AdminCalendarioPage />} />
            <Route path="terapisti" element={<TerapistiPage />} />
            <Route path="pazienti" element={<PazientiPage />} />
            <Route path="appuntamenti" element={<AppuntamentiPage />} />
            <Route path="blog" element={<BlogPage />} />
            <Route path="contratti" element={<ContrattiPage />} />
            <Route path="fatture" element={<FatturePage isAdmin={true} />} />
            <Route path="pagamenti" element={<PagamentiPage />} />
          </Route>

          {/* Therapist routes */}
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
          </Route>

          {/* Standalone signature flow (no layout — full-screen guided experience) */}
          <Route path="/terapeuta/firma-documenti" element={
            <ProtectedRoute roles={THERAPIST_ROLES}>
              <FirmaDocumentiPage />
            </ProtectedRoute>
          } />

          {/* Patient routes */}
          <Route path="/paziente" element={<ProtectedRoute roles={PATIENT_ROLES}><Layout /></ProtectedRoute>}>
            <Route index element={<PazienteDashboard />} />
            <Route path="fatture" element={<FatturePage isAdmin={false} />} />
            <Route path="privacy" element={<PrivacyUtentePage />} />
          </Route>

          {/* Public legal decline landing (no auth required — token-based) */}
          <Route path="/legal-decline/:token" element={<LegalDeclinePage />} />

          <Route path="/register" element={<Navigate to="/registrati" replace />} />

          {/* Reschedule (public, token-authenticated) */}
          <Route path="/riprogramma/:appuntamentoId" element={<RiprogrammaPage />} />

          {/* Video call (fullscreen, authenticated paziente/terapeuta/admin) */}
          <Route path="/seduta/:appuntamentoId" element={
            <ProtectedRoute roles={["paziente","terapeuta","admin"]}>
              <VideoCallPage />
            </ProtectedRoute>
          } />

          <Route path="*" element={<PublicLayout />}>
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
        <CookieBanner />
      </BrowserRouter>
    </AuthProvider>
  );
}
