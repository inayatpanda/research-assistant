EXTRACTION_PROMPT = """You are extracting bibliographic metadata from a research article.

Return STRICT JSON with these fields (use null when unknown):
{{
  "title": string,
  "authors": [string, ...],
  "journal": string | null,
  "year": integer | null,
  "volume": string | null,
  "issue": string | null,
  "pages": string | null,
  "doi": string | null,
  "confidence": number
}}

Rules:
- Use ONLY the provided article text. Do not invent.
- If the document is not a research article, return {{"title": "UNKNOWN", "authors": [], "confidence": 0.0}}.
- DOI format: "10.xxxx/..." — strip any "doi:" or "https://doi.org/" prefix.
- "authors" MUST be a list of "First Last" strings; never a single comma-joined string.
- "confidence" is YOUR confidence that the title is correct (0.0-1.0).
- Output JSON ONLY. No prose, no markdown fences, no commentary.

ARTICLE TEXT (truncated to first ~6000 chars):
\"\"\"
{text}
\"\"\"

JSON:"""


SUMMARISE_PROMPT = """Summarise the following passage in {max_sentences} sentence(s) or fewer.

Rules:
- Use ONLY the provided passage. Do not invent facts or context.
- If the passage is too short to summarise, respond with: INSUFFICIENT_SOURCE
- Output the summary text only — no prose preamble.

PASSAGE:
\"\"\"
{text}
\"\"\"

Summary:"""
