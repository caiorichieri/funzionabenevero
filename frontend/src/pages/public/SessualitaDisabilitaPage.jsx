import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import {
  ChevronDown, ChevronRight, Heart, Users, Baby, Activity, Ear, Brain,
  Zap, ArrowRight, Lock, MessageCircleHeart, Sparkles,
} from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

const NEEDS = [
  { n: "01", icon: Heart, key: "per-me", title: "Per me",
    desc: "Per parlare di corpo, desiderio, piacere, immagine di sé e dei cambiamenti legati alla disabilità." },
  { n: "02", icon: Users, key: "per-la-coppia", title: "Per la coppia",
    desc: "Per ritrovare intimità e comunicazione quando la disabilità cambia ruoli, tempi ed equilibri." },
  { n: "03", icon: Baby, key: "come-genitore", title: "Come genitore",
    desc: "Per accompagnare adolescenti e giovani adulti con strumenti concreti, rispetto e serenità." },
];

const DISABILITY_TYPES = [
  { icon: Activity, title: "Fisica o motoria",
    desc: "Lesioni midollari, amputazioni, paralisi, esiti di trauma o altre condizioni che modificano movimento, sensibilità e autonomia." },
  { icon: Ear, title: "Sensoriale",
    desc: "Disabilità visiva o uditiva, con attenzione a comunicazione, accessibilità, percezione del corpo e relazione." },
  { icon: Brain, title: "Intellettiva o neurodivergenza",
    desc: "Disabilità intellettiva, autismo, sindrome di Down e altre condizioni che richiedono linguaggi e strumenti adeguati." },
  { icon: Zap, title: "Acquisita o progressiva",
    desc: "Cambiamenti legati a malattia, trauma, intervento o patologia degenerativa, con il bisogno di elaborare una nuova immagine di sé." },
];

const DEEP_PATHS = [
  { n: "01", key: "persona", title: "Per la persona", subtitle: "Il corpo cambia. Tu resti tu.",
    desc: "Uno spazio per dare voce anche al disagio più intimo: sentirsi meno desiderabili, fare fatica a riconoscersi, temere il giudizio o non sapere come vivere desiderio e piacere dopo un cambiamento.",
    bullets: ["Immagine corporea, autostima e identità", "Desiderio, piacere e nuove possibilità", "Elaborazione di trauma, diagnosi o perdita funzionale"] },
  { n: "02", key: "coppia", title: "Per la coppia", subtitle: "Non solo cura. Ancora relazione.",
    desc: "Quando la disabilità compare durante la relazione, i ruoli possono cambiare. La coppia può aver bisogno di rinegoziare vicinanza, autonomia, desiderio e modi di stare insieme.",
    bullets: ["Parlare di bisogni senza ferirsi", "Distinguere il ruolo di partner da quello di caregiver", "Gestire differenze nel desiderio e nella disponibilità", "Ritrovare complicità, contatto e intimità"] },
  { n: "03", key: "genitori", title: "Per i genitori", subtitle: "Le parole giuste. Al momento giusto.",
    desc: "La sessualità fa parte della crescita anche in presenza di disabilità intellettiva, sindrome di Down, autismo o altre condizioni. Informare non significa anticipare: significa proteggere e rendere più autonomi.",
    bullets: ["Corpo, pubertà e cambiamenti", "Privacy, confini e consenso", "Affettività, relazioni e comportamenti", "Prevenzione di abusi e situazioni di rischio"] },
];

const SERVICES = [
  { title: "Supporto psicologico",
    desc: "Per elaborare disagio, cambiamenti, paura del giudizio, autostima e vissuti legati al corpo." },
  { title: "Consulenza sessuologica",
    desc: "Per comprendere desiderio, piacere, difficoltà intime, comunicazione e nuovi modi di vivere la sessualità." },
  { title: "Formazione per genitori e caregiver",
    desc: "Per affrontare crescita, consenso, privacy, affettività, comportamenti e prevenzione con maggiore sicurezza." },
];

