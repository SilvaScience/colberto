# Rapport de session — Calibration LUT multi-longueur d'onde du SLM

**Date :** 2026-08-02
**Branche :** `LUT_callibration_all_wavelenght` (à partir de `Bug_Streising`)
**Sujet :** correction de la calibration phase→greyscale du SLM pour tenir compte de la largeur spectrale du pulse, en prévision du NOPA

## 1. Contexte et problème posé

Aujourd'hui, une seule LUT (Look-Up Table) de calibration phase→greyscale est chargée dans le SLM, calibrée à une seule longueur d'onde λ_cal (`Generate_LUT_PhasetoGreyscale`, mesurée via `Measure_LUT_PhasetoGreyscale`). Le pulse a une largeur spectrale finie ; avec l'OPA actuel (bande étroite), l'écart entre λ_cal et les bords du spectre est faible et l'effet est négligeable. Avec le NOPA en construction (bande beaucoup plus large), cet écart devient significatif et pourrait dégrader la performance du façonnage.

La question de départ : est-ce que calibrer à une seule longueur d'onde introduit une erreur de **phase** (donc de compression), ou autre chose ? Et peut-on corriger sans multiplier les mesures de calibration ?

## 2. Physique détaillée

### 2.1 Le SLM façonne par diffraction, pas par modulation de phase directe

COLBERTo utilise un façonnage de type Turner/Nelson : un réseau de phase en dent de scie (`Beam.makeGrating`/`generate_1Dgrating`) diffracte la lumière, et l'ordre 1 de diffraction porte la phase désirée via le **décalage latéral** du réseau (`offset = phase/(2π) · period`). Ce n'est pas une modulation de phase directe où chaque pixel imposerait sa phase telle quelle.

### 2.2 Décomposition de Fourier du réseau en dents de scie

Pour un réseau en dents de scie d'amplitude réelle *A* (A=1 correspondant à une excursion de phase de 2π exactement) portant une phase désirée φ, l'amplitude complexe de l'ordre de diffraction 1 est :

$$c_1 = \mathrm{sinc}(A-1)\, e^{i\pi(A-1)}\, e^{-i\varphi}$$

où sinc(x) = sin(πx)/(πx). Deux conséquences directes :

- **Efficacité de diffraction** : η₁ = |c₁|² = sinc²(A-1). Maximale (100 %) pour A=1, décroît de part et d'autre.
- **Erreur de phase** : un terme supplémentaire π(A-1), qui s'ajoute à -φ.

### 2.3 D'où vient l'amplitude réelle A ?

Le SLM ne contrôle pas directement une "phase" — il contrôle une **tension**, qui incline les molécules de cristal liquide, qui change leur biréfringence Δn, qui produit une **retardance** :

$$\Gamma(g) = \Delta n(g)\cdot d$$

une longueur physique, indépendante de la couleur de la lumière. La phase vue par une longueur d'onde λ donnée est :

$$\varphi = \frac{2\pi\,\Gamma}{\lambda}$$

La calibration actuelle (`Generate_LUT_PhasetoGreyscale`) mesure φ(g) à λ_cal et reprogramme la LUT matérielle pour que g soit exactement linéaire en phase à λ_cal (g=1023 ↔ φ=2π à λ_cal). Comme Γ = φ_cal·λ_cal/2π, cela rend **automatiquement Γ linéaire en g** :

$$\Gamma(g) = \lambda_{cal}\cdot\frac{g}{1023}$$

C'est le point clé : la calibration existante calibre en réalité la **retardance**, pas la phase — la phase-à-λ_cal n'en est qu'une lecture particulière.

### 2.4 Le bug caché : envoyer g calculé pour λ_cal à une colonne d'une autre longueur d'onde

Le code actuel calcule `g = 1023·φ_désirée/2π` partout, peu importe la colonne. Cela revient à demander la retardance Γ = φ_désirée·λ_cal/2π. Mais si la lumière réelle à cette colonne est à λ(x) ≠ λ_cal, la phase réellement produite est :

$$\varphi_{réel} = \frac{2\pi\Gamma}{\lambda(x)} = \varphi_{désirée}\cdot\frac{\lambda_{cal}}{\lambda(x)}$$

C'est-à-dire A = λ_cal/λ(x) dans la formule du §2.2 — une erreur d'**amplitude du réseau**, pas une erreur de phase arbitraire.

### 2.5 Quantification

Avec λ_cal = 785 nm (calculs faits pendant la session) :

