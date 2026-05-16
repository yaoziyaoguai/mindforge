/**
 * Markdown → safe HTML rendering utility.
 *
 * Backend returns canonical Markdown text. Frontend is the single sanitization
 * point: Markdown → HTML (marked) → safe HTML (DOMPurify).
 *
 * RFC_0002 §6 / SDD_WIKI_PRESENTATION_V2 §7.
 */

import { marked } from "marked";
import DOMPurify from "dompurify";

const ALLOWED_TAGS = [
  "h1", "h2", "h3", "h4", "h5", "h6",
  "p", "br", "hr",
  "ul", "ol", "li",
  "a", "strong", "em", "code", "pre",
  "blockquote",
  "table", "thead", "tbody", "tr", "th", "td",
  "img",
  "details", "summary",
];

const ALLOWED_ATTR = ["href", "title", "src", "alt", "align"];

const FORBID_TAGS = ["script", "style", "iframe", "object", "embed", "form", "input"];
const FORBID_ATTR = ["onclick", "onerror", "onload", "onmouseover", "style"];

export function renderMarkdown(markdown: string): string {
  const raw = marked.parse(markdown, { async: false }) as string;
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    FORBID_TAGS,
    FORBID_ATTR,
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|ftp):|[^:/?#]*(?:[/?#]|$))/i,
  });
}
