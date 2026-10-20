"""
Étape 1.0 — Présentation des données (énoncé, partie 1).

- présente les 73 variables et leur nature (quantitative / qualitative) ;
- identifie les variables cibles (segmentation, fréquence, sévérité) ;
- réalise l'analyse descriptive des données brutes ;
- produit le tableau récapitulatif de la base.

Exécution (depuis la racine du projet) :
    .venv\\Scripts\\python.exe partie1_donnees\\1.0_presentation\\etape_1_0_presentation.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from commun import outils as o

RES = o.dossier_resultats("1.0")
log = o.Journal(RES, "Étape 1.0 — Présentation des données")
plt = o.style_graphique()

brut, libelles = o.charger_donnees_brutes()
n, p = brut.shape
log(f"Fichier : {o.FICHIER_BRUT.name} — feuille DataUsed — {n} lignes × {p} colonnes")

# ---------------------------------------------------------------------------
# 1. Dictionnaire des variables
# ---------------------------------------------------------------------------
log.section("1. Dictionnaire des variables")


def stockage(serie: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(serie):
        return "nombre"
    nombres = serie.dropna().astype(str).str.strip().str.fullmatch(r"\d+([.,]\d+)?")
    return "texte (nombres saisis en texte)" if nombres.mean() > 0.5 else "texte"


def exemples(serie: pd.Series, k: int = 3) -> str:
    vc = serie.dropna().astype(str).map(lambda s: " ".join(s.split())).value_counts()
    return " | ".join(v[:35] for v in vc.index[:k])


dico = pd.DataFrame({
    "code": o.CODES,
    "libelle_origine": [libelles[c] for c in o.CODES],
    "bloc": [o.BLOC[c] for c in o.CODES],
    "nature": [o.NATURE[c] for c in o.CODES],
    "stockage_excel": [stockage(brut[c]) for c in o.CODES],
    "nb_valeurs_distinctes": [brut[c].nunique() for c in o.CODES],
    "pct_manquants": [100 * brut[c].isna().mean() for c in o.CODES],
    "exemples": [exemples(brut[c]) for c in o.CODES],
})
o.sauver_table(dico, RES, "dictionnaire_variables")
log.table(dico.drop(columns=["libelle_origine", "exemples"]), index=False, floatfmt=".1f")

par_nature = dico.groupby("nature").size().rename("nb_variables").to_frame()
par_bloc = dico.groupby("bloc", sort=False).agg(
    nb_variables=("code", "size"), variables=("code", lambda s: ", ".join(s)))
o.sauver_table(par_nature, RES, "variables_par_nature", index=True)
o.sauver_table(par_bloc, RES, "variables_par_bloc", index=True)
log("Variables par nature :")
log.table(par_nature)
log("Variables par bloc thématique :")
log.table(par_bloc)

# ---------------------------------------------------------------------------
# 2. Variables cibles
# ---------------------------------------------------------------------------
log.section("2. Variables cibles")
couts_renseignes = brut[o.COUTS].notna().any(axis=1).sum()
cibles = pd.DataFrame([
    {"analyse": "Segmentation (K-means)",
     "variable_cible": "aucune (apprentissage non supervisé)",
     "role": "Les assurés sont regroupés selon leur profil (démographie, situation "
             "socio-économique, conditions de travail, état de santé). Le segment obtenu "
             "devient la variable cible de l'arbre CART (étape 2.2).",
     "observations_disponibles": n},
    {"analyse": "Fréquence des sinistres (GLM)",
     "variable_cible": "nb_maladies_graves",
     "role": "N_i = nombre de maladies graves déclarées sur 12 mois (comptage).",
     "observations_disponibles": int(brut["nb_maladies_graves"].notna().sum())},
    {"analyse": "Sévérité des sinistres (GLM)",
     "variable_cible": "cout_total = somme des coûts G.1 à G.6",
     "role": "S_i = coût du dernier épisode de maladie (consultation, hospitalisation, "
             "médicaments, déplacement, alimentation, autres), en Ariary. Construit à "
             "l'étape 1.1 après conversion du texte libre.",
     "observations_disponibles": int(couts_renseignes)},
])
o.sauver_table(cibles, RES, "variables_cibles")
log.table(cibles, index=False)

# ---------------------------------------------------------------------------
# 3. Tableau récapitulatif de la base
# ---------------------------------------------------------------------------
log.section("3. Tableau récapitulatif")
doublons = int(brut.drop(columns="id").duplicated().sum())
recap = pd.DataFrame([
    ("Nombre d'observations (individus)", n),
    ("Nombre de variables", p),
    ("dont identifiant", int((dico.nature == "Identifiant").sum())),
    ("dont quantitatives", int(dico.nature.str.startswith("Quantitative").sum())),
    ("dont qualitatives", int(dico.nature.str.startswith("Qualitative").sum())),
    ("dont texte libre", int((dico.nature == "Texte libre").sum())),
    ("Variables stockées en nombre dans Excel", int((dico.stockage_excel == "nombre").sum())),
    ("Variables quantitatives saisies en texte", int(((dico.stockage_excel != "nombre")
                                                     & dico.nature.str.startswith("Quantitative")).sum())),
    ("Cellules manquantes (% du total)", round(100 * brut.isna().to_numpy().mean(), 1)),
    ("Variables avec plus de 50 % de manquants", int((dico.pct_manquants > 50).sum())),
    ("Variables sans aucun manquant", int((dico.pct_manquants == 0).sum())),
    ("Lignes en double (hors identifiant)", doublons),
    ("Identifiant unique", "oui" if brut["id"].is_unique else "non"),
], columns=["caracteristique", "valeur"])
o.sauver_table(recap, RES, "tableau_recapitulatif")
log.table(recap, index=False)

# ---------------------------------------------------------------------------
# 4. Statistiques descriptives — variables quantitatives stockées en nombre
# ---------------------------------------------------------------------------
log.section("4. Statistiques descriptives des variables quantitatives (données brutes)")
quanti = [c for c in o.CODES if o.NATURE[c].startswith("Quantitative")
          and pd.api.types.is_numeric_dtype(brut[c])]
desc = brut[quanti].describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T
desc.insert(1, "manquants", n - desc["count"])
desc["asymetrie"] = brut[quanti].skew()
desc = desc.rename(columns={"count": "n", "mean": "moyenne", "std": "ecart_type", "min": "min",
                            "1%": "P1", "25%": "Q1", "50%": "mediane", "75%": "Q3",
                            "99%": "P99", "max": "max"})
o.sauver_table(desc, RES, "stats_quantitatives", index=True)
log.table(desc, floatfmt=",.1f")

# Quantitatives saisies en texte : part de nombres « propres »
texte_quanti = [c for c in o.CODES if o.NATURE[c].startswith("Quantitative")
                and not pd.api.types.is_numeric_dtype(brut[c])]
lignes = []
for c in texte_quanti:
    s = brut[c].dropna().astype(str).str.strip()
    propres = s.str.fullmatch(r"\d+([.,]\d+)?")
    lignes.append({"variable": c, "renseignees": len(s), "nombres_purs": int(propres.sum()),
                   "pct_nombres_purs": 100 * propres.mean(),
                   "exemples_non_numeriques": " | ".join(s[~propres].value_counts().index[:4])})
saisie_texte = pd.DataFrame(lignes)
o.sauver_table(saisie_texte, RES, "quantitatives_saisies_en_texte")
log("Variables quantitatives saisies en texte (converties à l'étape 1.1) :")
log.table(saisie_texte, index=False, floatfmt=".1f")

# ---------------------------------------------------------------------------
# 5. Distributions des variables qualitatives (données brutes)
# ---------------------------------------------------------------------------
log.section("5. Distributions des variables qualitatives (données brutes)")
quali = [c for c in o.CODES if o.NATURE[c].startswith("Qualitative")]
frequences, resume_quali = [], []
for c in quali:
    s = brut[c].map(lambda v: np.nan if pd.isna(v) else " ".join(str(v).split()))
    _, multiples = o.premiere_modalite(brut[c]) if c != "fokotany" else (None, pd.Series(False))
    vc = s.value_counts(dropna=False)
    for modalite, eff in vc.items():
        frequences.append({"variable": c, "modalite": "Manquant" if pd.isna(modalite) else modalite,
                           "effectif": int(eff), "pourcentage": 100 * eff / n})
    principale = vc.drop(index=[i for i in vc.index if pd.isna(i)], errors="ignore")
    resume_quali.append({
        "variable": c, "nature": o.NATURE[c], "modalites_distinctes": int(s.nunique()),
        "cellules_reponses_multiples": int(multiples.sum()),
        "modalite_principale": str(principale.index[0])[:45] if len(principale) else "",
        "pct_modalite_principale": 100 * principale.iloc[0] / n if len(principale) else np.nan,
        "pct_manquants": 100 * s.isna().mean()})
frequences = pd.DataFrame(frequences)
resume_quali = pd.DataFrame(resume_quali)
o.sauver_table(frequences, RES, "frequences_qualitatives")
o.sauver_table(resume_quali, RES, "resume_qualitatives")
log.table(resume_quali, index=False, floatfmt=".1f")

# Variable de fréquence : distribution complète
freq_n = brut["nb_maladies_graves"].value_counts(dropna=False).sort_index()
freq_n.index = freq_n.index.map(lambda v: "Manquant" if pd.isna(v) else int(v))
o.sauver_table(freq_n.rename("effectif").to_frame(), RES, "distribution_nb_maladies_graves", index=True)
m, v = brut["nb_maladies_graves"].mean(), brut["nb_maladies_graves"].var()
log(f"nb_maladies_graves : moyenne {m:.2f}, variance {v:.1f}, variance / moyenne {v / m:.1f}")

# ---------------------------------------------------------------------------
# 6. Figures
# ---------------------------------------------------------------------------
C = o.COULEURS
BLEU = o.SERIES[0]

# 6.1 Taux de manquants par variable
d = dico.sort_values("pct_manquants")
fig, ax = plt.subplots(figsize=(8, 13))
ax.barh(d.code, d.pct_manquants, color=BLEU, height=0.62)
for seuil, texte in [(5, "5 %"), (50, "50 %")]:
    ax.axvline(seuil, color=C["attenue"], lw=0.8)
    ax.text(seuil + 0.8, 1, texte, color=C["encre2"], fontsize=8, va="center")
ax.set_xlim(0, 100)
ax.grid(axis="x")
ax.grid(axis="y", visible=False)
ax.set_xlabel("Valeurs manquantes (% des 4 076 individus)")
ax.set_title("Taux de valeurs manquantes par variable (données brutes)")
ax.tick_params(axis="y", labelsize=7.5)
ax.margins(y=0.005)
o.sauver_figure(fig, RES, "manquants_par_variable")

# 6.2 Âge
fig, ax = plt.subplots(figsize=(8, 3.6))
age = brut["age"].dropna()
ax.hist(age.clip(upper=70), bins=np.arange(15, 72, 1), color=BLEU, rwidth=0.82)
ax.set_xlabel("Âge (années) — valeurs > 70 regroupées à 70")
ax.set_ylabel("Nombre d'individus")
ax.set_title(f"Distribution de l'âge (médiane {age.median():.0f} ans)")
hors = int(((age < 15) | (age > 70)).sum())
ax.text(0.99, 0.95, f"{hors} âges hors de 15–70 ans (3, 5, 72, 80, 85, 107, 112)",
        transform=ax.transAxes, ha="right", va="top", fontsize=8, color=C["encre2"])
o.sauver_figure(fig, RES, "distribution_age")

# 6.3 Nombre de maladies graves (variable de fréquence)
nm = brut["nb_maladies_graves"].dropna()
classes = list(range(0, 11)) + ["11+"]
eff = [int((nm == k).sum()) for k in range(0, 11)] + [int((nm > 10).sum())]
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar([str(k) for k in classes], eff, color=BLEU, width=0.62)
ax.set_xlabel("Nombre de maladies graves sur 12 mois")
ax.set_ylabel("Nombre d'individus")
ax.set_title("Variable de fréquence : nombre de maladies graves déclarées")
ax.annotate(f"{eff[-1]} individus déclarent plus de 10 maladies\n(jusqu'à 365) ; 1 valeur négative",
            xy=(11, eff[-1]), xytext=(8.2, max(eff) * 0.55), fontsize=8, color=C["encre2"],
            arrowprops=dict(arrowstyle="-", color=C["attenue"], lw=0.8))
o.sauver_figure(fig, RES, "distribution_nb_maladies_graves")

# 6.4 Principales variables qualitatives (petits multiples, une couleur)
def libelle_court(v: str) -> str:
    v = re.sub(r"^\d+\.\s*", "", " ".join(str(v).split()))
    v = re.sub(r"\s*\([^)]*\)", "", v)
    return v[:28]


choix = [("sexe", "Sexe"), ("niveau_etude", "Niveau d'étude"), ("revenu", "Revenu mensuel (Ar)"),
         ("statut_pro", "Statut professionnel"), ("maladie_chronique", "Maladie chronique"),
         ("renoncement_soins", "Renoncement aux soins (raisons financières)")]
fig, axes = plt.subplots(2, 3, figsize=(12, 6.4))
for ax, (c, titre) in zip(axes.ravel(), choix):
    resolu, multiples = o.premiere_modalite(brut[c])
    s = resolu.map(lambda v: np.nan if v is None else libelle_court(v))
    s[multiples] = "Réponses multiples"
    vc = s.value_counts(dropna=False)
    vc.index = vc.index.map(lambda v: "Manquant" if pd.isna(v) else v)
    vc = vc.sort_values()
    ax.barh(vc.index, 100 * vc.values / n, color=BLEU, height=0.6)
    for y, val in enumerate(100 * vc.values / n):
        ax.text(val + 1, y, f"{val:.1f} %", va="center", fontsize=7.5, color=C["encre2"])
    ax.set_xlim(0, 105)
    ax.set_title(titre, fontsize=10)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=7.5)
fig.suptitle("Principales variables qualitatives (% des individus, données brutes)", x=0.01,
             ha="left")
fig.tight_layout()
o.sauver_figure(fig, RES, "variables_qualitatives_principales")

# 6.5 Variables quantitatives (histogrammes, affichage limité au 99e centile)
choix = [("taille_menage", "Taille du ménage"), ("nb_actifs_menage", "Actifs dans le ménage"),
         ("budget_alim", "% budget alimentation"), ("budget_sante", "% budget santé"),
         ("budget_elec", "% budget électricité"), ("prime_souhaitee", "Prime mensuelle souhaitée (Ar)")]
fig, axes = plt.subplots(2, 3, figsize=(12, 6.2))
for ax, (c, titre) in zip(axes.ravel(), choix):
    s = brut[c].dropna()
    p99 = s.quantile(0.99)
    ax.hist(s[s <= p99], bins=30, color=BLEU, rwidth=0.85)
    ax.set_title(titre, fontsize=10)
    ax.text(0.98, 0.95, f"{int((s > p99).sum())} valeurs > P99 ({p99:,.0f})\nmax = {s.max():,.0f}"
            .replace(",", " "), transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
            color=C["encre2"])
    ax.xaxis.set_major_formatter(o.format_milliers)
fig.suptitle("Variables quantitatives stockées en nombre (affichage jusqu'au 99e centile)",
             x=0.01, ha="left")
fig.tight_layout()
o.sauver_figure(fig, RES, "variables_quantitatives")

log.section("Fichiers produits")
for f in sorted(RES.rglob("*.*")):
    log("-", f.relative_to(o.RACINE))
log.fermer()
