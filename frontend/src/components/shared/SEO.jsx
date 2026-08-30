import { Helmet } from "react-helmet-async";

const SITE = "https://funzionabene.it";
const DEFAULT_IMAGE = `${SITE}/assets/logo.png`;

/**
 * SEO — per-page meta tags. Wraps react-helmet-async.
 * Usage:
 *   <SEO title="…" description="…" path="/xxx" jsonLd={…} />
 */
export default function SEO({ title, description, path = "/", image = DEFAULT_IMAGE, noindex = false, jsonLd = null }) {
  const url = `${SITE}${path}`;
  const fullTitle = title ? `${title} — FunzionaBene` : "FunzionaBene — Psicologi e Sessuologi Online";
  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={url} />
      {noindex && <meta name="robots" content="noindex,nofollow" />}
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={url} />
      <meta property="og:image" content={image} />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={image} />
      {jsonLd && (
        <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
      )}
    </Helmet>
  );
}