const STEPS = [
  { n: "1", title: "Racconta il bisogno", desc: "Compila un breve questionario, in modo riservato." },
  { n: "2", title: "Trova il professionista", desc: "Individuiamo le competenze più adatte alla tua situazione." },
  { n: "3", title: "Incontratevi online", desc: "Parli da un luogo in cui ti senti al sicuro." },
  { n: "4", title: "Costruite il percorso", desc: "Obiettivi e tempi vengono definiti insieme." },
];

const FAQS = [
  { q: "La consulenza è adatta a ogni tipo di disabilità?",
    a: "Sì. Il primo colloquio serve proprio a comprendere la situazione personale — disabilità fisica, sensoriale, intellettiva o neurodivergenza, presente dalla nascita o acquisita. Il percorso viene poi definito in modo individuale, con linguaggi, strumenti e obiettivi calibrati sulla persona." },
  { q: "Posso partecipare insieme al mio partner?",
    a: "Certamente. Molti percorsi sono pensati proprio per la coppia. Puoi iniziare da solo/a e coinvolgere il partner in un secondo momento, oppure fare il primo colloquio insieme fin dall'inizio: lo decidete voi con il professionista." },
  { q: "Come funziona per i genitori?",
    a: "I genitori possono chiedere un percorso dedicato senza che il figlio/la figlia debba partecipare. L'obiettivo è darvi strumenti concreti su corpo, pubertà, privacy, consenso e affettività, calibrati sull'età e sulla condizione del ragazzo/a." },
  { q: "Si parla anche degli aspetti medici?",
    a: "Il servizio è di natura psicologica, sessuologica ed educativa. Non sostituisce visite mediche, urologiche o riabilitative. Se emergono aspetti sanitari, il professionista ti indirizzerà agli specialisti competenti." },
  { q: "La consulenza online è riservata?",
    a: "Sì. Le videochiamate avvengono su una piattaforma protetta con link personale, senza salvataggio della sessione. Il professionista è tenuto al segreto professionale come in studio, e i tuoi dati sono trattati secondo il GDPR." },
  { q: "Mio figlio o mia figlia deve partecipare?",
    a: "No, non è obbligatorio. Il percorso può essere rivolto solo a te come genitore. Se in un secondo momento è utile coinvolgerlo/a, la modalità viene concordata insieme, sempre rispettando i suoi tempi e la sua sensibilità." },
];

