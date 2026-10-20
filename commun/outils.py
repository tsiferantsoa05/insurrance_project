"""
Outils communs à toutes les étapes du projet « Assurance de risque ».

- chemins du projet et fichiers de données transmis d'une étape à l'autre ;
- dictionnaire des 73 variables (code court, bloc thématique, nature) ;
- chargement des données brutes ;
- journal d'exécution (console + fichier) et export des tables ;
- conversion du texte libre (français / malgache) en nombres ;
- style graphique commun (palette validée, marques fines, grille discrète).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GRAINE = 42  # graine aléatoire unique : tous les résultats sont reproductibles

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
RACINE = Path(__file__).resolve().parents[1]
SOURCES = RACINE / "sources"
FICHIER_BRUT = SOURCES / "InsuranceData.xlsx"

ETAPES = {
    "1.0": RACINE / "partie1_donnees" / "1.0_presentation",
    "1.1": RACINE / "partie1_donnees" / "1.1_qualite",
    "1.2": RACINE / "partie1_donnees" / "1.2_aberrantes",
    "1.3": RACINE / "partie1_donnees" / "1.3_preparation",
    "2.1": RACINE / "partie2_segmentation" / "2.1_kmeans",
    "2.2": RACINE / "partie2_segmentation" / "2.2_cart",
    "3.1": RACINE / "partie3_glm" / "3.1_frequence",
    "3.2": RACINE / "partie3_glm" / "3.2_severite",
    "3.3": RACINE / "partie3_glm" / "3.3_prime_pure",
}

# Données transmises d'une étape à la suivante
DONNEES = {
    "qualite": ETAPES["1.1"] / "resultats" / "donnees_qualite.csv",
    "aberrantes": ETAPES["1.2"] / "resultats" / "donnees_sans_aberrantes.csv",
    "finales": ETAPES["1.3"] / "resultats" / "donnees_finales.csv",
    "matrice": ETAPES["1.3"] / "resultats" / "matrice_standardisee.csv",
    "segments": ETAPES["2.1"] / "resultats" / "segments.csv",
    "pred_frequence": ETAPES["3.1"] / "resultats" / "predictions_frequence.csv",
    "pred_severite": ETAPES["3.2"] / "resultats" / "predictions_severite.csv",
    "primes": ETAPES["3.3"] / "resultats" / "primes_pures.csv",
}


def dossier_resultats(etape: str) -> Path:
    """Crée (si besoin) et renvoie le dossier resultats/ d'une étape."""
    dossier = ETAPES[etape] / "resultats"
    (dossier / "figures").mkdir(parents=True, exist_ok=True)
    (dossier / "tables").mkdir(parents=True, exist_ok=True)
    return dossier


