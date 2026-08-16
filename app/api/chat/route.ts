import { NextRequest } from "next/server";
import Groq from "groq-sdk";

export const runtime = "nodejs";
export const maxDuration = 60;

const MODEL = "llama-3.1-8b-instant";

export async function POST(req: NextRequest) {
  const apiKey = process.env.GROQ_API_KEY || req.headers.get("x-groq-key") || undefined;
  if (!apiKey) {
    return new Response(
      JSON.stringify({ error: "Aucune clé API Groq configurée." }),
      { status: 400, headers: { "content-type": "application/json" } }
    );
  }

  const { messages } = (await req.json()) as {
    messages: { role: "system" | "user" | "assistant"; content: string }[];
  };

  const groq = new Groq({ apiKey });

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      try {
        const completion = await groq.chat.completions.create({
          model: MODEL,
          messages,
          temperature: 0.1,
          stream: true,
        });

        for await (const chunk of completion) {
          const delta = chunk.choices[0]?.delta?.content;
          if (delta) controller.enqueue(encoder.encode(delta));
        }
        controller.close();
      } catch (err: any) {
        controller.enqueue(
          encoder.encode(
            `\n\n[Erreur lors de l'appel au modèle : ${err?.message ?? err}]`
          )
        );
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
