# SimForge Studio

Appli de bureau Windows (Python 3.9+, PySide6 + pyqtgraph) qui règle un volant Odrive-Wheel (carte ODrive v3.6)
et les pédales actives DIY de ChrGri (PCB V6, ESP32-S3), sans autre logiciel. Le propriétaire écrit en français.

## Arborescence
Tout le code est dans `simforge-studio-v3/` :
- `simforge_studio.py` : point d'entrée (`--demo` = matériel simulé). Les `.bat` créent `.venv` et lancent l'appli.
- `simforge/app.py` : fenêtre principale, menu de gauche (clés de page `w_*` volant, `p_*` pédales, `t_*` outils), `VERSION`.
- Volant : `ow_protocol.py` (commandes série + télémétrie HID), `ow_device.py` (`Board`), onglets `tab_setup/params/monitor/encoder/force/console/overlay.py`.
- Pédales : `ped_layout.py` (structures binaires générées depuis les en-têtes C de ChrGri, ne pas éditer à la main),
  `ped_protocol.py` (trames, `VERSION` de structure = 174, contrôles `plausible()`, catalogue `PFIELDS` des réglages affichés,
  chacun rangé dans un groupe `G_*`), `ped_device.py` (`PedalManager`, un thread par port, pédales simulées en démo),
  `tab_pedals.py` (page Réglages), `tab_pedal_fw.py` (flashage).
- `widgets.py` (`card`, `hint`, `AxisBar`…, `WheelGuard` : filtre global installé par `app.py`, la molette ne modifie
  un champ que s'il a été cliqué), `theme.py` (couleurs `C`, feuille de style `QSS`).
- `firmware/` : binaires des pédales et du récepteur (licence CC BY-NC-SA de ChrGri). Ne jamais modifier les `.bin`.

## Règles du code
- Textes d'interface écrits en français dans `T("…")` ; chaque nouveau texte doit avoir sa traduction dans
  `simforge/i18n_en.py` (clé = texte français exact). L'anglais est la langue par défaut.
- Style existant : commentaires et noms courts en français, lignes ≤ 120 caractères, pas de nouvelle dépendance sans raison.
- Réglages des pédales : ajouter/déplacer un réglage = une entrée `PField` dans `ped_protocol.PFIELDS` ; garder libellés,
  unités et plages existants sauf demande explicite. Référence : https://github.com/ChrGri/DIY-Sim-Racing-FFB-Pedal
  (firmware `ESP32/`, plugin `SimHubPlugin/`).
- Une seule appli ouvre un port série à la fois (SimHub, outil web Odrive… doivent être fermés).

## Vérifier sans matériel
```
pip install -r simforge-studio-v3/requirements.txt
python simforge-studio-v3/simforge_studio.py --demo                 # appli complète, matériel simulé
python tools/capture_demo.py p_settings capture.png [--lang en]     # capture d'une page sans fenêtre
```
Sous Linux sans écran il faut `libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3`.
Pas de tests automatisés : vérifier par la démo (pédales simulées « Frein » et « Accélérateur ») et regarder la capture.

## Git
- `main` = versions stables taguées (`v3.0.0`, …) ; `dev` = intégration ; une branche par sujet, créée depuis `dev`.
- Ne pas pousser sur `main` sans accord ; fusionner dans `dev` après essai par le propriétaire.
- Messages de commit en français. Ne pas versionner `.venv/`, `__pycache__/`, `errors.log`, `build/`, `dist/`.