export default function SessualitaDisabilitaPage() {
  const [openFaq, setOpenFaq] = useState(null);
  const [ambassadors, setAmbassadors] = useState([]);
  const [openAmb, setOpenAmb] = useState(null);

  useEffect(() => {
    axios.get(`${API}/public/ambassadors`).then((r) => setAmbassadors(r.data || [])).catch(() => {});
  }, []);

  return (
    <div data-testid="sessualita-disabilita-page" className="relative bg-transparent text-[#0A0A0A] overflow-hidden">
      {/* Decorative background blur (matches ChiSiamoPage aesthetic) */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute -top-32 -left-32 w-[600px] h-[600px] rounded-full bg-[#F58A1F]/10 blur-3xl" />
        <div className="absolute top-1/3 -right-32 w-[700px] h-[700px] rounded-full bg-[#6B8FA3]/15 blur-3xl" />
        <div className="absolute bottom-0 left-1/4 w-[500px] h-[500px] rounded-full bg-[#E9D628]/15 blur-3xl" />
      </div>

      {/* Hero */}
      <section className="relative max-w-6xl mx-auto px-6 pt-16 pb-20 md:pt-24 md:pb-28">
        <div className="grid md:grid-cols-2 gap-10 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F58A1F]/15 text-[#F58A1F] text-xs font-medium tracking-wide uppercase mb-6">
              <Sparkles className="w-3.5 h-3.5" /> Un percorso dedicato
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold font-[Outfit] leading-[1.05] mb-4">
              Sessualità e disabilità.
            </h1>
            <p className="text-xl md:text-2xl font-serif text-[#0A0A0A]/75 italic mb-6">
              Uno spazio competente per parlarne davvero.
            </p>
            <p className="text-base text-[#0A0A0A]/75 leading-relaxed mb-8 max-w-lg">
              La sessualità non scompare con una diagnosi, un trauma o una perdita funzionale.
              Può cambiare — e può essere riscoperta con informazioni corrette, ascolto e sostegno.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                data-testid="hero-cta-percorsi"
                to="#percorsi"
                onClick={(e) => { e.preventDefault(); document.getElementById("percorsi")?.scrollIntoView({ behavior: "smooth" }); }}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white font-medium transition-colors"
              >
                Trova il percorso adatto <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                data-testid="hero-cta-questionario"
                to="/questionario"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold transition-colors shadow-md"
              >
                Inizia il questionario
              </Link>
            </div>
          </div>
          <div className="relative flex items-center justify-center">
            <Mascotte name="abbraccio" size={340} animation="breathe" alt="Un abbraccio simbolico di sostegno" />
          </div>
        </div>
      </section>

      {/* 3 Bisogni */}
      <section id="percorsi" className="relative max-w-6xl mx-auto px-6 py-16 md:py-20">
        <div className="text-center mb-12">
          <div className="text-xs uppercase tracking-widest text-[#F58A1F] font-semibold mb-3">Da dove vuoi iniziare?</div>
          <h2 className="text-3xl md:text-4xl font-bold font-[Outfit] mb-4">Tre bisogni. Tre porte d&apos;ingresso.</h2>
          <p className="text-[#0A0A0A]/65 max-w-xl mx-auto">
            Non serve sapere già cosa chiedere. Scegli il punto di vista che ti somiglia di più:
            il resto si costruisce insieme.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {NEEDS.map((n, i) => {
            const mascots = ["pensativo", "coppia", "sereno"];
            return (
              <a
                key={n.key} href={`#dettaglio-${n.key}`}
                data-testid={`need-card-${n.key}`}
                className="group bg-white/70 backdrop-blur-sm border border-[#0A0A0A]/10 rounded-3xl p-6 hover:border-[#F58A1F] hover:shadow-md hover:bg-white transition-all"
              >
                <div className="flex items-start justify-between mb-4">
                  <span className="text-xs text-[#0A0A0A]/40 tracking-widest">{n.n}</span>
                  <Mascotte name={mascots[i]} size={80} animation="float" />
                </div>
                <h3 className="font-serif text-2xl mb-3">{n.title}</h3>
                <p className="text-sm text-[#0A0A0A]/70 leading-relaxed mb-4">{n.desc}</p>
                <div className="text-sm font-medium text-[#0A0A0A] group-hover:text-[#F58A1F] inline-flex items-center gap-1">
                  Approfondisci <ChevronRight className="w-4 h-4" />
                </div>
              </a>
            );
          })}
        </div>
      </section>

      {/* Preoccupazioni comuni */}
      <section className="relative bg-[#0A0A0A] text-white py-16 md:py-20">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold font-[Outfit] mb-3">
            Quando qualcosa cambia, non devi capirlo da solo.
          </h2>
          <p className="text-white/70 mb-10 max-w-2xl">
            La disabilità può essere presente dalla nascita o comparire dopo un trauma, una malattia
            o un cambiamento funzionale. Ogni esperienza è diversa.
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {["Paura del rifiuto o del giudizio",
              "Difficoltà a parlarne in coppia",
              "Confusione tra cura e relazione",
              "Dubbi su autonomia, confini e consenso"].map((c) => (
              <div key={c} className="flex items-start gap-3 p-4 border border-white/15 rounded-2xl">
                <div className="w-2 h-2 mt-2 rounded-full bg-[#F58A1F] flex-shrink-0" />
                <span className="text-white/90">{c}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tipologie */}
      <section className="relative max-w-6xl mx-auto px-6 py-16 md:py-20">
        <div className="text-center mb-12">
          <div className="text-xs uppercase tracking-widest text-[#F58A1F] font-semibold mb-3">Un tema, esperienze diverse</div>
          <h2 className="text-3xl md:text-4xl font-bold font-[Outfit] mb-4">Non esiste un solo modo di vivere la disabilità</h2>
          <p className="text-[#0A0A0A]/65 max-w-2xl mx-auto">
            Il sostegno parte dalla storia personale, non dall&apos;etichetta diagnostica.
            Consideriamo come e quando è comparsa la disabilità, il suo impatto sul corpo,
            sull&apos;autonomia e sulle relazioni.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {DISABILITY_TYPES.map((t) => (
            <div key={t.title} className="bg-white/70 backdrop-blur-sm border border-[#0A0A0A]/10 rounded-2xl p-5 hover:bg-white transition-colors">
              <t.icon className="w-7 h-7 text-[#6B8FA3] mb-3" />
              <h3 className="font-semibold mb-2">{t.title}</h3>
              <p className="text-xs text-[#0A0A0A]/65 leading-relaxed">{t.desc}</p>
            </div>
          ))}
        </div>
        <p className="text-center text-sm text-[#0A0A0A]/55 mt-8 italic max-w-2xl mx-auto">
          Il professionista adatta linguaggio, obiettivi e modalità di lavoro alle esigenze della persona e della famiglia.
        </p>
      </section>

      {/* Deep paths */}
      {DEEP_PATHS.map((p, i) => (
        <section
          key={p.key} id={`dettaglio-${p.key === "persona" ? "per-me" : p.key === "coppia" ? "per-la-coppia" : "come-genitore"}`}
          className={`relative py-16 md:py-20 ${i % 2 === 0 ? "bg-white/40 backdrop-blur-sm" : ""}`}
        >
          <div className="max-w-4xl mx-auto px-6 grid md:grid-cols-[1fr_180px] gap-8 items-center">
            <div>
              <div className="text-xs text-[#0A0A0A]/40 mb-3 tracking-widest">{p.n} · {p.title.toUpperCase()}</div>
              <h2 className="text-3xl md:text-4xl font-bold font-[Outfit] mb-4">{p.subtitle}</h2>
              <p className="text-[#0A0A0A]/75 leading-relaxed mb-8">{p.desc}</p>
              <ul className="space-y-3">
                {p.bullets.map((b) => (
                  <li key={b} className="flex items-start gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#F58A1F] mt-2.5 flex-shrink-0" />
                    <span className="text-[#0A0A0A]/85">{b}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="hidden md:flex justify-center">
              <Mascotte
                name={p.key === "persona" ? "pensativo" : p.key === "coppia" ? "coppia" : "sereno"}
                size={170}
                animation={p.key === "coppia" ? "wiggle" : "float"}
              />
            </div>
          </div>
        </section>
      ))}

      {/* Che cosa puoi trovare */}
      <section className="relative max-w-6xl mx-auto px-6 py-16 md:py-20">
        <div className="text-center mb-12">
          <div className="text-xs uppercase tracking-widest text-[#F58A1F] font-semibold mb-3">Che cosa puoi trovare</div>
          <h2 className="text-3xl md:text-4xl font-bold font-[Outfit] mb-4">Ascolto, orientamento e strumenti concreti.</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {SERVICES.map((s) => (
            <div key={s.title} className="bg-white/70 backdrop-blur-sm border border-[#0A0A0A]/10 rounded-3xl p-6 hover:bg-white transition-colors">
              <MessageCircleHeart className="w-8 h-8 text-[#F58A1F] mb-4" />
              <h3 className="font-semibold mb-3">{s.title}</h3>
              <p className="text-sm text-[#0A0A0A]/70 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
        <div className="text-center mt-10 flex items-center justify-center gap-2 text-sm text-[#0A0A0A]/65">
          <Lock className="w-4 h-4" />
          Professionisti iscritti all&apos;Albo. Incontri online, riservati e senza giudizio, individuali o di coppia.
        </div>
      </section>

      {/* Come funziona */}
      <section className="relative bg-white/40 backdrop-blur-sm py-16 md:py-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-12">
            <div className="text-xs uppercase tracking-widest text-[#F58A1F] font-semibold mb-3">Come funziona</div>
            <h2 className="text-3xl md:text-4xl font-bold font-[Outfit] mb-4">Un primo passo semplice. Senza imbarazzo.</h2>
            <p className="text-[#0A0A0A]/65 max-w-xl mx-auto">
              Non devi preparare un discorso perfetto. Basta partire da ciò che oggi pesa, confonde o manca.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-6">
            {STEPS.map((s) => (
              <div key={s.n} className="text-center">
                <div className="w-12 h-12 mx-auto rounded-full bg-[#0A0A0A] text-white font-bold flex items-center justify-center mb-4">{s.n}</div>
                <h4 className="font-semibold mb-2">{s.title}</h4>
                <p className="text-sm text-[#0A0A0A]/65">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Ambassadors */}
      <section className="relative max-w-6xl mx-auto px-6 py-16 md:py-20">
        <div className="text-center mb-12">
          <div className="text-xs uppercase tracking-widest text-[#F58A1F] font-semibold mb-3">Voci che aprono la conversazione</div>
          <h2 className="text-3xl md:text-4xl font-bold font-[Outfit] mb-4">
            L&apos;esperienza diretta può aiutare altre persone a parlarne.
          </h2>
          <p className="text-[#0A0A0A]/65 max-w-2xl mx-auto">
            Atleti paralimpici e persone con disabilità sostengono questa pagina come ambassador
            della conversazione: non come esperti clinici, ma come voci capaci di normalizzare il tema.
          </p>
        </div>

        {ambassadors.length === 0 ? (
          <div data-testid="ambassadors-empty" className="text-center py-12 bg-white/60 backdrop-blur-sm border border-[#0A0A0A]/10 rounded-3xl max-w-xl mx-auto">
            <div className="flex justify-center mb-3">
              <Mascotte name="saltitante" size={100} animation="wiggle" />
            </div>
            <p className="font-medium text-[#0A0A0A]">Stiamo raccogliendo le prime voci.</p>
            <p className="text-sm text-[#0A0A0A]/60 mt-2">Se vuoi condividere la tua esperienza, scrivici a <a className="underline hover:text-[#0A0A0A]" href="mailto:hr@funzionabene.it">hr@funzionabene.it</a>.</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
            {ambassadors.map((a) => (
              <button
                key={a.id}
                data-testid={`ambassador-card-${a.id}`}
                onClick={() => setOpenAmb(a)}
                className="text-left bg-white/70 backdrop-blur-sm border border-[#0A0A0A]/10 rounded-3xl overflow-hidden hover:shadow-lg hover:border-[#F58A1F] hover:bg-white transition-all"
              >
                {a.foto_url ? (
                  <img src={a.foto_url} alt={a.nome} className="w-full h-56 object-cover" loading="lazy" />
                ) : (
                  <div className="w-full h-56 bg-gradient-to-br from-[#F58A1F]/20 to-[#E9D628]/20 flex items-center justify-center">
                    <span className="font-serif text-4xl text-[#0A0A0A]/40">{a.nome?.[0]}</span>
                  </div>
                )}
                <div className="p-5">
                  <h4 className="font-semibold">{a.nome}</h4>
                  <div className="text-xs text-[#F58A1F] uppercase tracking-wide mb-3">{a.ruolo}</div>
                  <p className="text-sm text-[#0A0A0A]/70 italic leading-relaxed">«{a.testimonianza}»</p>
                  {a.storia && (
                    <div className="text-xs text-[#0A0A0A]/50 mt-3 inline-flex items-center gap-1">
                      Leggi la storia <ChevronRight className="w-3 h-3" />
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* FAQ */}
      <section className="relative bg-white/40 backdrop-blur-sm py-16 md:py-20">
        <div className="max-w-3xl mx-auto px-6">
          <div className="text-center mb-10">
            <div className="text-xs uppercase tracking-widest text-[#F58A1F] font-semibold mb-3">Domande frequenti</div>
            <h2 className="text-3xl md:text-4xl font-bold font-[Outfit] mb-3">Domande che è normale avere.</h2>
            <p className="text-[#0A0A0A]/65">Nessun tema è troppo piccolo, strano o imbarazzante per essere affrontato con rispetto.</p>
          </div>
          <div className="space-y-2">
            {FAQS.map((f, i) => (
              <div key={i} className="bg-white/80 backdrop-blur-sm border border-[#0A0A0A]/10 rounded-2xl overflow-hidden">
                <button
                  data-testid={`faq-toggle-${i}`}
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between p-5 text-left hover:bg-white"
                >
                  <span className="font-medium">{f.q}</span>
                  <ChevronDown className={`w-5 h-5 text-[#0A0A0A]/50 transition-transform ${openFaq === i ? "rotate-180" : ""}`} />
                </button>
                {openFaq === i && (
                  <div className="px-5 pb-5 text-sm text-[#0A0A0A]/75 leading-relaxed">{f.a}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative py-20 md:py-24 bg-gradient-to-br from-[#F58A1F] to-[#E9D628]">
        <div className="max-w-3xl mx-auto text-center px-6 relative z-10">
          <h2 className="text-3xl md:text-5xl font-bold font-[Outfit] text-[#0A0A0A] mb-4 leading-tight">
            La sessualità è parte della vita.
            <br /><span className="italic font-serif font-normal">Anche quando la vita cambia.</span>
          </h2>
          <p className="text-[#0A0A0A]/75 mb-8 max-w-xl mx-auto">
            Trova uno spazio professionale, riservato e senza giudizio.
          </p>
          <Link
            data-testid="final-cta"
            to="/questionario"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white font-medium text-lg transition-colors"
          >
            Inizia il Questionario <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Disclaimer */}
      <section className="relative bg-[#0A0A0A] text-white/70 py-10">
        <div className="max-w-3xl mx-auto px-6 text-center text-sm">
          <p className="font-semibold text-white mb-2">Importante</p>
          <p>
            Il servizio offre consulenza psicologica, sessuologica ed educativa online.
            Non offre assistenza sessuale né sostituisce visite o trattamenti medici.
          </p>
        </div>
      </section>

      {/* Ambassador story modal */}
      {openAmb && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setOpenAmb(null)}>
          <div
            data-testid="ambassador-story-modal"
            className="bg-white rounded-3xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {openAmb.foto_url && (
              <img src={openAmb.foto_url} alt={openAmb.nome} className="w-full h-64 object-cover rounded-t-3xl" />
            )}
            <div className="p-8">
              <h3 className="text-2xl font-bold font-[Outfit]">{openAmb.nome}</h3>
              <div className="text-sm text-[#F58A1F] uppercase tracking-wide mb-4">{openAmb.ruolo}</div>
              <p className="italic text-[#0A0A0A]/75 mb-6 border-l-2 border-[#F58A1F] pl-4">«{openAmb.testimonianza}»</p>
              <div className="text-[#0A0A0A]/80 leading-relaxed whitespace-pre-wrap">{openAmb.storia}</div>
              <button
                onClick={() => setOpenAmb(null)}
                className="mt-8 px-5 py-2 rounded-full bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white"
              >
                Chiudi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
