# ClarIA

**ClarIA** est un assistant documentaire par IA (RAG — *Retrieval-Augmented
Generation*) : dépose un ou plusieurs documents (PDF, DOCX, TXT), pose des
questions en langage naturel, et obtiens des réponses **basées uniquement
sur le contenu de tes documents**, avec citation systématique de l'extrait
source. Si l'information ne s'y trouve pas, ClarIA le dit clairement — sans
jamais inventer.

> **Projet personnel — tous droits réservés.** Ce projet appartient à Ikram. Toute copie, réutilisation, redistribution, modification ou exploitation de ce code, en tout ou partie, à des fins personnelles ou commerciales, est interdite sans autorisation écrite préalable de l'auteur.

## Fonctionnalités

- Import de documents PDF, DOCX et TXT (extraction robuste, y compris
  tableaux Word et texte multi-pages).
- **OCR automatique** pour les PDF scannés : toute page sans couche de
  texte native est détectée et passée à la reconnaissance optique de
  caractères (PyMuPDF + Tesseract), avec repli silencieux si l'OCR n'est
  pas disponible sur la machine.
- Découpage en chunks avec chevauchement, toujours aligné sur les fins de
  phrase (jamais de coupe au milieu d'une phrase).
- Embeddings locaux et gratuits (`sentence-transformers`, modèle
  `all-MiniLM-L6-v2`) : aucune clé API requise pour l'indexation.
- **Recherche hybride** : similarité cosinus (FAISS `IndexFlatIP`) combinée
  à une recherche par mots-clés (BM25), pour retrouver aussi bien le sens
  général d'une question que les termes exacts (noms propres, chiffres,
  références). Modes semantique seule / mots-clés seuls / hybride
  sélectionnables, avec un curseur de pondération.
- **Gestion fine des documents indexés** : chaque document peut être
  retiré individuellement de l'index (sans tout réindexer), utile en
  travaillant avec plusieurs fichiers.
- Génération des réponses via l'API **Groq** gratuite
  (`llama-3.1-8b-instant`), avec un prompt qui interdit explicitement toute
  réponse hors du contexte fourni et impose la citation des extraits
  utilisés.
- Réponses affichées **en streaming** (mot par mot).
- **Résumé automatique** de chaque document juste après son indexation.
- **Export PDF** de la conversation courante (questions, réponses, sources
  citées, score de confiance) via ReportLab.
- **Historique multi-conversations** : sauvegarde, rechargement et
  suppression de plusieurs conversations distinctes (fichiers JSON
  locaux), en plus de l'export PDF ponctuel.
- **Métriques quantifiées, pensées pour un usage en entreprise :**
  - Un **score de confiance** (Fort / Moyen / Faible) est affiché sous
    chaque réponse, calculé à partir de la pertinence des extraits
    utilisés.
  - Un **tableau de bord d'usage** (onglet dédié) affiche : nombre de
    questions posées, taux de réponses sourcées vs "information non
    trouvée", confiance moyenne, temps de réponse moyen, répartition de la
    confiance, documents les plus consultés, nombre d'appels à l'API Groq
    et volume de tokens estimé.
  - **Export CSV et Excel** de l'historique détaillé des questions/réponses
    (avec une feuille de synthèse dans le classeur Excel), prêt pour un
    reporting ou une analyse dans un tableur.
