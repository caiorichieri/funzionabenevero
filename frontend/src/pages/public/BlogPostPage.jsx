import { sanitizeHtml } from "@/utils/safeHtml";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ArrowLeft, Calendar, User } from "lucide-react";
import PrenotaSubitoCTA from "@/components/public/PrenotaSubitoCTA";
import SEO from "@/components/shared/SEO";

function formatDate(d) {
  if (!d) return "";
  try {
    return new Date(d).toLocaleDateString("it-IT", { year: "numeric", month: "long", day: "numeric" });
  } catch { return ""; }
}

// Content is authored by the admin / seeded from our own HTML source, so inner HTML is safe.
// Only <p>, <strong>, <em> tags are expected.
function hasHtmlMarkup(s) {
  return /<(p|em|strong|br)[\s>/]/i.test(s || "");
}

export default function BlogPostPage() {
  const { id } = useParams();
  const [articolo, setArticolo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/public/blog`).then(r => {
      const found = (r.data || []).find(a => a._id === id);
      setArticolo(found || null);
    }).finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <main className="min-h-[calc(100vh-80px)] bg-transparent flex items-center justify-center text-[#0A0A0A]/50">Caricamento...</main>;
  }

  if (!articolo) {
    return (
      <main className="min-h-[calc(100vh-80px)] bg-transparent flex items-center justify-center px-6" data-testid="blog-not-found">
        <div className="text-center">
          <h1 className="font-serif text-3xl text-[#0A0A0A] mb-4">Articolo non trovato</h1>
          <Link to="/blog" className="text-[#0A0A0A] hover:text-[#0A0A0A]/70">← Torna al blog</Link>
        </div>
      </main>
    );
  }

  const contenuto = articolo.contenuto || "";
  const isHtml = hasHtmlMarkup(contenuto);
  const plainExcerpt = (isHtml ? contenuto.replace(/<[^>]+>/g, " ") : contenuto)
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 160);

  return (
    <main className="min-h-[calc(100vh-80px)] bg-transparent py-16 lg:py-24" data-testid="blog-post">
      <SEO
        title={articolo.titolo}
        description={plainExcerpt || `Articolo di ${articolo.autore_nome || "FunzionaBene"}`}
        path={`/blog/${articolo._id}`}
        image={articolo.immagine_url || undefined}
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "Article",
          "headline": articolo.titolo,
          "description": plainExcerpt,
          "image": articolo.immagine_url ? [articolo.immagine_url] : undefined,
          "datePublished": articolo.created_at,
          "dateModified": articolo.updated_at || articolo.created_at,
          "author": { "@type": "Person", "name": articolo.autore_nome || "FunzionaBene" },
          "publisher": {
            "@type": "Organization",
            "name": "FunzionaBene",
            "logo": { "@type": "ImageObject", "url": "https://funzionabene.it/assets/logo.png" }
          },
          "mainEntityOfPage": { "@type": "WebPage", "@id": `https://funzionabene.it/blog/${articolo._id}` }
        }}
      />
      <article className="max-w-3xl mx-auto px-6 lg:px-10">
        <Link to="/blog" className="inline-flex items-center gap-2 text-sm text-[#0A0A0A]/60 hover:text-[#0A0A0A] mb-10">
          <ArrowLeft className="w-4 h-4" /> Torna al blog
        </Link>

        {articolo.categoria && (
          <span className="text-xs tracking-[0.25em] uppercase text-[#0A0A0A]">{articolo.categoria}</span>
        )}
        <h1 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight">
          {articolo.titolo}
        </h1>

        <div className="mt-8 pb-8 border-b border-[#0A0A0A]/10 flex flex-wrap gap-6 text-sm text-[#0A0A0A]/60">
          <span className="flex items-center gap-2"><User className="w-4 h-4" />{articolo.autore_nome}</span>
          <span className="flex items-center gap-2"><Calendar className="w-4 h-4" />{formatDate(articolo.created_at)}</span>
        </div>

        {articolo.immagine_url && (
          <div className="mt-10 rounded-3xl overflow-hidden border border-[#0A0A0A]/10">
            <img
              src={articolo.immagine_url}
              alt=""
              loading="eager"
              className="w-full h-auto max-h-[520px] object-cover"
              data-testid="blog-post-image"
            />
          </div>
        )}

        {isHtml ? (
          <div
            className="blog-prose mt-10"
            dangerouslySetInnerHTML={{ __html: sanitizeHtml(contenuto) }}
          />
        ) : (
          <div className="mt-10">
            {contenuto.split("\n").filter(Boolean).map((p, i) => (
              <p key={i} className="text-lg text-[#0A0A0A]/75 leading-loose mb-6 font-serif">
                {p}
              </p>
            ))}
          </div>
        )}

        <PrenotaSubitoCTA
          variant="banner"
          testid="blog-post-prenota"
          bannerTitle="Hai letto. Ora, se vuoi, possiamo parlarne."
          bannerCopy="Il primo passo è scegliere un orario. Online, riservato, senza giudizio. La prima sessione è in meno di 48 ore."
          mascotName="abbraccio"
        />

        <div className="mt-8 brand-card !p-8 text-center">
          <h3 className="font-serif text-2xl text-[#0A0A0A] mb-3">Preferisci un percorso guidato?</h3>
          <p className="text-[#0A0A0A]/65 mb-6">Prova il nostro questionario e trova lo specialista giusto per te.</p>
          <Link
            to="/questionario"
            data-testid="blog-post-cta"
            className="inline-flex items-center gap-3 px-6 py-3 border-[1.5px] border-[#0A0A0A] hover:bg-[#0A0A0A] hover:text-white text-[#0A0A0A] rounded-2xl text-sm font-medium tracking-wide transition-all"
          >
            Inizia il questionario
          </Link>
        </div>
      </article>
    </main>
  );
}
