import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import DailyIframe from "@daily-co/daily-js";
import { ArrowLeft, AlertCircle } from "lucide-react";

export default function VideoCallPage() {
  const { appuntamentoId } = useParams();
  const [searchParams] = useSearchParams();
  const magicToken = searchParams.get("token");
  const navigate = useNavigate();
  const containerRef = useRef(null);
  const callFrameRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function start() {
      try {
        // Magic link path (no auth needed) if a ?token=xxx is present
        const res = magicToken
          ? await axios.get(`${API}/videocall-magic/${appuntamentoId}`, {
              params: { token: magicToken },
            })
          : await axios.post(
              `${API}/appuntamenti/${appuntamentoId}/video-token`,
              {},
              { withCredentials: true }
            );
        if (cancelled) return;

        const { room_url, token, user_name } = res.data;
        setMeta(res.data);

        if (!room_url) {
          setError("Stanza video non disponibile");
          setLoading(false);
          return;
        }

        if (callFrameRef.current) {
          callFrameRef.current.destroy();
          callFrameRef.current = null;
        }

        const frame = DailyIframe.createFrame(containerRef.current, {
          showLeaveButton: true,
          iframeStyle: {
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            border: "0",
            background: "#0A0A0A",
          },
          theme: {
            colors: {
              accent: "#0A0A0A",
              accentText: "#111111",
              background: "#0A0A0A",
              backgroundAccent: "#1C2A33",
              baseText: "#F4F1ED",
              border: "rgba(255,255,255,0.08)",
              mainAreaBg: "#111111",
              mainAreaBgAccent: "#1C2A33",
              mainAreaText: "#F4F1ED",
              supportiveText: "rgba(230,226,216,0.7)",
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
        await frame.join(joinOptions);
        setLoading(false);
      } catch (err) {
        if (cancelled) return;
        const d = err.response?.data?.detail;
        setError(typeof d === "string" ? d : "Impossibile entrare nella stanza");
        setLoading(false);
      }
    }

    start();

    return () => {
      cancelled = true;
      if (callFrameRef.current) {
        try { callFrameRef.current.destroy(); } catch (e) { console.warn("daily destroy failed:", e); }
        callFrameRef.current = null;
      }
    };
  }, [appuntamentoId, magicToken, navigate]);

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
          <ArrowLeft className="w-4 h-4" /> Esci dalla seduta
        </button>
        <div className="text-xs tracking-[0.2em] uppercase text-[#0A0A0A] hidden sm:block">
          funzionabene · seduta online
        </div>
        <div className="text-xs text-[#E6E2D8]/50 hidden sm:block">
          {meta ? `${meta.durata_minuti} min` : ""}
        </div>
      </div>

      <div className="relative flex-1">
        <div ref={containerRef} className="absolute inset-0" />

        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-20 bg-[#0A0A0A]">
            <div className="text-center">
              <div className="w-10 h-10 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-[#E6E2D8]/60 text-sm">Apertura della stanza video...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-20 bg-[#0A0A0A] p-6">
            <div className="max-w-md w-full text-center p-8 bg-[#1C2A33]/40 border border-white/10 rounded-3xl" data-testid="video-error">
              <div className="w-14 h-14 mx-auto rounded-full bg-red-500/10 flex items-center justify-center mb-5">
                <AlertCircle className="w-7 h-7 text-red-400" />
              </div>
              <h2 className="font-serif text-2xl text-[#F4F1ED]">Impossibile entrare</h2>
              <p className="mt-3 text-sm text-[#E6E2D8]/60">{error}</p>
              <p className="mt-2 text-xs text-[#E6E2D8]/40">
                La stanza è disponibile 15 minuti prima dell&apos;orario della seduta.
              </p>
              <button
                onClick={() => navigate(-1)}
                className="mt-6 px-6 py-3 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-[#111111] rounded-full text-sm font-medium"
              >
                Torna indietro
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