- Interface **Streamlit** avec chat multi-tours, thème personnalisé (police Inter,
  cartes de documents avec icônes par type de fichier, badges de confiance
  colorés, écrans d'accueil vides guidés).
- **Bonus — recherche web complémentaire** (optionnelle, désactivée par
  défaut) : si l'information n'est pas dans tes documents, ClarIA peut
  chercher sur le web (DuckDuckGo, sans clé API) et l'indique alors
  explicitement dans sa réponse, en distinguant clairement source web et
  source documentaire.

## Architecture

```
ClarIA/
├── app.py                  # Interface Streamlit (assemble tout le reste)
├── rag_core.py              # Chunking, index hybride (FAISS+BM25), prompt, appels Groq, résumé
├── document_loader.py        # Extraction de texte PDF / DOCX / TXT + OCR
├── pdf_export.py             # Export de la conversation courante en PDF
├── conversation_store.py     # Sauvegarde / chargement multi-conversations (JSON)
├── analytics.py              # Score de confiance + agrégation de statistiques d'usage
├── stats_export.py           # Export des statistiques en CSV / Excel
├── ui_theme.py                # CSS personnalisé, icônes, badges de confiance, états vides
├── assets/
│   ├── logo.svg               # Logo ClarIA (intégré dans la bannière et la barre latérale)
│   └── logo.png                # Version rasterisée du logo, utilisée comme favicon
├── tests/
│   ├── test_rag_core.py            # Chunking, recherche hybride, suppression de document, prompt
│   ├── test_document_loader.py     # Extraction PDF/DOCX/TXT + OCR (fichiers générés à la volée)
│   ├── test_pdf_export.py          # Validité du PDF exporté (contenu + confiance)
│   ├── test_conversation_store.py  # Sauvegarde / chargement / suppression de conversations
│   ├── test_analytics.py           # Score de confiance, agrégation de statistiques
│   └── test_stats_export.py        # Validité des exports CSV / Excel
├── .vscode/                  # Configuration Visual Studio Code (voir plus bas)
├── requirements.txt
├── packages.txt              # Dépendances système (Tesseract) pour Streamlit Community Cloud
├── .env.example
└── .streamlit/config.toml
```

`rag_core.py`, `document_loader.py`, `conversation_store.py`,
`analytics.py` et `stats_export.py` n'ont **aucune dépendance à
Streamlit** : ils sont testables et réutilisables indépendamment de
l'interface (CLI, API, notebook...).

Les tests couvrent : le découpage en chunks (respect des fins de phrase,
chevauchement), la recherche hybride FAISS + BM25 (modes semantique /
mots-clés / hybride, avec un encodeur factice injecté pour ne pas dépendre
du téléchargement du vrai modèle sentence-transformers), la suppression
d'un document de l'index, l'extraction PDF/DOCX/TXT et l'OCR (sur des
fichiers générés à la volée, y compris un PDF scanné synthétique), la
validité du PDF exporté, la sauvegarde/chargement/suppression de
conversations, le calcul du score de confiance et l'agrégation des
statistiques d'usage, la validité des exports CSV/Excel, et la
construction du prompt envoyé au modèle.

## Notes de conception

- **Aucune hallucination** : le prompt système interdit explicitement au
  modèle d'utiliser des connaissances externes au contexte fourni, impose
  la citation de chaque affirmation, et impose une réponse explicite
  ("Je ne trouve pas cette information dans les documents fournis.")
  quand le contexte est insuffisant.
- **Citation systématique** : chaque chunk récupéré porte le nom du
  document (et le numéro de page pour les PDF), affiché sous chaque
  réponse et repris dans l'export PDF.
- **Recherche hybride** : le score BM25 (normalisé min-max) et la
  similarité cosinus sont combinés par une moyenne pondérée (`alpha`
  réglable). `alpha=1` équivaut à une recherche purement sémantique,
  `alpha=0` à une recherche purement par mots-clés.
- **Score de confiance** : combine le meilleur score de similarité (70%)
  et la moyenne des scores des extraits utilisés (30%), puis le classe en
  Fort / Moyen / Faible selon des seuils propres à chaque mode de
  recherche (les scores BM25 ne sont pas bornés comme la similarité
  cosinus).
- **Statistiques d'usage** : chaque question posée est journalisée
  (horodatage, confiance, documents cités, temps de réponse, estimation de
  tokens) dans `analytics.QueryLogEntry`, agrégée par
  `aggregate_usage_stats()` et affichée dans l'onglet Tableau de bord.
  L'estimation de tokens (~4 caractères/token) est indicative : Groq étant
  gratuit, il s'agit d'un indicateur de volume d'usage, pas d'un calcul de
  coût.
- **Suppression de document sans ré-encodage** : `VectorIndex` conserve les
  embeddings déjà calculés en cache ; retirer un document reconstruit
  l'index FAISS à partir de ce cache, sans rappeler le modèle
  d'embeddings.
- **OCR ciblé** : seules les pages dont l'extraction native renvoie moins
  de 20 caractères sont passées à l'OCR (évite de ralentir inutilement le
  traitement des PDF déjà numériques).
- **Recherche web bonus** : elle n'est déclenchée que si (a) l'utilisateur
  l'a activée et (b) le meilleur score de similarité documentaire est
  faible. La réponse indique alors explicitement que l'information vient
  du web.
- **Modularité** : `rag_core.py` accepte un encodeur d'embeddings injecté
  (`VectorIndex(encoder=...)`), ce qui permet de tester le pipeline sans
  dépendre du téléchargement du vrai modèle ni d'un accès réseau.

## Limites connues

- L'index vectoriel et l'historique de statistiques (`query_log`) sont en
  mémoire (session Streamlit) : ils ne sont pas persistés entre deux
  redémarrages de l'application (mais s'exportent en CSV/Excel avant de
  fermer la session).
- L'historique des conversations sauvegardées (`conversations/`) est
  stocké sur le disque local de l'application ; sur Streamlit Community
  Cloud, ce stockage est éphémère et remis à zéro à chaque redéploiement.
- La qualité de l'OCR dépend de la netteté du scan ; les documents très
  dégradés peuvent nécessiter une relecture manuelle du texte extrait.
- L'estimation de tokens et d'appels API est indicative (heuristique
  caractères/token), pas une valeur exacte issue de l'API Groq.
- La recherche web bonus dépend de la disponibilité du service DuckDuckGo
  et échoue silencieusement (retour à une liste vide) si le réseau ou la
  dépendance ne sont pas disponibles.
- Le code n'a pas été testé contre le vrai modèle sentence-transformers ni
  contre de vrais appels a l'API Groq dans l'environnement de
  developpement (contraintes de ressources) ; seule la logique pure a ete
  testee unitairement (voir section Tests). Un test en conditions reelles
  (cle API + modele reellement telecharge) est recommande avant un usage
  en production.
