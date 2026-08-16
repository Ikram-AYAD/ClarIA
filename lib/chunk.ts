/**
 * Découpage de texte en chunks avec chevauchement, en respectant les fins
 * de phrase (jamais de coupure au milieu d'une phrase). Portage direct de
 * la logique Python d'origine (rag_core.chunk_text).
 */

const SENTENCE_SPLIT_RE = /(?<=[.!?])\s+/;
const WHITESPACE_RE = /\s+/g;

export function splitIntoSentences(text: string): string[] {
  const normalized = text.replace(WHITESPACE_RE, " ").trim();
  if (!normalized) return [];
  return normalized
    .split(SENTENCE_SPLIT_RE)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function chunkText(
  text: string,
  chunkSize = 800,
  overlap = 150
): string[] {
  if (chunkSize <= 0) throw new Error("chunkSize doit être strictement positif");
  if (overlap < 0 || overlap >= chunkSize) {
    throw new Error("overlap doit être >= 0 et strictement inférieur à chunkSize");
  }

  const sentences = splitIntoSentences(text);
  if (sentences.length === 0) return [];

  const chunks: string[] = [];
  let current: string[] = [];
  let currentLen = 0;
  let i = 0;

  while (i < sentences.length) {
    const sentence = sentences[i];
    const sentenceLen = sentence.length + 1;

    if (current.length > 0 && currentLen + sentenceLen > chunkSize) {
      chunks.push(current.join(" "));

      const overlapSentences: string[] = [];
      let overlapLen = 0;
      for (let j = current.length - 1; j >= 0; j--) {
        overlapLen += current[j].length + 1;
        overlapSentences.unshift(current[j]);
        if (overlapLen >= overlap) break;
      }

      // Garde-fou anti-boucle infinie : si les phrases de `current` sont
      // toutes très courtes, la fenêtre de chevauchement ci-dessus peut
      // finir par reprendre `current` en entier (aucune réduction), ce qui
      // rejouerait indéfiniment la même itération sans jamais avancer `i`.
      // On force alors une progression stricte en retirant au moins la
      // phrase la plus ancienne.
      const nextCurrent =
        overlapSentences.length >= current.length
          ? current.slice(1)
          : overlapSentences;

      current = nextCurrent;
      currentLen = current.reduce((acc, s) => acc + s.length + 1, 0);
      continue;
    }

    current.push(sentence);
    currentLen += sentenceLen;
    i++;
  }

  if (current.length > 0) chunks.push(current.join(" "));
  return chunks;
}

export function tokenize(text: string): string[] {
  const matches = text.toLowerCase().match(/[\p{L}\p{N}_]+/gu);
  return matches ?? [];
}
