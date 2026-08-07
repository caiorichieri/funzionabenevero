import DOMPurify from "dompurify";

// Reasonable defaults for our legal / blog content
const CONFIG = {
  ALLOWED_TAGS: [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr", "strong", "em", "u", "s", "small",
    "ul", "ol", "li",
    "a",
    "blockquote", "code", "pre",
    "table", "thead", "tbody", "tr", "th", "td",
    "img", "figure", "figcaption",
    "div", "span",
  ],
  ALLOWED_ATTR: ["href", "target", "rel", "src", "alt", "title", "class", "id"],
  ALLOW_DATA_ATTR: false,
};

/**
 * Sanitize HTML from trusted-ish sources (our own admin CMS, legal docs, blog).
 * Blocks scripts, on* handlers, javascript: URIs, iframes and other XSS vectors.
 */
export function sanitizeHtml(input) {
  if (input == null) return "";
  return DOMPurify.sanitize(String(input), CONFIG);
}

/**
 * Convenience helper to spread into React JSX:
 *   <div {...safeHtml(text)} />
 */
export function safeHtml(input) {
  return { dangerouslySetInnerHTML: { __html: sanitizeHtml(input) } };
}