# ---------------------------------------------------------------------------
# Dictionnaire des variables (dans l'ordre des colonnes du fichier Excel)
# nature : Identifiant | Quantitative continue | Quantitative discrète |
#          Qualitative nominale | Qualitative ordinale | Texte libre
# ---------------------------------------------------------------------------
VARIABLES = [
    ("id", "Identifiant", "Identifiant"),
    ("sexe", "Démographie", "Qualitative nominale"),
    ("age", "Démographie", "Quantitative continue"),
    ("fokotany", "Démographie", "Qualitative nominale"),
    ("lien_chef_menage", "Démographie", "Qualitative nominale"),
    ("statut_pro", "Activité professionnelle", "Qualitative nominale"),
    ("statut_matrimonial", "Démographie", "Qualitative nominale"),
    ("taille_menage", "Ménage et logement", "Quantitative discrète"),
    ("nb_actifs_menage", "Ménage et logement", "Quantitative discrète"),
    ("secteur", "Activité professionnelle", "Qualitative nominale"),
    ("activite_conjoint", "Ménage et logement", "Qualitative nominale"),
    ("niveau_etude", "Démographie", "Qualitative ordinale"),
    ("statut_residence", "Ménage et logement", "Qualitative nominale"),
    ("source_eau", "Ménage et logement", "Qualitative nominale"),
    ("source_electricite", "Ménage et logement", "Qualitative nominale"),
    ("energie_cuisine", "Ménage et logement", "Qualitative nominale"),
    ("type_toilette", "Ménage et logement", "Qualitative nominale"),
    ("activite_famille", "Activité professionnelle", "Qualitative nominale"),
    ("anciennete_emploi", "Activité professionnelle", "Quantitative continue"),
    ("distance_travail", "Activité professionnelle", "Quantitative continue"),
    ("transport_travail", "Activité professionnelle", "Qualitative nominale"),
    ("heures_jour", "Activité professionnelle", "Quantitative continue"),
    ("jours_semaine", "Activité professionnelle", "Quantitative discrète"),
    ("nb_employes", "Activité professionnelle", "Quantitative discrète"),
    ("revenu", "Revenus et budget", "Qualitative ordinale"),
    ("budget_alim", "Revenus et budget", "Quantitative continue"),
    ("budget_sante", "Revenus et budget", "Quantitative continue"),
    ("budget_elec", "Revenus et budget", "Quantitative continue"),
    ("epargne", "Revenus et budget", "Qualitative nominale"),
    ("dettes", "Revenus et budget", "Qualitative nominale"),
    ("effort_physique", "Conditions de travail", "Qualitative ordinale"),
    ("duree_effort", "Conditions de travail", "Qualitative ordinale"),
    ("pb_sante_travail", "Conditions de travail", "Qualitative ordinale"),
    ("arret_maladie", "Conditions de travail", "Qualitative ordinale"),
    ("impact_travail_sante", "Conditions de travail", "Qualitative ordinale"),
    ("repos_recent", "Conditions de travail", "Qualitative ordinale"),
    ("couverture", "Couverture maladie", "Qualitative nominale"),
    ("mode_affiliation", "Couverture maladie", "Qualitative nominale"),
    ("type_couverture", "Couverture maladie", "Qualitative nominale"),
    ("ancienne_couverture", "Couverture maladie", "Qualitative nominale"),
    ("interet_couverture", "Couverture maladie", "Qualitative ordinale"),
    ("prime_souhaitee", "Couverture maladie", "Quantitative continue"),
    ("maladie_chronique", "État de santé", "Qualitative nominale"),
    ("chronique_categorie", "État de santé", "Qualitative nominale"),
    ("chronique_detail", "État de santé", "Texte libre"),
    ("traitement_regulier", "État de santé", "Qualitative ordinale"),
    ("freq_consult_chronique", "État de santé", "Qualitative ordinale"),
    ("depense_medic_chronique", "État de santé", "Quantitative continue"),
    ("lunettes", "État de santé", "Qualitative nominale"),
    ("valeur_lunettes", "État de santé", "Qualitative ordinale"),
    ("dentiste", "État de santé", "Qualitative ordinale"),
    ("freq_dentiste", "État de santé", "Qualitative ordinale"),
    ("nb_maladies_graves", "État de santé", "Quantitative discrète"),
    ("renoncement_soins", "État de santé", "Qualitative nominale"),
    ("date_derniere_maladie", "Dernier épisode de maladie", "Texte libre"),
    ("type_maladie", "Dernier épisode de maladie", "Texte libre"),
    ("douleur", "Dernier épisode de maladie", "Qualitative ordinale"),
    ("jours_arret", "Dernier épisode de maladie", "Quantitative continue"),
    ("type_recours", "Dernier épisode de maladie", "Qualitative nominale"),
    ("motif_recours", "Dernier épisode de maladie", "Qualitative nominale"),
    ("distance_soins", "Dernier épisode de maladie", "Quantitative continue"),
    ("satisfaction", "Dernier épisode de maladie", "Qualitative ordinale"),
    ("autre_recours_souhaite", "Dernier épisode de maladie", "Qualitative nominale"),
    ("benefice_autre_recours", "Dernier épisode de maladie", "Qualitative nominale"),
    ("cout_consultation", "Coûts du dernier épisode", "Quantitative continue"),
    ("cout_hospitalisation", "Coûts du dernier épisode", "Quantitative continue"),
    ("cout_medicaments", "Coûts du dernier épisode", "Quantitative continue"),
    ("cout_deplacement", "Coûts du dernier épisode", "Quantitative continue"),
    ("cout_alimentation", "Coûts du dernier épisode", "Quantitative continue"),
    ("cout_autres", "Coûts du dernier épisode", "Quantitative continue"),
    ("impact_autre", "Impact sur l'activité", "Qualitative nominale"),
    ("impact_maladie_activite", "Impact sur l'activité", "Qualitative ordinale"),
    ("recuperation_activite", "Impact sur l'activité", "Qualitative nominale"),
]
CODES = [code for code, _, _ in VARIABLES]
BLOC = {code: bloc for code, bloc, _ in VARIABLES}
NATURE = {code: nature for code, _, nature in VARIABLES}

COUTS = ["cout_consultation", "cout_hospitalisation", "cout_medicaments",
         "cout_deplacement", "cout_alimentation", "cout_autres"]

# Variables cibles
CIBLE_FREQUENCE = "nb_maladies_graves"   # N_i : nombre de sinistres sur 12 mois
CIBLE_SEVERITE = "cout_total"            # S_i : coût du dernier épisode (somme G.1 à G.6)

# Modalités des variables ordinales, de la plus faible à la plus forte
ORDRES = {
    "niveau_etude": ["Analphabète", "Primaire", "Collège", "Lycée", "Université"],
    "revenu": ["<100k", "100-200k", "200-300k", "300-400k", "400-500k", "500k-1M", ">1M"],
    "effort_physique": ["Jamais", "Rarement", "Parfois", "Souvent", "Toujours"],
    "duree_effort": ["<1 h", "1-3 h", "3-5 h", ">5 h"],
    "pb_sante_travail": ["Jamais", "Rarement", "Parfois", "Régulièrement"],
    "arret_maladie": ["Jamais", "Une ou deux fois", "Plusieurs fois"],
    "impact_travail_sante": ["Aucun", "Faible", "Modéré", "Important"],
    "repos_recent": ["Jamais", "Une fois", "Plusieurs fois"],
    "interet_couverture": ["Pas du tout", "Plutôt non", "Plutôt oui", "Tout à fait"],
    "dentiste": ["Jamais", "Parfois", "Souvent"],
    "douleur": ["Pas douloureux", "Peu douloureux", "Douloureux", "Très douloureux"],
    "satisfaction": ["Pas du tout satisfait", "Plutôt pas satisfait",
                     "Plutôt satisfait", "Tout à fait satisfait"],
    "impact_maladie_activite": ["Pas affecté", "Affecté", "Très affecté"],
}


