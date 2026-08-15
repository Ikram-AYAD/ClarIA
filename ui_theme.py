"""
ui_theme.py
-----------
Éléments visuels réutilisables pour l'interface Streamlit de ClarIA : CSS
personnalisé, logo, bannière d'en-tête, icônes de type de fichier, badges
de confiance stylisés et petits blocs HTML (titres de section, état vide).
Aucune logique métier ici — uniquement de la présentation, injectée
depuis app.py.
"""

from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_SVG_PATH = ASSETS_DIR / "logo.svg"
LOGO_PNG_PATH = ASSETS_DIR / "logo.png"

PRIMARY = "#4C6FFF"
PRIMARY_DARK = "#3A56D6"
PRIMARY_LIGHT = "#EEF1FF"

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

/* Fond general legerement teinte au lieu du blanc pur */
[data-testid="stAppViewContainer"] > .main {{
    background: linear-gradient(180deg, #FAFBFF 0%, #FFFFFF 260px);
}}

/* Barre laterale : fond distinct + bordure douce */
[data-testid="stSidebar"] {{
    background: #F5F6FC;
    border-right: 1px solid #E7E9F5;
}}
[data-testid="stSidebar"] > div:first-child {{
    padding-top: 1rem;
}}

/* Logo + nom en haut de la barre laterale */
.claria-sidebar-logo {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
}}
.claria-sidebar-logo svg {{
    width: 30px;
    height: 30px;
    flex-shrink: 0;
}}
.claria-sidebar-logo .claria-sidebar-logo-text {{
    font-size: 1.15rem;
    font-weight: 800;
    color: #1F2A44;
}}

/* Bandeau d'en-tete (banniere ClarIA) */
.claria-hero {{
    background: linear-gradient(120deg, {PRIMARY} 0%, #7B5CFA 100%);
    border-radius: 18px;
    padding: 28px 32px;
    margin-bottom: 22px;
    color: #FFFFFF;
    box-shadow: 0 10px 30px -12px rgba(76, 111, 255, 0.55);
}}
.claria-hero .claria-hero-title {{
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 1.9rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    margin-bottom: 6px;
}}
.claria-hero .claria-hero-icon {{
    font-size: 2rem;
}}
.claria-hero .claria-hero-logo svg {{
    width: 46px;
    height: 46px;
    display: block;
    filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.18));
}}
.claria-hero .claria-hero-tagline {{
    font-size: 0.98rem;
    color: #E9ECFF;
    font-weight: 400;
}}
.claria-hero .claria-hero-active {{
    margin-top: 10px;
    display: inline-block;
    background: rgba(255, 255, 255, 0.16);
    border-radius: 999px;
    padding: 4px 14px;
    font-size: 0.8rem;
    font-weight: 500;
}}

/* Cartes de metrique (tableau de bord) */
div[data-testid="stMetric"] {{
    background: #FFFFFF;
    border: 1px solid #E7E9F5;
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 2px 10px -6px rgba(31, 42, 68, 0.12);
}}
div[data-testid="stMetric"] label {{
    color: {PRIMARY_DARK};
}}

/* Titres de section dans la barre laterale, avec pastille icone coloree */
.claria-section-title {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.92rem;
    font-weight: 700;
    color: #1F2A44;
    margin: 1.3rem 0 0.6rem 0;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}}
.claria-section-title .claria-section-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: {PRIMARY_LIGHT};
    font-size: 0.85rem;
}}

