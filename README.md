# ClarIA

ClarIA est un assistant documentaire par IA que j'ai conçu et développé :
tu lui déposes un ou plusieurs documents (PDF, DOCX, TXT), tu lui poses des
questions en langage naturel, et il te répond en se basant **uniquement**
sur le contenu de ces documents — jamais d'invention, toujours avec la
source citée (nom du document, page, extrait). S'il ne trouve pas
l'information, il le dit clairement plutôt que de deviner.

> **Projet personnel — tous droits réservés.** Ce projet m'appartient (Ikram). Toute copie, réutilisation, redistribution ou modification de ce code, en tout ou partie, à des fins personnelles ou commerciales, est interdite sans mon autorisation écrite préalable.

## Ce que fait l'app

- Import de documents par glisser-déposer (PDF, DOCX, TXT), avec extraction
  de texte page par page pour les PDF, pour pouvoir citer précisément la
  source d'une réponse.
- Recherche hybride : similarité sémantique (embeddings) combinée à une
  recherche par mots-clés (BM25), avec un curseur pour ajuster le poids de
  chacune ou utiliser l'un des deux modes seul.
- Réponses générées en streaming (mot par mot), avec un score de confiance
  et les extraits sources affichés à côté de chaque réponse.
- Résumé automatique de chaque document, généré juste après son indexation.
- Historique de conversations : plusieurs conversations peuvent être
  sauvegardées, renommées, rechargées ou supprimées.
- Un tableau de bord qui suit l'usage en temps réel : nombre de questions,
  taux de réponses sourcées, confiance moyenne, documents les plus
  consultés, temps de réponse.
- Tout se passe dans le navigateur : les documents et leurs embeddings sont
  stockés en local (IndexedDB), pas sur un serveur. Le backend ne fait que
  relayer les appels aux API (Groq pour la génération, Hugging Face pour
  les embeddings) sans jamais conserver le contenu des documents.

## Pourquoi Next.js plutôt que Python

La première version de ClarIA était en Python (Streamlit), hébergée sur
Streamlit Community Cloud. Le tier gratuit limite chaque app à 1 Go de RAM,
ce qui provoquait des plantages récurrents — même après avoir remplacé les
embeddings calculés localement (torch/sentence-transformers) par un appel à
l'API d'inférence Hugging Face pour alléger l'app. Le problème restait
là : un process qui tourne en continu, avec une pile Python (pandas,
pyarrow, faiss, pymupdf...) trop lourde pour ce plafond.

J'ai donc tout réécrit en Next.js. Il n'y a plus de serveur qui tourne en
permanence : chaque action (lire un document, calculer des embeddings,
générer une réponse) passe par une fonction serverless, courte et sans
état, et les documents restent côté client. Ça règle le problème de RAM à
la racine, et ça se déploie gratuitement sur Vercel sans surprise.

## Architecture

```
app/
  page.tsx              interface principale (chat + tableau de bord)
  api/
    parse/route.ts      extraction de texte (PDF via unpdf, DOCX via mammoth, TXT)
    embed/route.ts      proxy vers l'API d'inférence Hugging Face (embeddings)
    chat/route.ts       proxy streaming vers l'API Groq (génération)
    summarize/route.ts  résumé automatique de document (Groq)
lib/
  chunk.ts              découpage des documents en chunks avec chevauchement
  search.ts             similarité cosinus + BM25 + recherche hybride
  analytics.ts          agrégation des statistiques d'usage
  prompt.ts             construction du prompt RAG
  db.ts                 persistance locale (IndexedDB)
hooks/
  useClaria.ts           état global de l'app
components/
  Sidebar, Uploader, ChatWindow, MessageBubble, Dashboard, ...
```

Les clés API (`GROQ_API_KEY`, `HF_TOKEN`) ne sont lues que côté serveur,
dans les routes `app/api/*` — elles ne sont jamais envoyées au navigateur.

## Lancer le projet en local

```bash
npm install
cp .env.example .env.local   # puis renseigne tes clés
npm run dev
```

- Clé API Groq (gratuite) : https://console.groq.com/keys
- Token Hugging Face (gratuit, permission "Inference Providers") :
  https://huggingface.co/settings/tokens/new?ownUserPermissions=inference.serverless.write&tokenType=fineGrained

L'app tourne ensuite sur http://localhost:3000.

## Déployer

1. Pousser le projet sur un repo GitHub.
2. Sur vercel.com → "Add New Project" → importer le repo (Next.js est
   détecté automatiquement, aucune config particulière à faire).
3. Dans Settings → Environment Variables, ajouter `GROQ_API_KEY` et
   `HF_TOKEN`.
4. Déployer. Chaque `git push` sur la branche principale redéploie
   automatiquement.

## Limites connues

- L'OCR des PDF scannés (pages sans couche de texte) n'est pas géré dans
  cette version — Tesseract est un binaire natif peu adapté à un
  environnement serverless. Un tel PDF renvoie une erreur claire plutôt
  qu'un résultat vide.
- La recherche web complémentaire, présente dans la version Python, n'a
  pas été reportée ici pour l'instant.
- Groq et Hugging Face sont gratuits mais soumis à des limites de débit ;
  en cas de pic d'usage une requête peut échouer, l'app affiche alors un
  message d'erreur clair.