# ---------------------------------------------------------------------------
# Chargement et écriture des données
# ---------------------------------------------------------------------------
def charger_donnees_brutes() -> tuple[pd.DataFrame, dict[str, str]]:
    """Lit le fichier Excel et renomme les 73 colonnes avec les codes courts.

    Renvoie (données, libellés) où libellés[code] = intitulé d'origine.
    """
    brut = pd.read_excel(FICHIER_BRUT, sheet_name="DataUsed")
    if brut.shape[1] != len(VARIABLES):
        raise ValueError(f"{brut.shape[1]} colonnes lues, {len(VARIABLES)} attendues")
    libelles = {code: " ".join(str(col).split()) for code, col in zip(CODES, brut.columns)}
    brut.columns = CODES
    return brut, libelles


def ecrire_donnees(df: pd.DataFrame, chemin: Path, excel: bool = False) -> None:
    """Écrit un jeu de données en CSV (UTF-8 avec BOM, lisible par Excel)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(chemin, index=False, encoding="utf-8-sig")
    if excel:
        df.to_excel(chemin.with_suffix(".xlsx"), index=False)


def lire_donnees(nom: str) -> pd.DataFrame:
    """Lit un jeu de données produit par une étape précédente (voir DONNEES)."""
    chemin = DONNEES[nom]
    if not chemin.exists():
        raise FileNotFoundError(f"{chemin} introuvable : exécuter d'abord l'étape qui le produit")
    return pd.read_csv(chemin, encoding="utf-8-sig")


def sauver_table(df: pd.DataFrame, dossier: Path, nom: str, index: bool = False) -> Path:
    chemin = dossier / "tables" / f"{nom}.csv"
    df.to_csv(chemin, index=index, encoding="utf-8-sig")
    return chemin


# ---------------------------------------------------------------------------
# Journal d'exécution
# ---------------------------------------------------------------------------
def dans_notebook() -> bool:
    """Vrai si le code s'exécute dans un notebook Jupyter (noyau IPython)."""
    try:
        from IPython import get_ipython

        shell = get_ipython()
        return shell is not None and shell.__class__.__name__ == "ZMQInteractiveShell"
    except ImportError:
        return False


def _afficher_tableau(df: pd.DataFrame, index: bool, floatfmt: str) -> None:
    """Affiche un tableau en HTML dans un notebook (nombres formatés comme dans le journal)."""
    from IPython.display import display

    def formater(v):
        if isinstance(v, (bool, np.bool_)):
            return str(v)
        if isinstance(v, (int, np.integer)):
            return str(v)
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else format(v, floatfmt)
        return v

    try:
        style = df.style.format(formatter=formater)
        display(style if index else style.hide(axis="index"))
    except Exception:
        display(df)


class Journal:
    """Affiche les messages et les recopie dans resultats/journal.txt.

    Dans un notebook, les tableaux sont affichés en HTML ; le journal reste identique.
    """

    def __init__(self, dossier: Path, titre: str):
        self.chemin = dossier / "journal.txt"
        self._fichier = open(self.chemin, "w", encoding="utf-8")
        self(f"# {titre}")

    def __call__(self, *morceaux) -> None:
        texte = " ".join(str(m) for m in morceaux)
        print(texte)
        self._fichier.write(texte + "\n")
        self._fichier.flush()

    def section(self, titre: str) -> None:
        self("")
        self(f"## {titre}")
        self("")

    def table(self, df: pd.DataFrame, index: bool = True, floatfmt: str = ",.2f") -> None:
        markdown = df.to_markdown(index=index, floatfmt=floatfmt)
        if dans_notebook():
            _afficher_tableau(df, index, floatfmt)
            self._fichier.write(markdown + "\n\n")
            self._fichier.flush()
        else:
            self(markdown)
            self("")

    def fermer(self) -> None:
        self._fichier.close()


