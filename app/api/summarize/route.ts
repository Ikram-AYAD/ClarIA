import { NextRequest, NextResponse } from "next/server";
import Groq from "groq-sdk";

export const runtime = "nodejs";
export const maxDuration = 30;

// llama-3.1-8b-instant a été arrêté par Groq le 16/08/2026 (voir
// console.groq.com/docs/deprecations). Remplacement recommandé par Groq :
// openai/gpt-oss-20b.
const MODEL = "openai/gpt-oss-20b";
const MAX_CHARS = 12000;

export async function POST(req: NextRequest) {
  const apiKey = process.env.GROQ_API_KEY || req.headers.get("x-groq-key") || undefined;
  if (!apiKey) {
    return NextResponse.json({ error: "Aucune clé API Groq configurée." }, { status: 400 });
  }

  try {
    const { text, docName } = (await req.json()) as { text: string; docName: string };
    const excerpt = text.slice(0, MAX_CHARS);
    const truncatedNote =
      text.length > MAX_CHARS
        ? "\n\n(Note : le document a été tronqué pour le résumé car il est très long.)"
        : "";

    const groq = new Groq({ apiKey });
    const completion = await groq.chat.completions.create({
      model: MODEL,
      temperature: 0.2,
      stream: false,
      messages: [
        {
          role: "system",
          content:
            "Tu rédiges des résumés clairs, fidèles et neutres de documents, en français. Tu ne dois jamais ajouter d'information absente du texte fourni.",
        },
        {
          role: "user",
          content: `Résume le document suivant ('${docName}') en 5 à 8 phrases, en dégageant les points clés et la structure générale :\n\n${excerpt}${truncatedNote}`,
        },
      ],
    });

    return NextResponse.json({ summary: completion.choices[0]?.message?.content ?? "" });
  } catch (err: any) {
    return NextResponse.json(
      { error: `Résumé indisponible : ${err?.message ?? err}` },
      { status: 500 }
    );
  }
}
