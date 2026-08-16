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
- Embeddings gratuits via l'**API d'inférence Hugging Face** (modèle
  `all-MiniLM-L6-v2`) : pas de modèle lourd (torch) à installer/charger en
  mémoire, ce qui garde l'application légère sur un hébergement gratuit.
  Nécessite une clé `HF_TOKEN` gratuite (voir Installation).
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

## Installation locale

Prérequis : Python 3.10+.

```bash
cd ClarIA
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Pour que l'OCR des PDF scannés fonctionne, le binaire **Tesseract** doit
être installé sur la machine (pas seulement le paquet Python
`pytesseract`, qui n'en est que le pont) :

```bash
# Debian / Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-fra

# macOS (Homebrew)
brew install tesseract tesseract-lang
```

Si Tesseract n'est pas installé, ClarIA continue de fonctionner
normalement pour les PDF avec une couche de texte (la grande majorité) ;
seul l'OCR des PDF scannés sera silencieusement indisponible.

Copie `.env.example` en `.env` et renseigne tes deux clés API (toutes deux
gratuites) :

```bash
cp .env.example .env
```

```
GROQ_API_KEY=gsk_votre_cle_api_ici
HF_TOKEN=hf_votre_token_ici
```

- `GROQ_API_KEY` : obtiens une clé gratuite sur
  [console.groq.com/keys](https://console.groq.com/keys) (génération des
  réponses).
- `HF_TOKEN` : obtiens un token gratuit sur
  [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens/new?ownUserPermissions=inference.serverless.write&tokenType=fineGrained)
  — choisis un token **fine-grained** avec la permission **"Inference
  Providers"** cochée (utilisé pour calculer les embeddings des documents
  via l'API, sans rien installer de lourd en local).

## Développer avec Visual Studio Code

Le projet inclut une configuration `.vscode/` prête à l'emploi
(`settings.json`, `launch.json`, `tasks.json`, `extensions.json`).

1. **Ouvre le dossier** `ClarIA` dans VS Code (`File > Open Folder...`, ou
   `code .` depuis un terminal placé dans le dossier).
2. **Installe les extensions recommandées** : VS Code affiche une
   notification proposant d'installer Python, Pylance et le débogueur
   `debugpy` — accepte-la. Sinon, installe-les manuellement depuis
   l'onglet Extensions.
3. **Crée l'environnement virtuel et installe les dépendances** si ce
   n'est pas déjà fait (voir "Installation locale" ci-dessus), soit dans
   le terminal intégré (`` Ctrl+` ``), soit via `Ctrl+Shift+P` →
   `Tasks: Run Task` → **ClarIA : installer les dependances**.
4. **Sélectionne l'interpréteur Python** : `Ctrl+Shift+P` →
   `Python: Select Interpreter` → choisis celui du dossier `.venv` créé à
   l'étape précédente.
5. **Configure ta clé API** : copie `.env.example` en `.env` et renseigne
   `GROQ_API_KEY` (VS Code la charge automatiquement grâce à
   `python.envFile` dans `.vscode/settings.json`).

Ensuite, trois façons de travailler :

- **Lancer l'application avec le débogueur** : ouvre le panneau *Run and
  Debug* (`Ctrl+Shift+D`), sélectionne **ClarIA : lancer l'application
  Streamlit** dans le menu déroulant, puis appuie sur `F5`. Tu peux poser
  des points d'arrêt dans `app.py`, `rag_core.py`, etc. — ils seront
  atteints normalement pendant l'exécution de l'app.
