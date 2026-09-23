import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import DailyIframe from "@daily-co/daily-js";
import { ArrowLeft, AlertCircle, Clock, Calendar } from "lucide-react";

/**
 * Video-call entry point.
 *
 * Handles three time-gating cases returned by the backend:
 *  - 200 OK       → open the Daily.co iframe.
 *  - 425 Too Early → show a countdown to `available_at` and auto-retry.
 *  - 410 Gone     → session window closed (no-show cutoff): show a friendly
 *                    message with a rebook CTA (patient) or contact-hr CTA
 *                    (therapist).
 */
export default function VideoCallPage() {
  const { appuntamentoId } = useParams();
  const [searchParams] = useSearchParams();
  const magicToken = searchParams.get("token");
  const navigate = useNavigate();
  const { user } = useAuth();
  const containerRef = useRef(null);
  const callFrameRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState(null);
  const [tooEarly, setTooEarly] = useState(null); // { available_at, start_at }
  const [closed, setClosed] = useState(null);     // { start_at, message, terapeuta_id }
  const [countdown, setCountdown] = useState("");

  const openFrame = useCallback((data) => {
    const { room_url, token, user_name } = data;
    if (!room_url) {
      setError("Stanza video non disponibile");
      setLoading(false);
      return;
    }
    if (callFrameRef.current) {
      try { callFrameRef.current.destroy(); } catch (e) { console.warn("daily destroy failed:", e); }
      callFrameRef.current = null;
    }
    const frame = DailyIframe.createFrame(containerRef.current, {
      showLeaveButton: true,
      allowMultipleCallInstances: true,
      iframeStyle: {
        position: "absolute", top: 0, left: 0, width: "100%", height: "100%",
        border: "0", background: "#0A0A0A",
      },
      theme: {
        colors: {
          accent: "#F58A1F", accentText: "#0A0A0A", background: "#0A0A0A",
          backgroundAccent: "#1C2A33", baseText: "#F4F1ED",
          border: "#1F2937", mainAreaBg: "#111111",
          mainAreaBgAccent: "#1C2A33", mainAreaText: "#F4F1ED",
          supportiveText: "#B8B4A8",
        },
      },
    });
    callFrameRef.current = frame;
    frame.on("left-meeting", () => {
      try { frame.destroy(); } catch (e) { console.warn("daily destroy failed:", e); }
      navigate(-1);
    });
    frame.on("error", (e) => {
      console.error("Daily error:", e);
      setError(e?.errorMsg || "Errore nella stanza video");
    });
    const joinOptions = { url: room_url, userName: user_name };
    if (token) joinOptions.token = token;
    frame.join(joinOptions).then(() => setLoading(false));
  }, [navigate]);

  const fetchToken = useCallback(async () => {
    setError("");
    setTooEarly(null);
    setClosed(null);
    setLoading(true);
    try {
      const res = magicToken
        ? await axios.get(`${API}/videocall-magic/${appuntamentoId}`, { params: { token: magicToken } })
        : await axios.post(`${API}/appuntamenti/${appuntamentoId}/video-token`, {}, { withCredentials: true });
      setMeta(res.data);
      openFrame(res.data);
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      if (status === 425 && detail && typeof detail === "object" && detail.available_at) {
        setTooEarly({ available_at: detail.available_at, start_at: detail.start_at });
      } else if (status === 410 && detail && typeof detail === "object") {
        setClosed({ start_at: detail.start_at, message: detail.message || "Sessione chiusa" });
      } else {
        const msg = typeof detail === "string" ? detail : (detail?.message || "Impossibile entrare nella stanza");
        setError(msg);
      }
      setLoading(false);
    }
  }, [magicToken, appuntamentoId, openFrame]);

  useEffect(() => {
    fetchToken();
    return () => {
      if (callFrameRef.current) {
        try { callFrameRef.current.destroy(); } catch (e) { console.warn("daily destroy failed:", e); }
        callFrameRef.current = null;
      }
    };
  }, [fetchToken]);

  // Countdown loop when too-early. Auto-retry ~2s after available_at is reached.
  useEffect(() => {
    if (!tooEarly) return;
    const target = new Date(tooEarly.available_at).getTime();
    const tick = () => {
      const ms = target - Date.now();
      if (ms <= 0) {
        setCountdown("Apertura in corso…");
        setTimeout(fetchToken, 1500);
        return;
      }
      const mm = Math.floor(ms / 60000);
      const ss = Math.floor((ms % 60000) / 1000);
      setCountdown(`${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [tooEarly, fetchToken]);

  const startAtLabel = (iso) => {
    try {
      const d = new Date(iso);
      return new Intl.DateTimeFormat("it-IT", {
        timeZone: "Europe/Rome", weekday: "long", day: "2-digit", month: "long",
        hour: "2-digit", minute: "2-digit",
      }).format(d);
    } catch (e) { return iso; }
  };

  const isTherapist = user?.role === "terapeuta";

  return (
    <div className="fixed inset-0 z-50 bg-[#0A0A0A] flex flex-col" data-testid="video-call-page">
      <div className="relative h-14 px-4 sm:px-6 flex items-center justify-between border-b border-white/10 bg-[#111111]/80 backdrop-blur-xl z-10">
        <button
          data-testid="video-back-btn"
          onClick={() => {
            if (callFrameRef.current) {
              try { callFrameRef.current.destroy(); } catch (e) { console.warn("daily destroy failed:", e); }
            }
            navigate(-1);
          }}
          className="flex items-center gap-2 text-sm text-[#E6E2D8]/70 hover:text-[#F4F1ED]"
        >
          <ArrowLeft className="w-4 h-4" /> Esci
        </button>
        <div className="text-xs tracking-[0.2em] uppercase text-[#E6E2D8]/50 hidden sm:block">
          funzionabene · seduta online
        </div>
        <div className="text-xs text-[#E6E2D8]/50 hidden sm:block">
          {meta ? `${meta.durata_minuti} min` : ""}
        </div>
      </div>

      <div className="relative flex-1">
        <div ref={containerRef} className="absolute inset-0" />

        {loading && !tooEarly && !closed && !error && (
          <div className="absolute inset-0 flex items-center justify-center z-20 bg-[#0A0A0A]">
            <div className="text-center">
              <div className="w-10 h-10 border-2 border-[#F58A1F] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-[#E6E2D8]/60 text-sm">Apertura della stanza video…</p>
            </div>
          </div>
        )}

        {tooEarly && (
          <div className="absolute inset-0 flex items-center justify-center z-20 bg-[#0A0A0A] p-6">
            <div className="max-w-md w-full text-center p-8 bg-[#1C2A33]/40 border border-white/10 rounded-3xl" data-testid="video-too-early">
              <div className="w-14 h-14 mx-auto rounded-full bg-[#F58A1F]/15 flex items-center justify-center mb-5">
                <Clock className="w-7 h-7 text-[#F58A1F]" />
              </div>
              <h2 className="font-serif text-2xl text-[#F4F1ED]">La stanza sta per aprirsi</h2>
              <p className="mt-3 text-sm text-[#E6E2D8]/60">
                La seduta è prevista {startAtLabel(tooEarly.start_at)} (ora italiana).
                <br />La stanza si apre automaticamente qui sotto.
              </p>
              <div className="mt-6 inline-flex items-center gap-3 px-6 py-3 rounded-2xl bg-white/5 border border-white/10">
                <Clock className="w-5 h-5 text-[#F58A1F]" />
                <span className="text-2xl font-mono font-semibold text-[#F4F1ED] tracking-wider" data-testid="video-countdown">
                  {countdown || "--:--"}
                </span>
              </div>
              <p className="mt-4 text-xs text-[#E6E2D8]/40">
                Puoi tenere aperta questa pagina — appena disponibile ti fa entrare da sola.
              </p>
              <button
                onClick={fetchToken}
                className="mt-5 text-xs underline text-[#E6E2D8]/60 hover:text-[#F4F1ED]"
                data-testid="video-retry-btn"
              >
                Riprova ora
              </button>
            </div>
          </div>
        )}

        {closed && (
          <div className="absolute inset-0 flex items-center justify-center z-20 bg-[#0A0A0A] p-6">
            <div className="max-w-md w-full text-center p-8 bg-[#1C2A33]/40 border border-white/10 rounded-3xl" data-testid="video-session-closed">
              <div className="w-14 h-14 mx-auto rounded-full bg-red-500/10 flex items-center justify-center mb-5">
                <AlertCircle className="w-7 h-7 text-red-400" />
              </div>
              <h2 className="font-serif text-2xl text-[#F4F1ED]">Finestra di accesso chiusa</h2>
              <p className="mt-3 text-sm text-[#E6E2D8]/60">
                La seduta del <strong>{startAtLabel(closed.start_at)}</strong> non è più accessibile
                (l&apos;accesso si chiude 15 minuti dopo l&apos;orario di inizio).
              </p>
              {isTherapist ? (
                <>
                  <p className="mt-4 text-sm text-[#E6E2D8]/70">
                    Se non hai potuto essere presente, scrivi al team amministrativo:
                  </p>
                  <a
                    href="mailto:hr@funzionabene.it?subject=Impossibilit%C3%A0%20a%20presiedere%20la%20seduta"
                    data-testid="video-contact-hr"
                    className="mt-4 inline-block px-6 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] rounded-full text-sm font-semibold"
                  >
                    Scrivi a hr@funzionabene.it →
                  </a>
                </>
              ) : (
                <>
                  <p className="mt-4 text-sm text-[#E6E2D8]/70">
                    Nessun problema — puoi prenotare un&apos;altra seduta subito.
                  </p>
                  <button
                    onClick={() => navigate("/paziente")}
                    data-testid="video-rebook"
                    className="mt-4 inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] rounded-full text-sm font-semibold"
                  >
                    <Calendar className="w-4 h-4" /> Prenota un&apos;altra seduta
                  </button>
                </>
              )}
              <button
                onClick={() => navigate(-1)}
                className="mt-4 block mx-auto text-xs text-[#E6E2D8]/40 hover:text-[#F4F1ED]"
              >
                Torna indietro
              </button>
            </div>
          </div>
        )}

        {error && !tooEarly && !closed && (
          <div className="absolute inset-0 flex items-center justify-center z-20 bg-[#0A0A0A] p-6">
            <div className="max-w-md w-full text-center p-8 bg-[#1C2A33]/40 border border-white/10 rounded-3xl" data-testid="video-error">
              <div className="w-14 h-14 mx-auto rounded-full bg-red-500/10 flex items-center justify-center mb-5">
                <AlertCircle className="w-7 h-7 text-red-400" />
              </div>
              <h2 className="font-serif text-2xl text-[#F4F1ED]">Impossibile entrare</h2>
              <p className="mt-3 text-sm text-[#E6E2D8]/60">{error}</p>
              <div className="mt-6 flex justify-center gap-2">
                <button
                  onClick={fetchToken}
                  className="px-5 py-2.5 bg-[#F58A1F] hover:opacity-90 text-[#0A0A0A] rounded-full text-sm font-medium"
                >
                  Riprova
                </button>
                <button
                  onClick={() => navigate(-1)}
                  className="px-5 py-2.5 border border-white/20 text-[#F4F1ED] rounded-full text-sm font-medium"
                >
                  Indietro
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
