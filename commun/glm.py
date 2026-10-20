"""
Outils communs aux modèles linéaires généralisés (étapes 3.1 et 3.2).

- construction des formules avec modalité de référence explicite ;
- sélection pas à pas (stepwise) bidirectionnelle sur l'AIC, avec test du rapport de vraisemblance
  à chaque étape (statistique de déviance ΔD comparée à un χ²) ;
- tableau des coefficients (avec exp(β)) et tests de suppression de chaque variable ;
- indicateurs d'erreur MAE, MSE, RMSE.
"""
from __future__ import annotations

import warnings
from typing import Callable

import numpy as np
import pandas as pd
from scipy import stats

# Variables explicatives a priori (connues à la souscription) et modalité de référence.
# Ordinales et classes : niveau le plus bas ; nominales : modalité la plus fréquente ;
# oui / non : « Non ». Le segment a pour référence S1 (risque faible).
REFERENCES = {
    "segment": "S1",
    "classe_age": "18-24", "sexe": "Femme", "classe_menage": "1-2",
    "niveau_etude": "Primaire ou moins", "revenu": "<100k", "statut_pro": "Indépendant",
    "statut_matrimonial": "Marié(e)", "lien_chef_menage": "Chef de ménage",
    "secteur": "Agriculture, élevage", "statut_residence": "Propriétaire",
    "source_eau": "Borne fontaine", "source_electricite": "Réseau JIRAMA",
    "energie_cuisine": "Charbon, gaz, électricité", "type_toilette": "Latrines",
    "transport_travail": "À pied", "epargne": "Non", "dettes": "Non",
    "effort_physique": "Parfois ou moins", "duree_effort": "<1 h", "pb_sante_travail": "Jamais",
    "arret_maladie": "Jamais", "impact_travail_sante": "Aucun", "repos_recent": "Jamais",
    "interet_couverture": "Non", "maladie_chronique": "Non", "lunettes": "Non",
    "dentiste": "Jamais", "renoncement_soins": "Non",
    "classe_heures": "≤6 h", "classe_jours": "≤5 j", "classe_budget_sante": "0 %",
    "classe_anciennete": "<5 ans", "classe_distance": "Domicile (0)",
}
CANDIDATS = list(REFERENCES)


def terme(variable: str) -> str:
    """Terme de formule patsy avec modalité de référence explicite."""
    return f'C({variable}, Treatment(reference="{REFERENCES[variable]}"))'


def formule(cible: str, variables: list[str]) -> str:
    return f"{cible} ~ " + (" + ".join(terme(v) for v in variables) if variables else "1")