- **Lancer les tests depuis l'onglet Testing** : l'icône en forme de
  fiole dans la barre latérale liste automatiquement tous les tests
  pytest (grâce à `python.testing.pytestEnabled` dans `settings.json`).
  Clique sur ▶ pour tout lancer, ou sur un test précis pour le lancer
  isolément (clic droit → *Debug Test* pour le déboguer avec points
  d'arrêt).
- **Lancer une tâche rapide sans debug** : `Ctrl+Shift+P` →
  `Tasks: Run Task` → **ClarIA : lancer l'application** ou
  **ClarIA : lancer les tests**.

Si `Python: Select Interpreter` ne propose pas `.venv` automatiquement,
utilise `Ctrl+Shift+P` → `Python: Select Interpreter` →
`Enter interpreter path...` et pointe vers `.venv/bin/python`
(`.venv\Scripts\python.exe` sur Windows).

## Lancer l'application (sans VS Code)

```bash
streamlit run app.py
```

L'application s'ouvre sur `http://localhost:8501`, avec deux onglets :
**Chat** (poser des questions) et **Tableau de bord** (statistiques
d'usage quantifiées, avec export CSV/Excel).

Si aucune clé n'est trouvée dans `.env` / les variables d'environnement,
tu peux la saisir directement dans la barre latérale de l'application.

## Lancer les tests

```bash
pytest
```

Les tests couvrent : le découpage en chunks (respect des fins de phrase,
chevauchement), la recherche hybride FAISS + BM25 (modes semantique /
mots-clés / hybride, avec un encodeur factice injecté pour ne pas dépendre
d'un appel réseau à l'API Hugging Face), l'encodeur d'embeddings basé sur
l'API d'inférence Hugging Face (`HFInferenceEncoder`, avec un faux client
HTTP), la suppression
d'un document de l'index, l'extraction PDF/DOCX/TXT et l'OCR (sur des
fichiers générés à la volée, y compris un PDF scanné synthétique), la
validité du PDF exporté, la sauvegarde/chargement/suppression de
conversations, le calcul du score de confiance et l'agrégation des
statistiques d'usage, la validité des exports CSV/Excel, et la
construction du prompt envoyé au modèle.

## Déploiement sur Streamlit Community Cloud

1. Pousse ce dossier `ClarIA/` dans un dépôt GitHub (public ou privé).
2. Va sur [share.streamlit.io](https://share.streamlit.io), connecte ton
   compte GitHub, puis clique sur **New app**.
3. Sélectionne le dépôt, la branche, et indique `app.py` comme fichier
   principal.
4. Dans **Advanced settings → Secrets**, ajoute tes deux clés au format
   TOML :

   ```toml
   GROQ_API_KEY = "gsk_votre_cle_api_ici"
   HF_TOKEN = "hf_votre_token_ici"
   ```

5. Clique sur **Deploy**.

Le fichier `requirements.txt` est pris en charge nativement par Streamlit
Community Cloud. Le fichier `packages.txt` (déjà inclus) installe
automatiquement `tesseract-ocr` et `tesseract-ocr-fra` au niveau système,
ce qui active l'OCR des PDF scannés sans configuration supplémentaire.
L'application lit automatiquement les deux clés via `st.secrets` (voir
`get_groq_api_key()` et `_sync_hf_token_to_environ()` dans `app.py`), sans
qu'aucun fichier `.env` ne soit nécessaire en production.

**Pourquoi `HF_TOKEN` est nécessaire** : ClarIA calcule les embeddings des
documents via l'API d'inférence gratuite de Hugging Face plutôt qu'en
chargeant un modèle localement (torch + sentence-transformers). Ce choix
évite d'installer/charger ~700 Mo de dépendances ML en mémoire, ce qui
dépassait la RAM disponible sur le tier gratuit de Streamlit Community
Cloud (l'application plantait ou restait bloquée au démarrage). Le modèle
utilisé (`all-MiniLM-L6-v2`) est identique, seule son exécution se fait à
distance. Crée un token gratuit sur
[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens/new?ownUserPermissions=inference.serverless.write&tokenType=fineGrained)
(type **fine-grained**, permission **"Inference Providers"** cochée).

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
  dépendre d'un accès réseau. `HFInferenceEncoder` (l'encodeur par défaut)
  respecte le même protocole minimal (`encode(texts) -> np.ndarray`) et
  pourrait être remplacé par un autre fournisseur d'embeddings sans changer
  le reste du pipeline.

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
- Les embeddings dépendent de la disponibilité de l'API d'inférence
  Hugging Face (gratuite, avec limite de débit) : en cas de pic de charge
  ou de token invalide/manquant, l'indexation échoue avec un message clair
  plutôt que de rester bloquée (voir `EmbeddingModelUnavailable` dans
  `rag_core.py`). Sur l'infrastructure gratuite, un modèle inactif depuis
  un moment peut nécessiter quelques secondes de "réveil" au premier appel
  (géré automatiquement par un réessai avec pause).
- Le code n'a pas été testé contre de vrais appels aux API Groq et
  Hugging Face dans l'environnement de développement (contraintes réseau
  du sandbox) ; la logique pure et les appels HTTP ont été testés
  unitairement avec des doubles de test (voir section Tests). Un test en
  conditions réelles (clés API valides) est recommandé avant un usage en
  production.
