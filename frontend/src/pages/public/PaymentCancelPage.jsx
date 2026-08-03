import { Link } from "react-router-dom";
import { XCircle } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

export default function PaymentCancelPage() {
  return (
    <main className="min-h-[70vh] flex items-center justify-center px-6 py-24" data-testid="payment-cancel-page">
      <div className="brand-card max-w-lg w-full text-center p-10">
        <XCircle className="w-14 h-14 text-[#0A0A0A]/50 mx-auto" />
        <h1 className="font-serif text-2xl text-[#0A0A0A] mt-6">Pagamento annullato</h1>
        <p className="text-[#0A0A0A]/70 mt-3">
          Nessun problema — la tua prenotazione non è stata confermata e non ti abbiamo addebitato nulla. Quando vuoi, ricomincia dall&apos;inizio.
        </p>
        <div className="my-8 flex justify-center">
          <Mascotte name="sereno" theme="light" size={110} animation="breathe" />
        </div>
        <Link
          to="/"
          className="inline-flex items-center justify-center rounded-full px-6 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-medium hover:opacity-90 transition"
          data-testid="back-home-btn"
        >
          Torna alla home
        </Link>
      </div>
    </main>
  );
}
