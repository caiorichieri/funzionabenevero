"""Shared slugify utility — kebab-case, Italian-accent aware, max-len bounded.

Keep this file in sync with the algorithm used in frontend/scripts/generate-sitemap.js
and with the production mapping committed in migrations/blog_slug_migration.py.
"""
import re
import unicodedata


def slugify(text: str, max_len: int = 70) -> str:
    """Normalise an Italian title to a kebab-case slug.

    Rules:
      * NFKD normalisation + strip combining marks → ASCII (à→a, è→e, …)
      * lower-case
      * any run of non-[a-z0-9] → single '-'
      * collapse multiple '-' and strip trailing/leading '-'
      * truncate at `max_len`, snap back to the previous word boundary
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rsplit("-", 1)[0]
    return s


async def make_unique_slug(db, base_title: str, exclude_id=None) -> str:
    """Return a slug for `base_title` that doesn't collide with existing articles.

    Appends `-2`, `-3`, … only on collision. Case where another article has the
    same `_id` (same doc being updated) is excluded via `exclude_id`.
    """
    base = slugify(base_title)
    if not base:
        return ""
    candidate = base
    i = 2
    while True:
        query = {"slug": candidate}
        if exclude_id is not None:
            query["_id"] = {"$ne": exclude_id}
        existing = await db.articoli.find_one(query, {"_id": 1})
        if existing is None:
            return candidate
        candidate = f"{base}-{i}"
        i += 1
