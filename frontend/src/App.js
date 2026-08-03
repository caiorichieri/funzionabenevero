import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";

const ADMIN_ROLES = ["admin"];
const THERAPIST_ROLES = ["terapeuta"];
const PATIENT_ROLES = ["paziente"];

import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import OTPPage from "@/pages/OTPPage";
import AdminDashboard from "@/pages/admin/AdminDashboard";
import TerapistiPage from "@/pages/admin/TerapistiPage";
import PazientiPage from "@/pages/admin/PazientiPage";
import AppuntamentiPage from "@/pages/admin/AppuntamentiPage";
import BlogPage from "@/pages/admin/BlogPage";
import TerapistaDashboard from "@/pages/therapist/TerapistaDashboard";
import TerapistaProfile from "@/pages/therapist/TerapistaProfile";
import TerapistaBlogPage from "@/pages/therapist/TerapistaBlogPage";
import PazienteDashboard from "@/pages/patient/PazienteDashboard";
import VideoCallPage from "@/pages/VideoCallPage";
import Layout from "@/components/shared/Layout";
import ScrollToTop from "@/components/shared/ScrollToTop";
import MagicCursor from "@/components/shared/MagicCursor";

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
            <Route path="/cookie" element={<CookiePage />} />
            <Route path="/termini" element={<TerminiPage />} />
            <Route path="/sedute-immersive" element={<SeduteImmersive />} />
            <Route path="/aree-intervento" element={<AreeInterventoPage />} />
            <Route path="/emergenze" element={<EmergenzePage />} />
            <Route path="/chi-siamo" element={<ChiSiamoPage />} />
            <Route path="/il-nostro-mondo" element={<IlNostroMondoPage />} />
            <Route path="/lavora-con-noi" element={<LavoraConNoiPage />} />
            <Route path="/contatti" element={<ContattiPage />} />
            <Route path="/payment/success" element={<PaymentSuccessPage />} />
            <Route path="/payment/cancel" element={<PaymentCancelPage />} />
          </Route>

          <Route path="/login" element={<LoginPage />} />
          <Route path="/registrati" element={<RegisterPage />} />
          <Route path="/verifica-otp" element={<OTPPage />} />

          {/* Admin routes */}
          <Route path="/admin" element={<ProtectedRoute roles={ADMIN_ROLES}><Layout /></ProtectedRoute>}>
            <Route index element={<AdminDashboard />} />
            <Route path="terapisti" element={<TerapistiPage />} />
            <Route path="pazienti" element={<PazientiPage />} />
            <Route path="appuntamenti" element={<AppuntamentiPage />} />
            <Route path="blog" element={<BlogPage />} />
          </Route>

          {/* Therapist routes */}
          <Route path="/terapeuta" element={<ProtectedRoute roles={THERAPIST_ROLES}><Layout /></ProtectedRoute>}>
            <Route index element={<TerapistaDashboard />} />
            <Route path="profilo" element={<TerapistaProfile />} />
            <Route path="blog" element={<TerapistaBlogPage />} />
          </Route>

          {/* Patient routes */}
          <Route path="/paziente" element={<ProtectedRoute roles={PATIENT_ROLES}><Layout /></ProtectedRoute>}>
            <Route index element={<PazienteDashboard />} />
          </Route>

          <Route path="/register" element={<Navigate to="/registrati" replace />} />

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
      </BrowserRouter>
    </AuthProvider>
  );
}