| λ | A | Efficacité η₁ | Perte |
|---|---|---|---|
| 650 nm | 1,208 | 86,6 % | 13,4 % |
| 700 nm | 1,121 | 95,2 % | 4,8 % |
| 785 nm | 1,000 | 100 % | 0 % |
| 900 nm | 0,872 | 94,7 % | 5,3 % |
| 950 nm | 0,826 | 90,5 % | 9,5 % |

Décomposition du terme de phase π(A-1) en ordres de dispersion (delai de groupe GD, GDD, TOD), sur 650-950 nm :

| | GD | GDD | TOD |
|---|---|---|---|
| sans dispersion de Δn(λ) | +1,31 fs | 0,00 fs² | 0,0 fs³ |
| avec dispersion Δn(λ) réaliste (cristal liquide) | +1,52 fs | **+0,29 fs²** | +0,2 fs³ |

Le terme π(A-1) est **exactement linéaire en ω** (fréquence angulaire) tant qu'on néglige la dispersion de Δn — ce n'est qu'un délai de groupe commun, qui s'annule dans toute mesure interférométrique. Le résidu dû à la dispersion réelle du cristal liquide (~0,3 fs² de GDD) est négligeable devant les valeurs typiquement corrigées (des centaines à milliers de fs²).

**Conclusion physique : calibrer à une seule longueur d'onde ne dégrade pratiquement pas la compression.** Le vrai coût est en **efficacité de diffraction** (jusqu'à ~20 % de perte aux bords de bande avec le NOPA), qui agit comme un filtre spectral et allonge légèrement l'impulsion effective.

### 2.6 Correction proposée : LUT linéaire en retardance, pas en phase

Puisque g et Γ sont déjà liés linéairement par la calibration existante (§2.3), on inverse pour obtenir le greyscale corrigé qui produit la bonne phase à la bonne longueur d'onde locale :

$$g_{corrigé}(x) = g_{naïf}(x)\cdot\frac{\lambda(x)}{\lambda_{cal}}$$

Une simple multiplication par colonne, appliquée juste avant l'écriture de l'image au SLM — **aucune nouvelle mesure de calibration nécessaire**, puisque la mesure actuelle (à une seule λ_cal) donne déjà Γ(g) en entier via la relation ci-dessus.

### 2.7 Contrainte matérielle

Pour atteindre 2π à λ, il faut Γ_max ≥ λ. Puisque Γ_max = λ_cal (retardance maximale du panneau, par construction de la calibration), on ne peut physiquement pas produire un réseau de pleine amplitude (2π) à une longueur d'onde λ > λ_cal. Vérifié empiriquement (scan de l'ancien SLM 8 bits en rouge/vert, communiqué pendant la session) : marge confortable, plusieurs périodes de 2π sur la plage balayée — donc pas de blocage pour l'instant, mais un point à garder en tête en élargissant vers le NOPA.

### 2.8 Piste de validation future (non implémentée aujourd'hui)

Le modèle ci-dessus peut être testé expérimentalement sans nouvelle infrastructure : `Measure_LUT_PhasetoGreyscale` balaie déjà le greyscale sur toute la largeur du SLM et enregistre le spectre complet à chaque valeur — la mesure est donc déjà résolue en longueur d'onde, seule l'analyse actuelle l'intègre sur une fenêtre de ±50 nm autour d'une seule `central_wavelength` et jette le reste.

