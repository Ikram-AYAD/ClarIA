import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

interface ParsedPage {
  page: number | null;
  text: string;
}

async function parsePdf(buffer: Buffer): Promise<ParsedPage[]> {
  const { extractText, getDocumentProxy } = await import("unpdf");
  const pdf = await getDocumentProxy(new Uint8Array(buffer));
  const { text } = await extractText(pdf, { mergePages: false });
  const pages = Array.isArray(text) ? text : [text];
  return pages.map((pageText, i) => ({ page: i + 1, text: pageText }));
}

async function parseDocx(buffer: Buffer): Promise<ParsedPage[]> {
  const mammoth = await import("mammoth");
  const result = await mammoth.extractRawText({ buffer });
  return [{ page: null, text: result.value }];
}

function parseTxt(buffer: Buffer): ParsedPage[] {
  const text = buffer.toString("utf-8");
  return [{ page: null, text }];
}

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File | null;
    if (!file) {
      return NextResponse.json({ error: "Aucun fichier fourni." }, { status: 400 });
    }

    const name = file.name;
    const ext = name.split(".").pop()?.toLowerCase();
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    let pages: ParsedPage[];
    if (ext === "pdf") {
      pages = await parsePdf(buffer);
    } else if (ext === "docx") {
      pages = await parseDocx(buffer);
    } else if (ext === "txt") {
      pages = parseTxt(buffer);
    } else {
      return NextResponse.json(
        { error: `Type de fichier non pris en charge : '.${ext}'. Formats acceptés : pdf, docx, txt.` },
        { status: 400 }
      );
    }

    const nonEmptyPages = pages.filter((p) => p.text && p.text.trim().length > 0);

    if (nonEmptyPages.length === 0) {
      return NextResponse.json(
        {
          error:
            "Aucun texte exploitable trouvé dans ce document. S'il s'agit d'un PDF scanné (image), l'OCR n'est pas encore pris en charge dans cette version web.",
        },
        { status: 422 }
      );
    }

    return NextResponse.json({ pages: nonEmptyPages });
  } catch (err: any) {
    return NextResponse.json(
      { error: `Erreur lors de la lecture du document : ${err?.message ?? err}` },
      { status: 500 }
    );
  }
}
