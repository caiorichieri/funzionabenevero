import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import Mascotte from "@/components/shared/Mascotte";
import ConversationList from "@/components/shared/chat/ConversationList";
import MessageThread from "@/components/shared/chat/MessageThread";

/**
 * ChatPanel — private 1:1 chat between paziente and terapista.
 * Orchestrates conversations + messages state; delegates rendering to
 * ConversationList and MessageThread. Usable for both roles.
 */
export default function ChatPanel({ role }) {
  const [conversazioni, setConversazioni] = useState([]);
  const [activeConv, setActiveConv] = useState(null);
  const [messaggi, setMessaggi] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const pollRef = useRef(null);

  const loadConversazioni = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/conversazioni`, { withCredentials: true });
      setConversazioni(res.data || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadConversazioni(); }, [loadConversazioni]);

  const loadMessaggi = useCallback(async (convId) => {
    if (!convId) return;
    try {
      const res = await axios.get(`${API}/messaggi/${convId}`, { withCredentials: true });
      setMessaggi(res.data || []);
      loadConversazioni();
    } catch (err) {
      console.warn("[ChatPanel] loadMessaggi failed:", err);
    }
  }, [loadConversazioni]);

  useEffect(() => {
    if (!activeConv) return;
    loadMessaggi(activeConv.conversazione_id);
    pollRef.current = setInterval(() => loadMessaggi(activeConv.conversazione_id), 5000);
    return () => pollRef.current && clearInterval(pollRef.current);
  }, [activeConv, loadMessaggi]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !activeConv) return;
    setSending(true);
    try {
      const destinatario_id = role === "paziente" ? activeConv.terapeuta_id : activeConv.paziente_id;
      await axios.post(
        `${API}/messaggi`,
        { destinatario_id, testo: input.trim() },
        { withCredentials: true }
      );
      setInput("");
      await loadMessaggi(activeConv.conversazione_id);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-[#0A0A0A]/55 text-sm" data-testid="chat-loading">
        Caricamento messaggi...
      </div>
    );
  }

  if (conversazioni.length === 0) {
    return (
      <div className="p-12 text-center flex flex-col items-center" data-testid="chat-empty">
        <Mascotte name="ovo" size={110} animation="float" />
        <h3 className="font-serif text-xl text-[#0A0A0A] mt-4 mb-2">Nessuna conversazione</h3>
        <p className="text-sm text-[#0A0A0A]/55 max-w-sm">
          {role === "paziente"
            ? "Le conversazioni con il tuo terapeuta saranno disponibili dopo la prima prenotazione confermata."
            : "Le conversazioni con i tuoi pazienti appariranno qui dopo la prima seduta."}
        </p>
      </div>
    );
  }

  return (
    <div
      className="grid md:grid-cols-[280px_1fr] h-[540px] border border-[#0A0A0A]/10 rounded-2xl overflow-hidden bg-white"
      data-testid="chat-panel"
    >
      <div
        className={`border-r border-[#0A0A0A]/10 bg-[#FAF8F3]/60 overflow-y-auto ${
          activeConv ? "hidden md:block" : ""
        }`}
      >
        <ConversationList
          conversazioni={conversazioni}
          activeConv={activeConv}
          onSelect={setActiveConv}
          role={role}
        />
      </div>

      <div className={`flex flex-col ${!activeConv ? "hidden md:flex" : "flex"}`}>
        <MessageThread
          activeConv={activeConv}
          messaggi={messaggi}
          role={role}
          input={input}
          onInputChange={setInput}
          onSend={sendMessage}
          onBack={() => setActiveConv(null)}
          sending={sending}
        />
      </div>
    </div>
  );
}
