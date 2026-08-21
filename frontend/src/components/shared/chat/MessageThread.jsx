import { useEffect, useRef } from "react";
import { Send, ArrowLeft } from "lucide-react";

/**
 * MessageThread — header + scrollable messages + composer for a single conversation.
 * Presentational; parent owns state.
 */
export default function MessageThread({
  activeConv,
  messaggi,
  role,
  input,
  onInputChange,
  onSend,
  onBack,
  sending,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messaggi]);

  if (!activeConv) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-[#0A0A0A]/50">
        Seleziona una conversazione
      </div>
    );
  }

  const otherName =
    role === "paziente" ? `Dr. ${activeConv.terapeuta_nome}` : activeConv.paziente_nome;
  const initial = (role === "paziente" ? activeConv.terapeuta_nome : activeConv.paziente_nome || "?")[0];

  return (
    <>
      {/* Header */}
      <div className="px-5 py-3 border-b border-[#0A0A0A]/10 flex items-center gap-3">
        <button
          className="md:hidden p-1 text-[#0A0A0A]/55 hover:text-[#0A0A0A]"
          onClick={onBack}
          data-testid="chat-back"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="w-9 h-9 rounded-full bg-[#6B8FA3]/10 flex items-center justify-center">
          <span className="text-xs font-medium text-[#6B8FA3]">{initial}</span>
        </div>
        <div>
          <div className="text-sm font-medium text-[#0A0A0A]">{otherName}</div>
          <div className="text-xs text-[#0A0A0A]/50">Conversazione privata</div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3 bg-[#FAF8F3]/30">
        {messaggi.length === 0 ? (
          <div className="text-center text-xs text-[#0A0A0A]/50 py-8">
            Nessun messaggio. Inizia la conversazione.
          </div>
        ) : (
          messaggi.map((m, i) => {
            const isMe = m.mittente_ruolo === role;
            return (
              <div key={m._id || i} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                    isMe
                      ? "bg-[#0A0A0A] text-white rounded-br-sm"
                      : "bg-white border border-[#0A0A0A]/10 text-[#0A0A0A] rounded-bl-sm"
                  }`}
                >
                  {m.testo}
                  <div className={`text-[10px] mt-1 ${isMe ? "text-white/70" : "text-[#0A0A0A]/50"}`}>
                    {new Date(m.created_at).toLocaleTimeString("it-IT", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <form onSubmit={onSend} className="p-3 border-t border-[#0A0A0A]/10 bg-white flex gap-2">
        <input
          data-testid="chat-input"
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="Scrivi un messaggio..."
          className="flex-1 px-4 py-2.5 bg-[#FAF8F3] border border-[#0A0A0A]/10 rounded-full text-sm text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
        />
        <button
          data-testid="chat-send"
          type="submit"
          disabled={sending || !input.trim()}
          className="px-4 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] disabled:opacity-40 text-white rounded-full flex items-center gap-2 text-sm font-medium"
        >
          <Send className="w-4 h-4" /> Invia
        </button>
      </form>
    </>
  );
}