Protocole proposé (à faire une fois le NOPA disponible, où l'écart entre les 3 points serait significatif) :
1. Extraire Γ(g) depuis une mesure au centre du spectre.
2. Prédire analytiquement φ(g) aux deux extrémités via φ = 2πΓ(g)/λ.
3. Mesurer réellement φ(g) aux deux extrémités (réanalyse de la même acquisition, fenêtres différentes).
4. Comparer prédiction et mesure : un bon accord confirme le modèle (donc le correctif ci-dessus suffit) ; un désaccord révélerait une physique non modélisée (ex. dispersion de Δn plus forte que l'estimation du §2.5) et donnerait directement les 3 courbes nécessaires pour une correction empirique interpolée à la place.

## 3. Implémentation

### 3.1 `src/drivers/SLM.py` (pilote réel Meadowlark) et `src/drivers/SLMDemo.py` (démo, logique identique)

- `SLMWorker` : nouvel état `calibration_wavelength` (λ_cal, mètres) et `wavelength_axis` (λ(x) par colonne, mètres) — `None` par défaut, aucune correction tant que les deux ne sont pas fixés (comportement identique à avant).
- `set_calibration_wavelength(λ_m)` / `set_wavelength_axis(axis_m)` — setters, exposés aussi sur les classes `Slm`/`SLMDemo` (wrappers), qui délèguent au worker.
- `apply_wavelength_correction(digital_image, max_value)` — implémente g_corrigé = g_naïf × λ(x)/λ_cal, borne le résultat à [0, max_value], émet un avertissement dans le log (limité à 1×/seconde) si la correction sature — signe qu'une phase demandée dépasse ce que le panneau peut produire à cette longueur d'onde locale.
- Câblée dans `change_image()`, juste après la conversion phase→greyscale existante (`normalize_phase_image`).
- Choix d'architecture : la correction vit dans `SLMWorker` (toujours disponible dès la construction), pas dans l'objet matériel bas niveau (`self.slm`, créé de façon asynchrone dans le thread du worker) — évite une course entre l'initialisation matérielle et l'arrivée de la calibration spectrale.

### 3.2 `src/main.py`

- `assign_spectral_calibration()` — calcule l'axe λ(x) sur toute la largeur du SLM à partir de la calibration spectrale déjà existante (`DataHandling.calibration['spectral_calibration_fit']`) et le pousse au SLM via `set_wavelength_axis`.
- `Generate_LUT_PhasetoGreyscale()` (génération d'un nouveau LUT) — pousse automatiquement λ_cal (conversion nm→m) depuis le spinbox `LUT_calib_central_wavelength_value` déjà présent dans l'interface.
- `Load_LUT_PhasetoGrayscale()` (chargement manuel d'un ancien fichier `.lut`) — pousse aussi λ_cal depuis le même spinbox, en filet de sécurité manuel (le format `.lut` du fabricant ne contient que deux colonnes greyscale/tension, aucune métadonnée possible).
- Nouveau label permanent dans la barre de statut (`statusbar.addPermanentWidget`), affichant le nom du fichier `.lut` chargé ou généré — puisque la longueur d'onde de calibration n'est pas récupérable du fichier lui-même, mais est en général incluse dans son nom par convention. **Aucune extraction de sous-chaîne automatique n'est faite** (jugé trop fragile) — l'utilisateur lit le nom lui-même.

### 3.3 `src/measurements/Calibration_Classes.py`

- Nouveau signal `sendSavedPath` sur `Generate_LUT_PhasetoGreyscale`, émis une fois le fichier `.lut` réellement sauvegardé, pour que `main.py` puisse mettre à jour le label de nom de fichier (le chemin était auparavant choisi via une boîte de dialogue interne au thread de mesure, jamais remonté nulle part).

### 3.4 Bug trouvé et corrigé en testant

`digital_image.astype(dtype)` **tronque** vers zéro plutôt que d'arrondir — biais systématique toujours vers le bas. Corrigé en `np.round(clipped).astype(dtype)` dans les deux fichiers pilotes.

### 3.5 Tests effectués

Aucun matériel disponible côté développement. Tests unitaires hors-écran (`QT_QPA_PLATFORM=offscreen`), sur les deux pilotes (réel et démo, le réel instancié via `__new__` pour éviter la dépendance au fichier de configuration externe) :
- Comportement neutre (aucun changement) tant que la calibration n'est pas fixée
- Sens physique correct de la correction (réduit sous λ_cal, augmente au-dessus)
- Saturation correctement bornée, avec avertissement limité en fréquence
- Type de données (dtype) préservé
- Garde-fou si l'axe de longueur d'onde a une taille incompatible avec l'image (pas de crash)

## 4. Limites connues et travail futur

- **Pas de test sur matériel réel** — tout le raisonnement ci-dessus repose sur la physique et sur des tests logiciels ; à confirmer une fois le NOPA disponible.
- **La dispersion Δn(λ) du cristal liquide est estimée, pas mesurée** sur le panneau actuel (valeur représentative d'un nématique typique) — le protocole du §2.8 permettrait de la mesurer réellement.
- **Le spinbox `LUT_calib_central_wavelength_value` ne se restaure pas automatiquement** après le chargement d'une calibration sauvegardée (limite déjà présente avant ce travail) — donc après un chargement, sa valeur peut ne plus refléter λ_cal réelle tant qu'elle n'est pas re-confirmée manuellement.
- **Validation à 3 points (§2.8)** — pas implémentée aujourd'hui, à faire une fois le NOPA en service.