/* Carte document (barre laterale) */
.claria-doc-card {{
    display: flex;
    align-items: center;
    gap: 10px;
    background: #FFFFFF;
    border: 1px solid #E7E9F5;
    border-radius: 12px;
    padding: 8px 12px;
    margin-bottom: 6px;
    box-shadow: 0 1px 4px -2px rgba(31, 42, 68, 0.1);
}}
.claria-doc-card .claria-doc-icon {{
    font-size: 1.15rem;
}}
.claria-doc-card .claria-doc-text {{
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}
.claria-doc-card .claria-doc-name {{
    font-size: 0.86rem;
    font-weight: 600;
    color: #1F2A44;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.claria-doc-card .claria-doc-note {{
    font-size: 0.72rem;
    color: {PRIMARY_DARK};
}}

/* Badges de confiance (pilules colorees) */
.claria-badge {{
    display: inline-block;
    padding: 4px 13px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.01em;
}}
.claria-badge-fort {{ background: #DEF7E5; color: #157A3D; }}
.claria-badge-moyen {{ background: #FFEFD6; color: #A15C00; }}
.claria-badge-faible {{ background: #FCE1E1; color: #B4231F; }}
.claria-badge-none {{ background: #E8E9F2; color: #565B72; }}

/* Etat vide (aucun document / aucune conversation) */
.claria-empty-state {{
    text-align: center;
    padding: 64px 24px;
    color: #6B7280;
    background: {PRIMARY_LIGHT};
    border: 1px dashed #C9D1FF;
    border-radius: 18px;
}}
.claria-empty-state .claria-empty-icon {{
    font-size: 3rem;
    margin-bottom: 12px;
}}
.claria-empty-state .claria-empty-title {{
    font-size: 1.15rem;
    font-weight: 700;
    color: #1F2A44;
    margin-bottom: 6px;
}}

/* Boutons : coins arrondis partout */
.stButton > button, .stDownloadButton > button {{
    border-radius: 10px !important;
    font-weight: 600 !important;
}}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
    background: {PRIMARY} !important;
    border-color: {PRIMARY} !important;
    box-shadow: 0 6px 16px -6px rgba(76, 111, 255, 0.6);
}}
.stButton > button[kind="primary"]:hover {{
    background: {PRIMARY_DARK} !important;
    border-color: {PRIMARY_DARK} !important;
}}

/* Zone de televersement de fichiers */
[data-testid="stFileUploaderDropzone"] {{
    border-radius: 12px !important;
    border: 1.5px dashed #C9D1FF !important;
    background: #FFFFFF !important;
}}

/* Onglets (Chat / Tableau de bord) */
button[data-baseweb="tab"] {{
    font-weight: 600;
}}

/* Zone de saisie du chat */
[data-testid="stChatInput"] {{
    border-radius: 14px;
}}
</style>
"""

FILE_ICONS = {
    ".pdf": "📕",
    ".docx": "📘",
    ".txt": "🗒️",
}

BADGE_CLASS_BY_LABEL = {
    "Fort": "claria-badge-fort",
    "Moyen": "claria-badge-moyen",
    "Faible": "claria-badge-faible",
    "Aucune source": "claria-badge-none",
}


def _load_logo_svg() -> str:
    """Charge le SVG du logo ClarIA en mémoire. Renvoie une chaîne vide
    (repli propre) si le fichier n'est pas présent."""
    try:
        return LOGO_SVG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def sidebar_logo_html(app_name: str) -> str:
    """Construit le HTML du petit logo + nom affiché en haut de la barre latérale."""
    logo_svg = _load_logo_svg()
    logo_html = logo_svg if logo_svg else '<span style="font-size:1.4rem;">📄</span>'
    return (
        '<div class="claria-sidebar-logo">'
        f"{logo_html}"
        f'<span class="claria-sidebar-logo-text">{app_name}</span>'
        "</div>"
    )


def file_icon(filename: str) -> str:
    """Renvoie un émoji représentatif du type de fichier."""
    return FILE_ICONS.get(Path(filename).suffix.lower(), "📄")


def confidence_badge_html(label: str, score: float) -> str:
    """Construit le HTML d'un badge de confiance coloré (pilule)."""
    css_class = BADGE_CLASS_BY_LABEL.get(label, "claria-badge-none")
    return f'<span class="claria-badge {css_class}">{label} · {score:.2f}</span>'


def section_title_html(icon: str, label: str) -> str:
    """Construit le HTML d'un titre de section stylisé (pastille + texte) pour la barre latérale."""
    return (
        '<div class="claria-section-title">'
        f'<span class="claria-section-badge">{icon}</span>{label}'
        "</div>"
    )


def doc_card_html(icon: str, name: str, note: str = "") -> str:
    """Construit le HTML d'une carte document (barre latérale)."""
    note_html = f'<span class="claria-doc-note">{note}</span>' if note else ""
    return (
        '<div class="claria-doc-card">'
        f'<span class="claria-doc-icon">{icon}</span>'
        '<span class="claria-doc-text">'
        f'<span class="claria-doc-name">{name}</span>'
        f"{note_html}"
        "</span>"
        "</div>"
    )


def empty_state_html(icon: str, title: str, subtitle: str) -> str:
    """Construit le HTML d'un état vide centré (ex : aucun document indexé)."""
    return (
        '<div class="claria-empty-state">'
        f'<div class="claria-empty-icon">{icon}</div>'
        f'<div class="claria-empty-title">{title}</div>'
        f"<div>{subtitle}</div>"
        "</div>"
    )


def hero_banner_html(title: str, tagline: str, active_conversation: str = "") -> str:
    """Construit le HTML de la bannière d'en-tête colorée en haut de l'application,
    avec le logo ClarIA intégré (repli sur un émoji si le fichier logo est absent)."""
    logo_svg = _load_logo_svg()
    icon_html = (
        f'<span class="claria-hero-logo">{logo_svg}</span>'
        if logo_svg
        else '<span class="claria-hero-icon">📄</span>'
    )
    active_html = (
        f'<div class="claria-hero-active">💬 {active_conversation}</div>'
        if active_conversation
        else ""
    )
    return (
        '<div class="claria-hero">'
        '<div class="claria-hero-title">'
        f"{icon_html}{title}"
        "</div>"
        f'<div class="claria-hero-tagline">{tagline}</div>'
        f"{active_html}"
        "</div>"
    )
