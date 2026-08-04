import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Sidebar from "@/components/shared/Sidebar";
import { Bell, LogOut, ChevronDown, Menu, X } from "lucide-react";
import { useState } from "react";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const initials = `${user?.nome?.[0] || ""}${user?.cognome?.[0] || ""}`.toUpperCase();

  return (
    <div className="min-h-screen h-screen bg-transparent flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-20 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <div className={`
        fixed lg:sticky top-0 h-screen z-30 lg:z-auto
        transition-transform duration-300
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
      `}>
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 h-screen">
        {/* Topbar */}
        <header className="sticky top-0 z-10 bg-[#E3D266] border-b border-[#0A0A0A]/12 px-6 py-4 flex items-center justify-between">
          <button
            data-testid="sidebar-toggle"
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-xl hover:bg-[#0A0A0A]/5"
          >
            <Menu className="w-5 h-5 text-[#0A0A0A]" />
          </button>

          <div className="hidden lg:block" />

          <div className="flex items-center gap-3">
            <button className="p-2 rounded-xl hover:bg-[#0A0A0A]/5 relative">
              <Bell className="w-5 h-5 text-[#0A0A0A]/65" />
            </button>
            <div className="flex items-center gap-2 pl-3 border-l border-[#0A0A0A]/12">
              <div className="w-8 h-8 rounded-full bg-[#0A0A0A] flex items-center justify-center">
                <span className="text-white text-xs font-semibold">{initials}</span>
              </div>
              <div className="hidden sm:block">
                <div className="text-sm font-medium text-[#0A0A0A]">{user?.nome} {user?.cognome}</div>
                <div className="text-xs text-[#0A0A0A]/55 capitalize">{user?.role}</div>
              </div>
              <button
                data-testid="logout-btn"
                onClick={handleLogout}
                className="ml-2 p-2 rounded-xl hover:bg-red-50 text-[#0A0A0A]/55 hover:text-red-600 transition-colors"
                title="Esci"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 overflow-auto min-h-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