# ---------------------------------------------------------------------------
# Texte libre -> catégories
# ---------------------------------------------------------------------------
def normaliser(x) -> str | None:
    """Minuscules, espaces simples, sans retour à la ligne. None si manquant."""
    if x is None or (isinstance(x, float) and np.isnan(x)) or x is pd.NA:
        return None
    s = str(x).replace("\n", " ").replace(" ", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s or None


def premiere_modalite(serie: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Résout les réponses multiples concaténées dans une cellule.

    Une cellule est « multiple » si elle contient au moins deux modalités simples
    (une modalité simple est une valeur qui n'en contient aucune autre). On garde la
    modalité citée en premier. Renvoie (série résolue, masque des cellules multiples).
    """
    s = serie.map(lambda v: None if pd.isna(v) else " ".join(str(v).split()))
    valeurs = sorted({v for v in s.dropna()}, key=len)
    simples = [v for v in valeurs if not any(u != v and u in v for u in valeurs)]
    multiples = pd.Series(False, index=s.index)
    resolu = s.copy()
    for i, v in s.items():
        if v is None or v in simples:
            continue
        trouvees = [(v.find(m), m) for m in simples if m in v]
        if len(trouvees) >= 2:
            multiples[i] = True
            resolu[i] = min(trouvees)[1]
    return resolu, multiples


def recoder(serie: pd.Series, regles: list[tuple[str, str]]) -> tuple[pd.Series, list[str]]:
    """Recode une variable qualitative avec des règles (motif regex, libellé).

    La première règle qui correspond l'emporte. Renvoie (série recodée, valeurs non reconnues).
    """
    non_reconnues = []

    def _un(v):
        s = normaliser(v)
        if s is None:
            return np.nan
        for motif, libelle in regles:
            if re.search(motif, s):
                return libelle
        non_reconnues.append(v)
        return np.nan

    return serie.map(_un), sorted(set(map(str, non_reconnues)))


# ---------------------------------------------------------------------------
# Texte libre -> nombres
# ---------------------------------------------------------------------------
_NOMBRE = r"\d+(?:[.,]\d+)?"
_CODE_ZERO = re.compile(r"[\s,.'’]*[o0pi∅]+[\s,.'’]*")  # 'O', '00', 'P', ',0' : saisies de zéro

# Nombres écrits en toutes lettres (malgache, puis français)
_MOTS_NOMBRES = [
    (r"\biray\b", "1"), (r"\bray\b", "1"), (r"\broa", "2"), (r"\btelo\b", "3"),
    (r"\befatra", "4"), (r"\bdimy\b", "5"), (r"\benina\b", "6"), (r"\bfito\b", "7"),
    (r"\bvalo\b", "8"), (r"\bsivy\b", "9"), (r"\bfolo\b", "10"),
    (r"\bune?\b", "1"), (r"\bdeux\b", "2"), (r"\btrois\b", "3"), (r"\bquatre\b", "4"),
    (r"\bcinq\b", "5"), (r"\bsix\b", "6"), (r"\bsept\b", "7"), (r"\bhuit\b", "8"),
    (r"\bdix\b", "10"), (r"\bquinze\b", "15"),
]


def _mots_en_chiffres(s: str) -> str:
    for motif, chiffre in _MOTS_NOMBRES:
        s = re.sub(motif, chiffre + " ", s)
    return s


def _fusionner_milliers(s: str) -> str:
    """'20 000' -> '20000', '1 000 000' -> '1000000'."""
    return re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", s)


def _vers_float(t: str) -> float:
    return float(t.replace(",", ".").replace(" ", ""))


def _plage(s: str, seuil: float = 0.0) -> float | None:
    """Moyenne d'une fourchette 'a ~ b', 'a - b', 'a à b', 'a na b', 'a_b'."""
    m = re.search(rf"({_NOMBRE})\s*(?:ar|km|k|m|j|h|ans?)?\s*(?:~|-|–|_|\bà\b|\ba\b|\bna\b)\s*({_NOMBRE})", s)
    if m:
        a, b = _vers_float(m.group(1)), _vers_float(m.group(2))
        if a >= seuil and b >= seuil:
            return (a + b) / 2
    return None


# Saisies de montant sans chiffre qui signifient « aucune dépense » : rien payé, remède
# traditionnel (tambavy, evoka, ravina), déplacement à pied, alimentation inchangée,
# prise en charge par un tiers.
MOTS_ZERO_MONTANT = (
    "tsy nisy", "ts nisy", "tsa nisy", "tsy misy", "ts misy", "tsisy", "tsis ",
    "tsy narary", "tsa niala", "tsy nandoa", "nandoavambola", "tsa nividy", "ts nividy",
    "tsa mila", "tsa niditra", "prise en charge", "gratuit", "tambavy", "tabavy", "evoka",
    "nievo", "ravina", "randriaka", "ady gasy", "bicyclette", "tongotra", "tsa niova",
    "tsa niava", "ts miova", "ts muiova", "tsy mampiasa", "otran isan", "hotran isan",
    "fiovany", "naha sakafo", "naha hinana", "mahasakafo", "mahahinana", "nahasakafo",
    "nahahinana", "mahalany", "voakazo", "nande teny", "tsa namonjy", "nutanika",
    "notanehina", "notenahiny", "niotra hoe", "fiandry", "niantoka", "niatoka", "topon",
    "mitambatra", "nandany vola", "ts dia lafo", "ts d ambony", "maha hinana", "tsa miova",
    "ts de misy vola",
)

# Expressions de calcul trop complexes pour une règle générale (clé = texte normalisé)
CORRECTIONS_MONTANT = {
    "12500 + calcium novidina manokana 1500 ×5": 20000.0,
    "yaourt(500) 3/j + pain ( 500) 2/j × 5": 12500.0,
    "5000 ar ny tsindrona iray nefa mitsindrona in-droa isan'andro": 10000.0,
    "karama niandry marary 10000, ofany lakosia nandrahona mpiandry marary : 3000/ j": 13000.0,
}


def texte_vers_montant(x) -> tuple[float, str]:
    """Convertit une saisie de montant (Ariary) en nombre.

    Renvoie (valeur, statut) ; statut ∈ manquant, numerique, zero_code, zero_texte,
    calcul, fourchette, texte_nombre, correction_manuelle, inconnu.
    Règles, dans l'ordre :
      1. résultat de calcul donné après ':' ou '=' ('8000×2:16000' -> 16000) ;
      2. 'x million' -> x × 1 000 000 ;
      3. fourchette ou alternative ('11000 ~ 15000', '1000 na 2000') -> moyenne ;
      4. somme explicite ('15000 (...) + 3000') -> somme ;
      5. produit explicite ('7000 × 6') -> produit ;
      6. sinon le plus grand nombre cité (les petits nombres sont des quantités ou durées).
    Un montant exprimé par jour ou par semaine sans durée est gardé tel quel (borne basse).
    """
    if pd.isna(x):
        return np.nan, "manquant"
    if isinstance(x, (int, float, np.number)):
        return float(x), "numerique"
    s = normaliser(x)
    if s is None:
        return np.nan, "manquant"
    if s in CORRECTIONS_MONTANT:
        return CORRECTIONS_MONTANT[s], "correction_manuelle"
    if _CODE_ZERO.fullmatch(s):
        return 0.0, "zero_code"
    s = _fusionner_milliers(s)
    if re.fullmatch(_NOMBRE, s):
        return _vers_float(s), "numerique"
    nombres = re.findall(_NOMBRE, s)
    if not nombres:
        if any(m in s for m in MOTS_ZERO_MONTANT):
            return 0.0, "zero_texte"
        return np.nan, "inconnu"
    m = re.search(rf"[:=]\s*({_NOMBRE})", s)
    if m:
        return _vers_float(m.group(1)), "calcul"
    if "million" in s:
        return _vers_float(nombres[0]) * 1e6, "calcul"
    p = _plage(s, seuil=100)
    if p is not None:
        return p, "fourchette"
    m = re.search(r"(\d+)\s*(?:ar)?\s*(?:\([^)]*\))?\s*\+\s*(\d+)", s)
    if m and float(m.group(1)) >= 100 and float(m.group(2)) >= 100:
        return float(m.group(1)) + float(m.group(2)), "calcul"
    m = re.search(r"(\d+)\s*[×x*]\s*(\d+)", s)
    if m:
        return float(m.group(1)) * float(m.group(2)), "calcul"
    return max(_vers_float(n) for n in nombres), "texte_nombre"


# --- Distances (km) ---------------------------------------------------------
_UNITE_KM = r"(?:km|kmn|k|ko|kilom\w*)"
_UNITE_M = r"(?:m|mètre|metre|métre|mettre|metttre|metatra)"
MOTS_DOMICILE = ("domicile", "trano", "ato hiany", "ao hiany", "tokontany", "manodidina")
MOTS_PROCHE = ("akaiky", "tsa de lavitra", "tsy lavitra")


def texte_vers_km(x) -> tuple[float, str]:
    """Convertit une distance saisie librement en kilomètres.

    Unités reconnues : km, m (et variantes 'mètre', 'mettre'...). Sans unité, une valeur
    ≥ 50 est lue en mètres, sinon en kilomètres. Fourchette -> milieu. Travail ou soins
    au domicile -> 0 ; « proche » sans chiffre -> 0,1 km ; distance variable -> manquant.
    """
    if pd.isna(x):
        return np.nan, "manquant"
    if isinstance(x, (int, float, np.number)):
        v = float(x)
        return (v / 1000 if v >= 50 else v), "numerique"
    s = normaliser(x)
    if s is None:
        return np.nan, "manquant"
    s = re.sub(r"(?<![a-z])o(?=\s*[,.]?\s*\d|km)", "0", s)  # 'O,5' -> '0,5', 'Okm' -> '0km'
    s = re.sub(r"(?<=\d),\s(?=\d)", ",", s)                  # '1, 5 km' -> '1,5 km'
    if _CODE_ZERO.fullmatch(s):
        return 0.0, "zero_code"
    s = _mots_en_chiffres(s)
    if re.search(r"\d\s*mn\b", s):
        return np.nan, "inconnu"  # durée en minutes, pas une distance
    m = re.search(r"(\d+)\s*km\s*(\d{3})\b", s)  # '1km500'
    if m:
        return float(m.group(1)) + float(m.group(2)) / 1000, "texte_nombre"
    jetons = re.findall(rf"({_NOMBRE})\s*({_UNITE_KM}|{_UNITE_M})?(?![a-z])", s)
    if not jetons:
        if any(m in s for m in MOTS_DOMICILE):
            return 0.0, "zero_texte"
        if any(m in s for m in MOTS_PROCHE):
            return 0.1, "zero_texte"
        return np.nan, "inconnu"
    unites = [u for _, u in jetons if u]
    unite_defaut = unites[-1] if unites else None

    def _km(valeur: str, unite: str | None) -> float:
        v = _vers_float(valeur)
        unite = unite or unite_defaut
        if unite is None:
            return v / 1000 if v >= 50 else v
        return v / 1000 if re.fullmatch(_UNITE_M, unite) else v

    demi = 0.5 if re.search(r"et demi|sy sasany|sy tapany", s) else 0.0
    if len(jetons) >= 2 and re.search(r"~|-|–|_|\bà\b|\ba\b|\d\s*a\s*\d", s):
        return (_km(*jetons[0]) + _km(*jetons[1])) / 2, "fourchette"
    statut = "numerique" if re.fullmatch(_NOMBRE, s) else "texte_nombre"
    return _km(*jetons[0]) + demi, statut


# --- Durées (jours) ---------------------------------------------------------
_UNITES_JOURS = [
    (r"tapa-?bolana", 15.0), (r"tokombolana", 7.0), (r"herin'?andro|semaine?s?|semain", 7.0),
    (r"mois|moins|moi\b|volana|bolana", 30.0), (r"taona|ans?\b", 365.0),
    (r"jours?|jous|andro|j\b", 1.0), (r"h\b|heures?", 1 / 24),
]


# Unités employées seules, sans chiffre ('Herinandro' = une semaine)
_UNITES_SEULES = [
    (r"\btapa-?bolana\b", 15.0), (r"\btokombolana\b", 7.0),
    (r"\bherin'?andro\b|\bsemaines?\b", 7.0), (r"\bvolana\b|\bmois\b", 30.0), (r"\btaona\b", 365.0),
]


def _unite_jours(texte: str) -> float | None:
    for motif, facteur in _UNITES_JOURS:
        if re.match(motif, texte):
            return facteur
    return None


def texte_vers_jours(x) -> tuple[float, str]:
    """Convertit une durée d'arrêt d'activité saisie librement en jours.

    Unités : jour/andro (1), semaine/herinandro (7), tapabolana (15), mois/volana (30),
    an/taona (365). « A continué à travailler » (niasa/miasa ihany) -> 0.
    Somme si '+' ('1 mois + 15 jours' -> 45), fourchette -> moyenne, '½'/'et demi' -> +0,5 unité.
    """
    if pd.isna(x):
        return np.nan, "manquant"
    if isinstance(x, (int, float, np.number)):
        return float(x), "numerique"
    s = normaliser(x)
    if s is None:
        return np.nan, "manquant"
    if _CODE_ZERO.fullmatch(s) or s in ("non", "sans", "tsy nisy") or "tsy narary" in s:
        return 0.0, "zero_code"
    if re.fullmatch(_NOMBRE, s):
        return _vers_float(s), "numerique"
    s = s.replace("½", " sy tapany ")
    s = _mots_en_chiffres(s)
    s = re.sub(r"\bdemi jour\b|tapak'?andro", " 0.5 j ", s)
    s = re.sub(r"\bamambolana\b", " 1 mois ", s)
    s = re.sub(r"\bamataona\b", " 1 an ", s)
    jetons = []
    for m in re.finditer(rf"({_NOMBRE})\s*([a-z'-]*)", s):
        facteur = _unite_jours(m.group(2)) if m.group(2) else None
        jetons.append((_vers_float(m.group(1)), facteur))
    if not jetons:
        for motif, facteur in _UNITES_SEULES:
            if re.search(motif, s):
                return facteur, "texte_nombre"
        if re.search(r"\b(tsy|tsa|ts)\s+(niasa|miasa)", s):
            return np.nan, "inconnu"  # n'a pas travaillé, durée non précisée
        if re.search(r"niasa|miasa|nias\b|mias\b|nivarotra", s):
            return 0.0, "zero_texte"  # a continué à travailler
        return np.nan, "inconnu"
    facteurs = [f for _, f in jetons if f]
    defaut = facteurs[0] if facteurs else 1.0
    demi = 0.5 if re.search(r"et demi|sy tapany", s) else 0.0
    if "+" in s:
        total = sum(v * (f or defaut) for v, f in jetons)
        return total, "calcul"
    if len(jetons) >= 2 and re.search(r"~|_|-|\bà\b", s):
        return (jetons[0][0] + jetons[1][0]) / 2 * defaut, "fourchette"
    v, f = jetons[0]
    f = f or defaut
    return (v + demi) * f, "texte_nombre"


# --- Ancienneté (années) ----------------------------------------------------
def texte_vers_annees(x, annee_enquete: int = 2026) -> tuple[float, str]:
    """Convertit une ancienneté dans l'emploi en années (mois -> /12).

    Une année civile (1950-2030) citée seule est convertie en durée (2026 - année) ;
    citée avec un autre nombre, elle est ignorée. « Depuis l'enfance » -> manquant.
    """
    if pd.isna(x):
        return np.nan, "manquant"
    if isinstance(x, (int, float, np.number)):
        return float(x), "numerique"
    s = normaliser(x)
    if s is None:
        return np.nan, "manquant"
    if re.fullmatch(_NOMBRE, s):
        return _vers_float(s), "numerique"
    if _CODE_ZERO.fullmatch(s):
        return 0.0, "zero_code"
    if "fahazazana" in s:
        return np.nan, "inconnu"
    jetons = []
    for m in re.finditer(rf"({_NOMBRE})\s*([a-z]*)", s):
        u = m.group(2)
        if re.match(r"ans?|taona", u):
            f = 1.0
        elif re.match(r"mois|moi|moins|volana", u):
            f = 1 / 12
        else:
            f = None
        jetons.append((_vers_float(m.group(1)), f))
    if not jetons:
        return np.nan, "inconnu"
    civiles = [v for v, _ in jetons if 1950 <= v <= 2030]
    autres = [(v, f) for v, f in jetons if not 1950 <= v <= 2030]
    if not autres:
        return float(annee_enquete - civiles[0]), "calcul"
    demi = 0.5 if re.search(r"et demi|sy tapany", s) else 0.0
    m = re.search(r"(\d+)\s*(?:ans?|taona)\s*(?:sy|et)\s*(\d+)\s*(?:mois|volana)", s)
    if m:  # '1taona sy 3volana' -> 1,25
        return float(m.group(1)) + float(m.group(2)) / 12, "calcul"
    p = _plage(s)
    if p is not None:
        f = next((f for _, f in autres if f), 1.0)
        return p * f, "fourchette"
    avec_unite = [(v, f) for v, f in autres if f]
    v, f = avec_unite[0] if avec_unite else (autres[0][0], 1.0)
    return (v + demi) * f, "texte_nombre"


# --- Heures par jour, jours par semaine, effectifs ---------------------------
def texte_vers_heures(x) -> tuple[float, str]:
    """Heures travaillées par jour : '8h' -> 8, '4 ~ 5' -> 4,5, '24/24' -> 24,
    'tontolo andro' (toute la journée) -> 12, réponse variable -> manquant."""
    if pd.isna(x):
        return np.nan, "manquant"
    if isinstance(x, (int, float, np.number)):
        return float(x), "numerique"
    s = normaliser(x)
    if re.fullmatch(_NOMBRE, s):
        return _vers_float(s), "numerique"
    if "24/24" in s:
        return 24.0, "texte_nombre"
    if "tontolo andro" in s:
        return 12.0, "zero_texte"
    p = _plage(s)
    if p is not None:
        return p, "fourchette"
    nombres = re.findall(_NOMBRE, s)
    if not nombres:
        return np.nan, "inconnu"
    return _vers_float(nombres[0]), "texte_nombre"


def texte_vers_jours_semaine(x) -> tuple[float, str]:
    """Jours travaillés par semaine : '6j' -> 6, '6/7' -> 6, '5/6' -> 5,5,
    'miasa isanandro' (tous les jours) -> 7, '5 et demi' -> 5,5."""
    if pd.isna(x):
        return np.nan, "manquant"
    if isinstance(x, (int, float, np.number)):
        return float(x), "numerique"
    s = normaliser(x)
    if re.fullmatch(_NOMBRE, s):
        return _vers_float(s), "numerique"
    if _CODE_ZERO.fullmatch(s):
        return 0.0, "zero_code"
    s = _mots_en_chiffres(s)
    m = re.search(r"(\d+)\s*[a-z]*\s*/\s*(\d+)", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return (a if b == 7 else (a + b) / 2), "texte_nombre"
    p = _plage(s)
    if p is not None:
        return p, "fourchette"
    nombres = re.findall(_NOMBRE, s)
    if not nombres:
        if re.search(r"isan'?andro", s):
            return 7.0, "zero_texte"
        return np.nan, "inconnu"
    demi = 0.5 if "demi" in s else 0.0
    return _vers_float(nombres[0]) + demi, "texte_nombre"


def texte_vers_effectif(x) -> tuple[float, str]:
    """Nombre d'employés : chiffres ; 'tsy mampiasa', entraide familiale -> 0 ;
    emploi occasionnel sans chiffre -> 1."""
    if pd.isna(x):
        return np.nan, "manquant"
    if isinstance(x, (int, float, np.number)):
        return float(x), "numerique"
    s = normaliser(x)
    if re.fullmatch(_NOMBRE, s):
        return _vers_float(s), "numerique"
    if _CODE_ZERO.fullmatch(s):
        return 0.0, "zero_code"
    p = _plage(s)
    if p is not None:
        return p, "fourchette"
    nombres = re.findall(_NOMBRE, s)
    if nombres:
        return _vers_float(nombres[0]), "texte_nombre"
    if re.search(r"tsy mampiasa|tsy misy|ihany|iany|hiany|kifanomba|indran|mindrana", s):
        return 0.0, "zero_texte"
    if re.search(r"ndraindray|indrai|kindraindray|sendraika|misy fotoana|rehefa|manarama|mampiasa", s):
        return 1.0, "zero_texte"
    return np.nan, "inconnu"


def convertir(serie: pd.Series, fonction) -> tuple[pd.Series, pd.Series]:
    """Applique un convertisseur texte -> nombre ; renvoie (valeurs, statuts)."""
    resultats = serie.map(fonction)
    return resultats.map(lambda r: r[0]).astype(float), resultats.map(lambda r: r[1])


# ---------------------------------------------------------------------------
# Statistiques utiles
# ---------------------------------------------------------------------------
def cramers_v(x: pd.Series, y: pd.Series) -> float:
    """V de Cramér corrigé du biais (Bergsma, 2013) entre deux variables qualitatives."""
    from scipy.stats import chi2_contingency

    tableau = pd.crosstab(x, y)
    if tableau.shape[0] < 2 or tableau.shape[1] < 2:
        return np.nan
    chi2 = chi2_contingency(tableau, correction=False)[0]
    n = tableau.to_numpy().sum()
    phi2 = chi2 / n
    r, k = tableau.shape
    phi2c = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    rc, kc = r - (r - 1) ** 2 / (n - 1), k - (k - 1) ** 2 / (n - 1)
    return float(np.sqrt(phi2c / max(1e-12, min(kc - 1, rc - 1))))


def table_frequences(serie: pd.Series, ordre: list[str] | None = None) -> pd.DataFrame:
    effectifs = serie.value_counts(dropna=False)
    if ordre:
        effectifs = effectifs.reindex([m for m in ordre if m in effectifs.index]
                                      + [m for m in effectifs.index if m not in ordre])
    t = pd.DataFrame({"effectif": effectifs, "pourcentage": 100 * effectifs / effectifs.sum()})
    t.index = t.index.map(lambda v: "Manquant" if pd.isna(v) else v)
    t.index.name = serie.name
    return t


# ---------------------------------------------------------------------------
# Style graphique
# Palette validée (scripts/validate_palette.js du guide de visualisation) :
# 3 premières couleurs catégorielles sûres pour les daltoniens, rampe ordinale bleue.
# ---------------------------------------------------------------------------
COULEURS = {
    "surface": "#fcfcfb", "encre": "#0b0b0b", "encre2": "#52514e", "attenue": "#898781",
    "grille": "#e1e0d9", "axe": "#c3c2b7", "fond_point": "#d9d8d2",
}
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
RAMPE_BLEUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
               "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]


def rampe_ordinale(n: int) -> list[str]:
    """n teintes bleues ordonnées du clair au foncé (la plus claire reste lisible)."""
    utilisables = RAMPE_BLEUE[3:12]  # du pas 250 au pas 650
    idx = np.linspace(0, len(utilisables) - 1, n).round().astype(int)
    return [utilisables[i] for i in idx]


def style_graphique():
    """Configure matplotlib (rendu fichier, surface claire, grille discrète) et le renvoie."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cycler import cycler

    c = COULEURS
    plt.rcParams.update({
        "figure.facecolor": c["surface"], "axes.facecolor": c["surface"],
        "savefig.facecolor": c["surface"], "axes.edgecolor": c["axe"], "axes.linewidth": 0.8,
        "axes.labelcolor": c["encre2"], "axes.titlecolor": c["encre"], "axes.titlesize": 11.5,
        "axes.titleweight": "semibold", "axes.titlelocation": "left", "axes.titlepad": 10,
        "axes.labelsize": 9.5, "xtick.color": c["axe"], "ytick.color": c["axe"],
        "xtick.labelcolor": c["encre2"], "ytick.labelcolor": c["encre2"],
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": c["grille"],
        "grid.linewidth": 0.8, "grid.linestyle": "-", "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False,
        "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
        "legend.frameon": False, "legend.fontsize": 8.5, "legend.labelcolor": c["encre2"],
        "lines.linewidth": 2, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "patch.edgecolor": c["surface"], "patch.linewidth": 1.2,
        "axes.prop_cycle": cycler(color=SERIES), "figure.dpi": 110, "savefig.dpi": 150,
        "savefig.bbox": "tight", "figure.titlesize": 12.5, "figure.titleweight": "semibold",
    })
    return plt


def sauver_figure(fig, dossier: Path, nom: str) -> Path:
    """Enregistre la figure en PNG ; dans un notebook, l'affiche aussi (image intégrée)."""
    import matplotlib.pyplot as plt

    chemin = dossier / "figures" / f"{nom}.png"
    fig.savefig(chemin)
    plt.close(fig)
    if dans_notebook():
        from IPython.display import Image, display

        display(Image(filename=str(chemin)))
    return chemin


def format_milliers(x, _pos=None) -> str:
    """Formateur d'axe : 12 500 -> '12 500'."""
    return f"{x:,.0f}".replace(",", " ")
