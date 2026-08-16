import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60;

const MODEL = "sentence-transformers/all-MiniLM-L6-v2";
const HF_URL = `https://api-inference.huggingface.co/models/${MODEL}`;
const EMBEDDING_DIM = 384;

function meanPoolIfNeeded(vectors: unknown): number[][] {
  // La réponse peut être soit déjà poolée (array de vecteurs, un par texte),
  // soit "par token" (3D) auquel cas on moyenne sur l'axe des tokens.
  const arr = vectors as any[];
  if (Array.isArray(arr[0]?.[0])) {
    return arr.map((tokenVectors: number[][]) => {
      const dim = tokenVectors[0]?.length ?? EMBEDDING_DIM;
      const summed = new Array(dim).fill(0);
      for (const tok of tokenVectors) {
        for (let i = 0; i < dim; i++) summed[i] += tok[i];
      }
      return summed.map((s) => s / tokenVectors.length);
    });
  }
  return arr as number[][];
}

async function callHf(texts: string[], token: string, maxRetries = 3): Promise<number[][]> {
  let lastError: unknown = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const res = await fetch(HF_URL, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          inputs: texts,
          options: { wait_for_model: true },
        }),
      });

      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`HF API a répondu ${res.status} : ${body.slice(0, 300)}`);
      }

      const data = await res.json();
      if (data?.error) throw new Error(String(data.error));

      return meanPoolIfNeeded(data);
    } catch (err) {
      lastError = err;
      if (attempt < maxRetries - 1) {
        // Un modèle inactif depuis un moment doit parfois être "réveillé" :
        // le premier appel peut échouer/timeout le temps qu'il charge.
        await new Promise((r) => setTimeout(r, Math.min(4000 * (attempt + 1), 10000)));
      }
    }
  }
  throw lastError;
}

export async function POST(req: NextRequest) {
  const token = process.env.HF_TOKEN;
  if (!token) {
    return NextResponse.json(
      { error: "HF_TOKEN manquant côté serveur. Ajoute-le dans les variables d'environnement." },
      { status: 500 }
    );
  }

  try {
    const { texts } = (await req.json()) as { texts: string[] };
    if (!Array.isArray(texts) || texts.length === 0) {
      return NextResponse.json({ error: "'texts' doit être un tableau non vide." }, { status: 400 });
    }

    // L'API d'inférence HF traite des lots raisonnables ; on découpe pour
    // rester robuste sur de gros documents.
    const BATCH_SIZE = 32;
    const embeddings: number[][] = [];
    for (let i = 0; i < texts.length; i += BATCH_SIZE) {
      const batch = texts.slice(i, i + BATCH_SIZE);
      const batchEmbeddings = await callHf(batch, token);
      embeddings.push(...batchEmbeddings);
    }

    return NextResponse.json({ embeddings });
  } catch (err: any) {
    return NextResponse.json(
      {
        error: `Impossible de calculer les embeddings (API Hugging Face indisponible, HF_TOKEN invalide, ou limite de débit atteinte) : ${err?.message ?? err}`,
      },
      { status: 502 }
    );
  }
}
