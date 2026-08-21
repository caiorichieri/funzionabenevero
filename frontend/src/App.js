import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";

import ScrollToTop from "@/components/shared/ScrollToTop";
import CookieBanner from "@/components/public/CookieBanner";
import PWAInstaller from "@/components/shared/PWAInstaller";
import IOSInstallHelper from "@/components/shared/IOSInstallHelper";

import AppRoutes, { StandaloneRedirector } from "@/routes";

import "@/App.css";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ScrollToTop />
        <StandaloneRedirector />
        <PWAInstaller />
        <IOSInstallHelper />
        <AppRoutes />
        <CookieBanner />
      </BrowserRouter>
    </AuthProvider>
  );
}