def ajuster_silencieux(fonction: Callable, *args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fonction(*args, **kwargs)


def stepwise(ajuster: Callable[[list[str]], object], candidats: list[str], depart: list[str],
             journal=print, max_etapes: int = 60, critere: str = "aic") -> tuple[list[str], pd.DataFrame]:
    """Sélection pas à pas bidirectionnelle minimisant un critère d'information (AIC ou BIC).

    À chaque étape, on essaie d'ajouter chaque variable absente et de retirer chaque variable
    présente ; on applique le mouvement qui fait le plus baisser le critère et on s'arrête quand
    aucun mouvement ne le fait baisser. Pour chaque mouvement retenu, on calcule aussi le test du
    rapport de vraisemblance entre les deux modèles emboîtés : ΔD = 2 (ℓ_grand − ℓ_petit) ~ χ²(Δddl).
    AIC = −2ℓ + 2k ; BIC = −2ℓ + k·ln(n) pénalise davantage chaque paramètre.
    """
    nom = critere.upper()
    courant = list(depart)
    modele = ajuster(courant)
    historique = [{"etape": 0, "action": "départ", "variable": ", ".join(courant) or "constante",
                   "aic": modele.aic, "bic": modele.bic, "nb_parametres": len(modele.params),
                   "delta_deviance": np.nan, "ddl": np.nan, "p_value_rv": np.nan}]
    journal(f"  étape 0 : départ [{', '.join(courant) or 'constante'}] — {nom} "
            f"{getattr(modele, critere):,.1f}")
    for etape in range(1, max_etapes + 1):
        essais = []
        for v in candidats:
            if v not in courant:
                essais.append(("ajout", v, ajuster(courant + [v])))
        for v in courant:
            essais.append(("retrait", v, ajuster([c for c in courant if c != v])))
        action, variable, nouveau = min(essais, key=lambda e: getattr(e[2], critere))
        if getattr(nouveau, critere) >= getattr(modele, critere) - 1e-6:
            journal(f"  arrêt : aucun ajout ni retrait ne fait baisser le {nom} "
                    f"({getattr(modele, critere):,.1f})")
            break
        grand, petit = (nouveau, modele) if action == "ajout" else (modele, nouveau)
        dd = 2 * (grand.llf - petit.llf)
        ddl = len(grand.params) - len(petit.params)
        p = stats.chi2.sf(dd, ddl)
        courant = courant + [variable] if action == "ajout" else [c for c in courant if c != variable]
        historique.append({"etape": etape, "action": action, "variable": variable, "aic": nouveau.aic,
                           "bic": nouveau.bic, "nb_parametres": len(nouveau.params),
                           "delta_deviance": dd, "ddl": ddl, "p_value_rv": p})
        journal(f"  étape {etape} : {action} de {variable} — {nom} {getattr(nouveau, critere):,.1f} "
                f"(ΔD = {dd:.1f}, ddl = {ddl}, p = {p:.2g})")
        modele = nouveau
    return courant, pd.DataFrame(historique)


def tests_suppression(ajuster: Callable[[list[str]], object], variables: list[str]) -> pd.DataFrame:
    """Test du rapport de vraisemblance de la suppression de chaque variable (« type III »)."""
    complet = ajuster(variables)
    lignes = []
    for v in variables:
        reduit = ajuster([c for c in variables if c != v])
        dd = 2 * (complet.llf - reduit.llf)
        ddl = len(complet.params) - len(reduit.params)
        lignes.append({"variable": v, "delta_deviance": dd, "ddl": ddl,
                       "p_value": stats.chi2.sf(dd, ddl), "hausse_aic_si_retiree": reduit.aic - complet.aic})
    return pd.DataFrame(lignes).sort_values("delta_deviance", ascending=False)


def table_coefficients(resultat, exclure: tuple[str, ...] = ("alpha",)) -> pd.DataFrame:
    """Coefficients, erreurs-types, tests de Wald et exp(β) avec intervalle de confiance à 95 %."""
    ic = resultat.conf_int()
    t = pd.DataFrame({"coefficient": resultat.params, "erreur_type": resultat.bse,
                      "z": resultat.params / resultat.bse, "p_value": resultat.pvalues,
                      "exp_coef": np.exp(resultat.params), "exp_ic_bas": np.exp(ic[0]),
                      "exp_ic_haut": np.exp(ic[1])})
    t = t.drop(index=[i for i in exclure if i in t.index])
    t.index = [nom_lisible(i) for i in t.index]
    return t


def nom_lisible(parametre: str) -> str:
    """'C(segment, Treatment(reference="S1"))[T.S3]' -> 'segment = S3'."""
    if parametre.startswith("C(") and "[T." in parametre:
        variable = parametre[2:parametre.index(",")]
        modalite = parametre[parametre.index("[T.") + 3:-1]
        return f"{variable} = {modalite}"
    return parametre


class GammaMV:
    """GLM Gamma dont la log-vraisemblance est évaluée au maximum de vraisemblance de la forme.

    statsmodels calcule la log-vraisemblance (donc l'AIC) d'un GLM Gamma avec la dispersion de
    Pearson φ = χ² / ddl. Avec des coûts à queue épaisse, cet estimateur est gonflé par quelques
    grands résidus et varie fortement d'un modèle à l'autre : l'AIC qui en découle n'est pas une
    vraie log-vraisemblance et fausse la sélection de variables. Ici, les coefficients β sont ceux
    du GLM (ils ne dépendent pas de φ) et la forme k = 1/φ est estimée par maximum de
    vraisemblance, à μ̂ fixé ; l'AIC compte p coefficients + 1 paramètre de forme.
    """

    def __init__(self, resultat, y):
        from scipy import optimize, special

        self.res = resultat
        self.params = resultat.params
        mu = np.asarray(resultat.fittedvalues, float)
        y = np.asarray(y, float)

        def moins_ll(log_k):
            k = np.exp(log_k)
            return -np.sum(k * np.log(k / mu) + (k - 1) * np.log(y) - k * y / mu - special.gammaln(k))

        opt = optimize.minimize_scalar(moins_ll, bounds=(-6, 6), method="bounded")
        self.forme = float(np.exp(opt.x))
        self.phi_mv = 1 / self.forme
        self.llf = -float(opt.fun)
        self.aic = -2 * self.llf + 2 * (len(self.params) + 1)
        self.bic = -2 * self.llf + np.log(len(y)) * (len(self.params) + 1)


def erreurs(y, prediction) -> dict:
    e = np.asarray(y, dtype=float) - np.asarray(prediction, dtype=float)
    return {"MAE": np.mean(np.abs(e)), "MSE": np.mean(e ** 2), "RMSE": np.sqrt(np.mean(e ** 2))}
