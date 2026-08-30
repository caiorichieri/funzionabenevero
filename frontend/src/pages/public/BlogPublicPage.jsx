import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import PrenotaSubitoCTA from "@/components/public/PrenotaSubitoCTA";
import { motion } from "framer-motion";
import { ArrowRight, Calendar, User } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";
import SEO from "@/components/shared/SEO";

function formatDate(d) {
  if (!d) return "";
  try {
    return new Date(d).toLocaleDateString("it-IT", { year: "numeric", month: "long", day: "numeric" });
  } catch { return ""; }
}

function stripHtml(html) {
  if (!html) return "";
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

export default function BlogPublicPage() {
  const [articoli, setArticoli] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/public/blog`)
      .then(r => setArticoli(r.data))
      .catch(() => setArticoli([]))
      .finally(() => setLoading(false));
  }, []);

  const [hero, ...rest] = articoli;

  return (
    <main className="min-h-[calc(100vh-80px)] bg-transparent py-16 lg:py-24" data-testid="blog-page">
      <SEO
        title="Rivista — Sessuologia, coppia, benessere"
        description="Articoli e ricerche dai nostri sessuologi e psicologi: intimità, desiderio, coppia, disfunzioni, identità e piacere. Sempre rigorosi, mai sensazionalisti."
        path="/blog"
      />
      <div className="max-w-7xl mx-auto px-6 lg:px-10">
        <div className="mb-16 max-w-2xl">
          <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Rivista</span>
          <h1 className="mt-4 font-serif text-5xl lg:text-6xl text-[#0A0A0A] leading-tight">
            Pensieri e ricerche<br />dai nostri specialisti.
          </h1>
          <p className="mt-6 text-[#0A0A0A]/65 text-lg">
            Articoli scritti dai nostri specialisti per aiutarti a comprendere meglio te stesso.
          </p>
        </div>

        {loading && (
          <div className="text-center py-20 text-[#0A0A0A]/50">Caricamento...</div>
        )}

        {!loading && articoli.length === 0 && (
          <div className="py-20 text-center border border-dashed border-[#0A0A0A]/10 rounded-3xl flex flex-col items-center gap-6" data-testid="blog-empty">
            <Mascotte name="ovo" theme="light" size={140} animation="float" />
            <p className="text-[#0A0A0A]/60 max-w-md">Nessun articolo pubblicato al momento. Torna presto — i nostri specialisti stanno scrivendo per te.</p>
          </div>
        )}

        {hero && (
          <motion.article
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            data-testid="blog-hero"
            className="mb-16 grid md:grid-cols-[1.1fr_1fr] gap-0 bg-gradient-to-br from-[#0A0A0A] via-[#0A0A0A]/12 to-white border border-[#0A0A0A]/10 rounded-3xl overflow-hidden"
          >
            {hero.immagine_url && (
              <Link to={`/blog/${hero._id}`} className="relative aspect-[4/3] md:aspect-auto overflow-hidden block group">
                <img
                  src={hero.immagine_url}
                  alt=""
                  loading="eager"
                  className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-r from-transparent to-white/80 md:to-white" />
              </Link>
            )}
            <div className="relative p-10 lg:p-14 flex flex-col justify-center">
              <div className="absolute -top-20 -right-20 w-[400px] h-[400px] rounded-full bg-white/12 blur-3xl" />
              <div className="relative">
                {hero.categoria && (
                  <span className="text-xs tracking-[0.25em] uppercase text-[#0A0A0A]">{hero.categoria}</span>
                )}
                <h2 className="mt-4 font-serif text-3xl lg:text-4xl xl:text-5xl text-[#0A0A0A] leading-tight">
                  {hero.titolo}
                </h2>
                <p className="mt-6 text-[#0A0A0A]/75 text-base lg:text-lg leading-relaxed line-clamp-3">
                  {stripHtml(hero.contenuto).slice(0, 240)}…
                </p>
                <div className="mt-8 flex items-center gap-6 text-xs text-[#0A0A0A]/60">
                  <span className="flex items-center gap-2"><User className="w-3.5 h-3.5" />{hero.autore_nome}</span>
                  <span className="flex items-center gap-2"><Calendar className="w-3.5 h-3.5" />{formatDate(hero.created_at)}</span>
                </div>
                <Link
                  to={`/blog/${hero._id}`}
                  data-testid="blog-hero-link"
                  className="mt-8 inline-flex items-center gap-3 px-6 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg text-sm font-medium tracking-wide transition-all"
                >
                  Leggi l&apos;articolo <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </motion.article>
        )}

        {rest.length > 0 && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {rest.map((a, i) => (
              <motion.article
                key={a._id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.4, delay: Math.min(i * 0.05, 0.3) }}
                data-testid={`blog-card-${i}`}
                className="brand-card group flex flex-col overflow-hidden !p-0"
              >
                {a.immagine_url && (
                  <Link to={`/blog/${a._id}`} className="relative aspect-[16/10] overflow-hidden block">
                    <img
                      src={a.immagine_url}
                      alt=""
                      loading="lazy"
                      className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A0A]/10 to-transparent" />
                  </Link>
                )}
                <div className="p-7 flex flex-col flex-1">
                  {a.categoria && (
                    <span className="text-xs tracking-[0.25em] uppercase text-[#6B8FA3] mb-3">{a.categoria}</span>
                  )}
                  <h3 className="font-serif text-xl lg:text-2xl text-[#0A0A0A] leading-tight mb-4">
                    {a.titolo}
                  </h3>
                  <p className="text-sm text-[#0A0A0A]/65 line-clamp-3 mb-6 flex-1">
                    {stripHtml(a.contenuto).slice(0, 160)}…
                  </p>
                  <div className="flex items-center justify-between pt-4 border-t border-[#0A0A0A]/10">
                    <span className="text-xs text-[#0A0A0A]/50">{formatDate(a.created_at)}</span>
                    <Link
                      to={`/blog/${a._id}`}
                      data-testid={`blog-card-link-${i}`}
                      className="text-xs tracking-[0.15em] uppercase text-[#0A0A0A] hover:text-[#0A0A0A]/70"
                    >
                      Leggi →
                    </Link>
                  </div>
                </div>
              </motion.article>
            ))}
          </div>
        )}

        <PrenotaSubitoCTA
          variant="banner"
          testid="blog-list-prenota"
          bannerTitle="Hai un dubbio specifico?"
          bannerCopy="A volte un articolo dà la direzione, ma serve qualcuno che ascolti la tua storia. Prenota una prima sessione."
          mascotName="pensativo"
        />
      </div>
    </main>
  );
}
