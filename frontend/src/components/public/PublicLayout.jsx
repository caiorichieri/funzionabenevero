import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import { TITOLARE, DPO } from "@/data/legalInfo";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/sedute-immersive", label: "Immersive" },
  { to: "/aree-intervento", label: "Aree" },
  { to: "/il-nostro-mondo", label: "Il nostro mondo" },
  { to: "/chi-siamo", label: "Chi siamo" },
  { to: "/blog", label: "Blog" },
  { to: "/faq", label: "FAQ" },
];

function Header() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const dashboardPath =
    user && user.role === "admin" ? "/admin" :
    user && user.role === "terapeuta" ? "/terapeuta" :
    user && user.role === "paziente" ? "/paziente" : null;

  return (
    <header data-testid="public-header" className="sticky top-0 z-40 bg-[#E3D266]/95 backdrop-blur-xl border-b border-[#0A0A0A]/10">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 h-20 flex items-center justify-between">
        <Link to="/" data-testid="public-logo" className="flex items-center gap-3">
          <img src="/assets/logo.png" alt="FunzionaBene" className="w-12 h-12 object-contain" />
          <span className="font-serif text-3xl sm:text-4xl text-[#0A0A0A] tracking-tight leading-none">funzionabene</span>
        </Link>

        <nav className="hidden lg:flex items-center gap-7">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              data-testid={`nav-${n.label.toLowerCase().replace(/\s+/g,'-')}`}
              className={({ isActive }) =>
                `text-sm tracking-wide whitespace-nowrap transition-colors ${isActive ? "text-[#0A0A0A]" : "text-[#0A0A0A]/75 hover:text-[#0A0A0A]"}`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden lg:flex items-center gap-4">
          {user && user.role ? (
            <>
              <button
                data-testid="nav-dashboard"
                onClick={() => navigate(dashboardPath)}
                className="text-sm text-[#0A0A0A]/75 hover:text-[#0A0A0A]"
              >
                Area personale
              </button>
              <button
                data-testid="nav-logout"
                onClick={async () => { await logout(); navigate("/"); }}
                className="text-sm text-[#0A0A0A]/65 hover:text-[#0A0A0A]"
              >
                Esci
              </button>
            </>
          ) : (
            <>
              <Link to="/login" data-testid="nav-login" className="text-sm text-[#0A0A0A]/75 hover:text-[#0A0A0A]">
                Accedi
              </Link>
              <Link
                to="/questionario"
                data-testid="nav-cta"
                className="px-5 py-2.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg text-sm tracking-wide transition-all"
              >
                Inizia il Questionario
              </Link>
            </>
          )}
        </div>

        <button
          data-testid="mobile-menu-toggle"
          onClick={() => setOpen(!open)}
          className="lg:hidden text-[#0A0A0A] p-2"
          aria-label="Apri menu"
        >
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {open && (
        <div className="lg:hidden border-t border-[#0A0A0A]/10 bg-[#E3D266]/95 backdrop-blur-xl">
          <div className="px-6 py-4 space-y-3">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                onClick={() => setOpen(false)}
                data-testid={`mobile-nav-${n.label.toLowerCase()}`}
                className={({ isActive }) =>
                  `block py-2 text-base ${isActive ? "text-[#0A0A0A]" : "text-[#0A0A0A]/75"}`
                }
              >
                {n.label}
              </NavLink>
            ))}
            <div className="pt-3 border-t border-[#0A0A0A]/10 flex flex-col gap-3">
              {user && user.role ? (
                <>
                  <button onClick={() => { setOpen(false); navigate(dashboardPath); }} className="text-left text-[#0A0A0A]/75 py-2">
                    Area personale
                  </button>
                  <button onClick={async () => { await logout(); setOpen(false); navigate("/"); }} className="text-left text-[#0A0A0A]/65 py-2">
                    Esci
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" onClick={() => setOpen(false)} className="text-[#0A0A0A]/75 py-2">Accedi</Link>
                  <Link
                    to="/questionario"
                    onClick={() => setOpen(false)}
                    className="inline-block w-full text-center px-5 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg"
                  >
                    Inizia il Questionario
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

function Footer() {
  return (
    <footer data-testid="public-footer" className="bg-[#E3D266] border-t border-[#0A0A0A]/12 mt-24">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-16 grid md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <img src="/assets/logo.png" alt="FunzionaBene" className="w-11 h-11 object-contain" />
            <span className="font-serif text-2xl text-[#0A0A0A]">funzionabene</span>
          </div>
          <p className="text-[#0A0A0A]/65 text-sm max-w-md leading-relaxed">
            Uno spazio discreto, professionale e caloroso per la tua salute psicologica e sessuologica.
            Specialisti iscritti all&apos;Albo, percorsi individuali e di coppia.
          </p>
        </div>
        <div>
          <h4 className="text-[#0A0A0A] text-sm tracking-[0.15em] uppercase mb-4">Esplora</h4>
          <ul className="space-y-2 text-sm text-[#0A0A0A]/65">
            <li><Link to="/questionario" className="hover:text-[#0A0A0A]">Questionario</Link></li>
            <li><Link to="/sedute-immersive" className="hover:text-[#0A0A0A]">Sessioni immersive</Link></li>
            <li><Link to="/aree-intervento" className="hover:text-[#0A0A0A]">Aree di intervento</Link></li>
            <li><Link to="/sessualita-e-disabilita" className="hover:text-[#0A0A0A]">Sessualità e disabilità</Link></li>
            <li><Link to="/chi-siamo" className="hover:text-[#0A0A0A]">Chi siamo</Link></li>
            <li><Link to="/blog" className="hover:text-[#0A0A0A]">Blog</Link></li>
            <li><Link to="/faq" className="hover:text-[#0A0A0A]">FAQ</Link></li>
            <li><Link to="/lavora-con-noi" className="hover:text-[#0A0A0A]">Lavora con noi</Link></li>
            <li><Link to="/contatti" className="hover:text-[#0A0A0A]">Contatti</Link></li>
            <li><Link to="/emergenze" className="hover:text-[#C77474]">Numeri d&apos;emergenza</Link></li>
            <li><Link to="/scarica-app" className="hover:text-[#0A0A0A] font-medium">Scarica l&apos;app</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="text-[#0A0A0A] text-sm tracking-[0.15em] uppercase mb-4">Legale</h4>
          <ul className="space-y-2 text-sm text-[#0A0A0A]/65">
            <li><Link to="/privacy" className="hover:text-[#0A0A0A]">Privacy Policy</Link></li>
            <li><Link to="/cookie" className="hover:text-[#0A0A0A]">Cookie Policy</Link></li>
            <li><Link to="/termini" className="hover:text-[#0A0A0A]">Termini e Condizioni</Link></li>
            <li><Link to="/mandato-legale" className="hover:text-[#0A0A0A]">Mandato legale</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-[#0A0A0A]/10">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-6 space-y-3">
          <p className="text-[11px] text-[#0A0A0A]/55 leading-relaxed text-center md:text-left">
            <strong>BIDOC SRL</strong> opera come <strong>piattaforma tecnologica di intermediazione</strong> per l&apos;incontro tra pazienti e professionisti sanitari. Le prestazioni psicologiche/sessuologiche sono erogate autonomamente dai singoli professionisti iscritti al proprio Albo, che ne sono i responsabili clinici e i Titolari autonomi del trattamento dei dati sanitari (artt. 6 e 9 GDPR). Bidoc SRL riscuote i compensi in nome e per conto dei professionisti in forza di Mandato all&apos;Incasso con Rappresentanza.
          </p>
          <div className="flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-[#0A0A0A]/50">
            <span>© {new Date().getFullYear()} funzionabene.it — Marchio di {TITOLARE.nome}</span>
            <span>P.IVA {TITOLARE.pIva} · {TITOLARE.citta} · <a href={`mailto:${DPO.email}`} className="underline hover:text-[#0A0A0A]">DPO: {DPO.email}</a></span>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-transparent text-[#0A0A0A] font-sans antialiased">
      <Header />
      <Outlet />
      <Footer />
    </div>
  );
}
