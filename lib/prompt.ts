import type { SearchResult } from "./search";

export const SYSTEM_PROMPT = `Tu es ClarIA, un assistant documentaire rigoureux. Tu réponds UNIQUEMENT à partir des extraits de documents fournis dans le contexte ci-dessous.

Règles strictes, non négociables :
1. N'utilise aucune connaissance externe au contexte fourni, même si tu penses connaître la réponse.
2. Si l'information demandée ne figure pas dans le contexte, réponds explicitement : "Je ne trouve pas cette information dans les documents fournis." Ne comble jamais un manque d'information par une supposition.
3. Chaque affirmation factuelle doit citer l'extrait source utilisé, au format : [Source : nom_du_document, extrait ou page].
4. N'invente jamais de chiffre, de nom, de date ou de citation.
5. Réponds dans la même langue que la question posée.
6. Sois concis et précis ; structure ta réponse si plusieurs points sont abordés.`;

export const WEB_SYSTEM_SUFFIX = `

Si, et seulement si, le contexte documentaire ci-dessus ne contient pas la réponse, tu peux utiliser les résultats de recherche web fournis sous l'étiquette [RESULTATS WEB]. Dans ce cas, indique très clairement au début de ta réponse que l'information provient du web et non des documents fournis par l'utilisateur, et cite la source web (titre / URL).`;

export const NO_INFO_PHRASE =
  "Je ne trouve pas cette information dans les documents fournis.";

export function formatContext(results: SearchResult[]): string {
  return results
    .map((r, i) => {
      const loc = r.chunk.page ? `, page ${r.chunk.page}` : "";
      return `[Extrait ${i + 1} - ${r.chunk.docName}${loc} - similarité=${r.score.toFixed(
        2
      )}]\n${r.chunk.text}`;
    })
    .join("\n\n");
}

export interface WebResult {
  title: string;
  url: string;
  snippet: string;
}

export interface ChatApiMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export function buildMessages(
  query: string,
  results: SearchResult[],
  history: ChatApiMessage[],
  webResults: WebResult[]
): ChatApiMessage[] {
  let context = formatContext(results);
  if (!context) context = "(Aucun extrait pertinent trouvé dans les documents indexés.)";

  let systemPrompt = SYSTEM_PROMPT;
  let webBlock = "";
  if (webResults.length > 0) {
    systemPrompt += WEB_SYSTEM_SUFFIX;
    const webLines = webResults.map(
      (r, i) => `[Résultat web ${i + 1}] ${r.title} (${r.url})\n${r.snippet}`
    );
    webBlock = "\n\n[RESULTATS WEB]\n" + webLines.join("\n\n");
  }

  const userContent = `Contexte documentaire :\n${context}${webBlock}\n\nQuestion : ${query}\n\nRéponds en te basant strictement sur le contexte ci-dessus et cite l'extrait utilisé pour chaque affirmation.`;

  return [
    { role: "system", content: systemPrompt },
    ...history,
    { role: "user", content: userContent },
  ];
}
