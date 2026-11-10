# Notes de maintenance

Pour reprendre le projet : comment le dépôt est organisé, comment publier, et ce qu'il faut savoir du matériel.

## Le dépôt

| Dossier | Contenu |
|---|---|
| `simforge-studio-v3/` | L'application (`simforge/`), les firmwares fournis (`firmware/`), les `.bat` de lancement |
| `tests/` | Tests automatisés, sans matériel |
| `tools/capture_demo.py` | Capture d'écran d'une page en mode démo |
| `installer/`, `.github/workflows/` | Fabrication de l'installeur Windows |
| `docs/` | Ces notes et les images du README |
| `CLAUDE.md` | Organisation du code et règles, lues par Claude à chaque session |

**Branches** : `main` = ce qui est publié ; `dev` = travail en cours. Une modification se fait sur `dev`
(ou une branche créée depuis `dev`), s'essaie, puis passe dans `main`.

**GitHub Desktop** : « Fetch origin » regarde s'il y a du nouveau, « Pull origin » le récupère. « Current branch »
change de branche ; le dossier sur le PC change alors de contenu.

## Lancer depuis le code

Python 3.9 ou plus. Double-clic sur `simforge-studio-v3/SimForge Studio V3.bat` : le premier lancement crée
`.venv`. `SimForge Studio V3 (demo).bat` simule le matériel.

```
pip install -r simforge-studio-v3/requirements.txt pytest ruff
python simforge-studio-v3/simforge_studio.py --demo
python -m pytest tests
ruff check --select F,E9 --line-length 120 simforge-studio-v3 tools tests
python tools/capture_demo.py p_settings docs/images/p_settings.png --size 1400x860
```

## Publier une version

1. Vérifier que `main` contient ce qu'il faut publier.
2. GitHub › **Releases › Draft a new release** : nouvelle étiquette `vX.Y.Z` sur `main`, puis **Publish release**.
3. **Actions** lance « Installeur Windows » (tests, PyInstaller, Inno Setup). Une dizaine de minutes plus tard,
   `SimForge-Studio-Setup-X.Y.Z.exe` est attaché à la version.

Installeur d'essai sans publier : **Actions › Installeur Windows › Run workflow** ; il est dans « Artifacts »,
en bas de la page du lancement. Installer par-dessus une ancienne version la remplace.

## Journaux d'erreur

`errors.log` (erreurs avec message) et `crash.log` (fermetures brutales) : dans `simforge-studio-v3/` quand
l'appli est lancée depuis le code, dans `%LOCALAPPDATA%\SimForge Studio` quand elle est installée.

## Pédales : ce qu'il faut savoir

| Firmware (page Firmware) | Prise UART (puce CH343) | Prise USB (native) |
|---|---|---|
| Pédale active — PCB V6 (ChrGri, d'origine) | réglages et flashage | manette |
| PCB V6, un seul câble (version SimForge) | flashage seulement | réglages et manette |
| Récepteur sans fil (deux variantes) | flashage | manette et appairage |

- On flashe toujours par la prise UART.
- La carte V6 prend son 5 V sur la prise USB de l'ESP32 (pont « IN-OUT » à souder sur l'ESP32). En sans-fil,
  chaque pédale garde donc un câble USB d'alimentation, ou reçoit un convertisseur 36 V → 5 V.
- Sans fil : le récepteur reconnaît chaque pédale par son adresse rangée dans la case de son rôle. Le rôle se
  change par câble, puis on refait l'appairage.
- Filtre IMM : peut bloquer la pédale en position de départ avec le firmware fourni. Garder Kalman.
- Résistance de freinage : la valeur réglée doit être la vraie (33 Ω sur mes pédales, 8 à 10 Ω prévus par ChrGri).
- Modules ESP32-S3 N16R8 : fonctionnent sur la V6, bien que les broches 35 à 37 soient en principe réservées.
- Nom de manette : Windows garde l'ancien nom en mémoire (registre, `…\Joystick\OEM\VID_303A&PID_8331`, `OEMName`).

**Firmwares modifiés** : chaque version SimForge a son `simforge_changes.diff`, à appliquer sur le dépôt de ChrGri
(commit `7564dad`) après `firmware/build_changes.diff`, puis compilation PlatformIO
(`ControlBoard_V6_OneCable`, `Bridge_SimForge`). Détail dans `simforge-studio-v3/firmware/README.txt`.

## Volant : ce qu'il faut savoir

- Codeur entraîné par courroie 72/16 (4,5 tours par tour moteur) : pas d'index Z. Fil Z débranché, « Utiliser
  l'index Z » décoché, calage du codeur à chaque allumage (volant droit et lâché).
- Batterie d'hoverboard : son BMS coupe vers 15 A. Limiter le courant tiré sur l'alimentation, ou passer à une
  alimentation secteur.
- Assetto Corsa : gain du retour de force négatif, 900°, « Inverser uniquement les forces du jeu » décoché.
