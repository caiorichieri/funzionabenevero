/**
 * ConversationList — sidebar list of chat conversations.
 * Used inside ChatPanel; presentational (no data fetching).
 */
export default function ConversationList({ conversazioni, activeConv, onSelect, role }) {
  return (
    <div className="px-4 py-3 border-b border-[#0A0A0A]/10 text-xs tracking-[0.2em] uppercase text-[#0A0A0A]/55">
      Conversazioni
      <ul className="mt-3 -mx-4">
        {conversazioni.map((c) => {
          const nome = role === "paziente" ? `Dr. ${c.terapeuta_nome}` : c.paziente_nome;
          const isActive = activeConv?.conversazione_id === c.conversazione_id;
          return (
            <li key={c.conversazione_id}>
              <button
                data-testid={`conv-${c.conversazione_id}`}
                onClick={() => onSelect(c)}
                className={`w-full text-left px-4 py-3 border-b border-[#0A0A0A]/8 hover:bg-white/20 transition-colors normal-case tracking-normal ${
                  isActive ? "bg-white/30 border-l-2 border-l-[#0A0A0A]" : ""
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-medium text-[#0A0A0A] text-sm truncate">{nome}</span>
                  {c.non_letti > 0 && (
                    <span className="bg-[#0A0A0A] text-white text-[10px] font-bold min-w-[20px] h-5 px-1.5 rounded-full flex items-center justify-center">
                      {c.non_letti}
                    </span>
                  )}
                </div>
                <div className="text-xs text-[#0A0A0A]/55 truncate">
                  {c.ultimo_messaggio || "Nessun messaggio"}
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
