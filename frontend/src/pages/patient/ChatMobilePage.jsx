import { useEffect, useState, useRef, useCallback } from "react";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import { Send, Loader2, MessageCircle, ArrowLeft } from "lucide-react";

/**
 * Mobile-first chat page: shows list of conversations or one conversation open.
 * For paziente: single conversation with their terapeuta.
 */
export default function ChatMobilePage() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [text, setText] = useState("");
  const scrollRef = useRef(null);

  const loadConversations = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/conversazioni`, { withCredentials: true });
      setConversations(r.data || []);
      // Auto-select the first conversation for paziente
      if ((r.data || []).length === 1) setSelected(r.data[0]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMessages = useCallback(async () => {
    if (!selected) return;
    const r = await axios.get(`${API}/messaggi/${selected.conversazione_id}`, { withCredentials: true });
    setMessages(r.data || []);
    setTimeout(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight); }, 50);
  }, [selected]);

  useEffect(() => { loadConversations(); }, [loadConversations]);
  useEffect(() => { loadMessages(); }, [loadMessages]);

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim() || !selected) return;
    // Backend expects destinatario_id (terapeuta_id for paziente, paziente_id for terapeuta)
    const destinatario_id = selected.terapeuta_id || selected.paziente_id;
    if (!destinatario_id) return;
    setSending(true);
    try {
      await axios.post(`${API}/messaggi`, {
        destinatario_id,
        testo: text.trim(),
      }, { withCredentials: true });
      setText("");
      await loadMessages();
    } finally {
      setSending(false);
    }
  };

  // List view
  if (!selected) {
    return (
      <div className="px-5 pt-8" data-testid="chat-list">
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Chat</h1>
        <p className="text-sm text-[#0A0A0A]/60 mt-1">Le tue conversazioni con il terapeuta.</p>
        <div className="mt-6 space-y-2">
          {loading ? (
            <div className="flex justify-center py-14"><Loader2 className="w-6 h-6 animate-spin text-[#F58A1F]" /></div>
          ) : conversations.length === 0 ? (
            <div className="py-14 text-center bg-white/50 rounded-3xl">
              <MessageCircle className="w-10 h-10 mx-auto text-[#0A0A0A]/30 mb-3" />
              <p className="text-sm text-[#0A0A0A]/60">Ancora nessuna conversazione.</p>
            </div>
          ) : conversations.map((c) => (
            <button
              key={c.conversazione_id}
              onClick={() => setSelected(c)}
              data-testid={`chat-open-${c.conversazione_id}`}
              className="w-full flex items-center gap-3 p-4 bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow text-left"
            >
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-[#0A0A0A] to-[#3A3A3A] text-white font-bold text-sm flex items-center justify-center flex-shrink-0">
                {(c.terapeuta_nome || c.paziente_nome || "?").split(" ").map(s => s[0]).slice(0, 2).join("")}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-sm text-[#0A0A0A] truncate">
                  {c.terapeuta_nome || c.paziente_nome || "Terapeuta"}
                </div>
                <p className="text-xs text-[#0A0A0A]/60 truncate mt-0.5">{c.ultimo_messaggio || "Nessun messaggio ancora"}</p>
              </div>
              {c.non_letti > 0 && (
                <span className="inline-flex items-center justify-center min-w-[22px] h-[22px] rounded-full bg-[#F58A1F] text-white text-[10px] font-bold px-1.5">
                  {c.non_letti > 9 ? "9+" : c.non_letti}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
    );
  }

  // Open conversation view — takes over full app (hides BottomNav so composer is tappable)
  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#F4EAA8]" data-testid="chat-conversation">
      <div className="flex items-center gap-3 px-4 py-3 bg-white/70 backdrop-blur border-b border-[#0A0A0A]/8 flex-shrink-0" style={{ paddingTop: "max(env(safe-area-inset-top, 12px), 12px)" }}>
        <button onClick={() => setSelected(null)} className="p-1 rounded-lg hover:bg-[#0A0A0A]/5" data-testid="chat-back">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-[#0A0A0A] to-[#3A3A3A] text-white font-bold text-xs flex items-center justify-center">
          {(selected.terapeuta_nome || selected.paziente_nome || "?").split(" ").map(s => s[0]).slice(0, 2).join("")}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm text-[#0A0A0A] truncate">{selected.terapeuta_nome || selected.paziente_nome}</div>
          <div className="text-[10px] text-[#0A0A0A]/50">Chat riservata · cifrata</div>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-2 min-h-0">
        {messages.length === 0 ? (
          <div className="text-center text-xs text-[#0A0A0A]/50 py-14">Inizia la conversazione…</div>
        ) : messages.map((m) => {
          const mine = m.mittente_id === user._id;
          return (
            <div key={m._id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[75%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                mine
                  ? "bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] rounded-br-md"
                  : "bg-white text-[#0A0A0A] rounded-bl-md shadow-sm"
              }`}>
                {m.testo}
                <div className={`text-[9px] mt-1 ${mine ? "text-[#0A0A0A]/50" : "text-[#0A0A0A]/40"}`}>
                  {new Date(m.created_at).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <form
        onSubmit={send}
        className="p-3 bg-white/90 backdrop-blur border-t border-[#0A0A0A]/8 flex-shrink-0"
        style={{ paddingBottom: "max(env(safe-area-inset-bottom, 12px), 12px)" }}
      >
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Scrivi un messaggio…"
            data-testid="chat-input"
            className="flex-1 px-4 py-3 rounded-full bg-[#0A0A0A]/5 focus:bg-[#0A0A0A]/8 border-0 text-sm outline-none"
          />
          <button
            type="submit"
            disabled={!text.trim() || sending}
            data-testid="chat-send"
            className="w-11 h-11 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] flex items-center justify-center disabled:opacity-40 transition-opacity"
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin text-[#0A0A0A]" /> : <Send className="w-4 h-4 text-[#0A0A0A]" />}
          </button>
        </div>
      </form>
    </div>
  );
}
