"""English strings (key = French source text)."""

EN = {
    'Port série : réglages et commandes':
        'Serial port: settings and commands',
    'Réglages':
        'Settings',
    'HID : télémétrie à 1 kHz et retour de force':
        'HID: 1 kHz telemetry and force feedback',
    'Mesures':
        'Telemetry',
    'Recherche de la carte…':
        'Looking for the board…',
    'Activer le moteur':
        'Enable motor',
    "Passe l'axe en boucle fermée : le moteur est alimenté et applique les forces.":
        'Puts the axis in closed loop: the motor is powered and applies the forces.',
    "Met l'axe au repos : le moteur n'est plus alimenté du tout (jeux compris) et le reste tant que le STOP est enclenché. Raccourci : Échap.\nNe remplace pas la coupure matérielle de l'alimentation.":
        'Puts the axis in idle: the motor is no longer powered at all (games included) and stays so while STOP is latched. Shortcut: Esc.\nDoes not replace cutting the power supply.',
    'Mise en route':
        'Setup',
    'Moniteur':
        'Monitor',
    'Codeur':
        'Encoder',
    'Journal':
        'Log',
    'Recentrer le volant':
        'Recenter wheel',
    'Le volant prend sa position actuelle comme centre (mémorisé avec « Enregistrer »).':
        'The wheel takes its current position as the center (stored with “Save”).',
    'Effacer les erreurs':
        'Clear errors',
    'Mode DFU…':
        'DFU mode…',
    "Redémarre la carte dans son chargeur DFU pour la reflasher (STM32CubeProgrammer), sans toucher à l'interrupteur.":
        'Reboots the board into its DFU bootloader to reflash it (STM32CubeProgrammer), without touching the switch.',
    'Redémarrer la carte':
        'Reboot board',
    'Enregistrer dans la carte':
        'Save to board',
    "Mémorise les réglages volant/effets (sans redémarrer) et, s'il y en a, les réglages ODrive (moteur au repos, la carte redémarre et refait son calage).":
        'Stores the wheel/effect settings (no reboot) and, if any, the ODrive settings (motor idle, the board reboots and redoes its alignment).',
    'Prêt':
        'Ready',
    'Codeur pas calé':
        'Encoder not aligned',
    "Le codeur n'a pas été calé depuis l'allumage : la carte ne sait pas où est le rotor. Lancer le calage maintenant ? Le moteur va tourner d'environ un tour : lâche le volant.":
        'The encoder has not been aligned since power-up: the board does not know where the rotor is. Run the alignment now? The motor will turn about one revolution: let go of the wheel.',
    'Réarmer':
        'Re-arm',
    'Le moteur est au repos. Que faire ?':
        'The motor is idle. What now?',
    'Réarmer et activer le moteur':
        'Re-arm and enable motor',
    'Réarmer, moteur au repos':
        'Re-arm, motor idle',
    'Garder le STOP':
        'Keep STOP',
    'Le volant est sorti de la course réglée pendant un essai':
        'The wheel left the configured range during a test',
    'Coupure de sécurité':
        'Safety cut-off',
    'DÉMO':
        'DEMO',
    'Firmware':
        'Firmware',
    'Version de firmware':
        'Firmware version',
    'réglages volant/effets':
        'wheel/effect settings',
    'réglages ODrive':
        'ODrive settings',
    "Le moteur va être alimenté et appliquer les forces (jeu, ressort au repos, butées). Garde la main près de la coupure d'alimentation. Continuer ?":
        'The motor will be powered and apply forces (game, idle spring, end stops). Keep a hand near the power switch. Continue?',
    'Enregistrer':
        'Save',
    "Mémoriser les réglages volant et effets ?\n\nAucun réglage ODrive n'a été changé depuis la lecture. Mémoriser aussi la configuration ODrive (la carte redémarre) ?":
        'Store the wheel and effect settings?\n\nNo ODrive setting has changed since it was read. Also store the ODrive configuration (the board reboots)?',
    'Les réglages non mémorisés seront perdus et la carte refera son calage au démarrage (le volant bouge). Continuer ?':
        'Unsaved settings will be lost and the board will redo its alignment at start-up (the wheel moves). Continue?',
    'Mode DFU':
        'DFU mode',
    "La carte va quitter le mode volant et attendre un nouveau firmware (STM32CubeProgrammer, USB). Elle reviendra au firmware actuel après un débranchement/rebranchement si rien n'est flashé. Continuer ?":
        'The board will leave wheel mode and wait for new firmware (STM32CubeProgrammer, USB). It returns to the current firmware after unplugging/replugging if nothing is flashed. Continue?',
    'STOP VOLANT':
        'WHEEL STOP',
    'STOP VOLANT ENCLENCHÉ — RÉARMER':
        'WHEEL STOP LATCHED — RELEASE',
    'STOP ENCLENCHÉ — RÉARMER':
        'STOP LATCHED — RELEASE',
    'Connecté':
        'Connected',
    'Port série seul (pas de télémétrie HID)':
        'Serial port only (no HID telemetry)',
    'MOTEUR ACTIF':
        'MOTOR ACTIVE',
    'Modifications appliquées : clique de nouveau « Enregistrer » une fois relues.':
        'Changes applied: click “Save” again once they have been read back.',
    "Des réglages ODrive ont changé : le moteur va être mis au repos, la configuration mémorisée, puis la carte redémarre et refait son calage (le volant bouge d'environ un tour). Lâche le volant. Continuer ?":
        'ODrive settings changed: the motor will be set to idle, the configuration stored, then the board reboots and redoes its alignment (the wheel moves about one revolution). Let go of the wheel. Continue?',
    'Réglages volant/effets mémorisés':
        'Wheel/effect settings stored',
    'Configuration ODrive mémorisée, la carte redémarre…':
        'ODrive configuration stored, the board is rebooting…',
    'Vitesse mesurée {v} °/s pendant un essai':
        'Measured speed {v} °/s during a test',
    "{what} : moteur mis au repos.\n\nCauses probables d'un emballement : calage du codeur faux, CPR ou paires de pôles faux, courroie qui saute, parasites sur le codeur.\nLe STOP reste enclenché : réarme-le quand le volant est sous contrôle.":
        '{what}: motor set to idle.\n\nLikely causes of a runaway: wrong encoder alignment, wrong CPR or pole pairs, skipping belt, encoder noise.\nSTOP stays latched: re-arm it once the wheel is under control.',
    "Télémétrie seule : port série occupé ? (ferme l'outil web)":
        'Telemetry only: serial port busy? (close the web tool)',
    'La carte répond « {h} » : SimForge Studio V3 est fait pour le firmware Odrive-Wheel.':
        'The board answers “{h}”: SimForge Studio V3 is made for the Odrive-Wheel firmware.',
    'La carte annonce une base ODrive {v}. SimForge Studio V3 a été écrit pour Odrive-Wheel sur ODrive 0.5.6 : vérifie les valeurs avant de les modifier.':
        'The board reports ODrive base {v}. SimForge Studio V3 was written for Odrive-Wheel on ODrive 0.5.6: check the values before changing them.',
    'Matériel annoncé : v{h}':
        'Reported hardware: v{h}',
    'ERREUR : {e}':
        'ERROR: {e}',
    'MOTEUR AU REPOS':
        'MOTOR IDLE',
    'Non mémorisé : {l}':
        'Not stored: {l}',
    "{n} modification(s) pas encore appliquée(s). Les appliquer avant d'enregistrer ?":
        '{n} change(s) not applied yet. Apply them before saving?',
    'Mémorisation refusée : {m}':
        'Storing refused: {m}',
    "Le port série ne peut être ouvert que par un seul programme à la fois : ferme l'outil web Odrive-Wheel, la console odrivetool ou SimHub (plugin Odrive-Wheel).":
        'The serial port can only be opened by one program at a time: close the Odrive-Wheel web tool, the odrivetool console or SimHub (Odrive-Wheel plugin).',
    'Déconnecté':
        'Disconnected',
    'Télémétrie HID reçue (1 kHz)':
        'HID telemetry received (1 kHz)',
    'pas de réponse':
        'no answer',
    'carte injoignable':
        'board unreachable',
    'mémorisation + redémarrage':
        'store + reboot',
    'redémarrage':
        'reboot',
    'mode DFU':
        'DFU mode',
    'effacement de la configuration':
        'configuration erase',
    "STOP enclenché : réarme-le avant d'activer le moteur.":
        'STOP latched: re-arm it before enabling the motor.',
    'carte non connectée':
        'board not connected',
    'Port série {p} ouvert ({h})':
        'Serial port {p} open ({h})',
    'Réglages lus ({n} valeurs)':
        'Settings read ({n} values)',
    'La carte redémarre ({w})…':
        'The board is rebooting ({w})…',
    'plus de rapport HID':
        'no more HID reports',
    'STOP':
        'STOP',
    "STOP : port série non connecté, la carte n'a pas pu être mise au repos ! Coupe l'alimentation.":
        'STOP: serial port not connected, the board could not be set to idle! Cut the power.',
    'Port série non connecté.':
        'Serial port not connected.',
    'Port série perdu ({w})':
        'Serial port lost ({w})',
    'Non disponibles sur ce firmware : {l}':
        'Not available on this firmware: {l}',
    "Télémétrie HID perdue ({w}). Depuis l'ouverture : {n} rapports n°1, {o} autres rapports, {e} erreurs de lecture.":
        'HID telemetry lost ({w}). Since opening: {n} reports #1, {o} other reports, {e} read errors.',
    'Commande ignorée : carte non connectée.':
        'Command ignored: board not connected.',
    'HID ouvert : {p} (usage {u:04X}:{v:04X}, {n} interface(s) trouvée(s))':
        'HID open: {p} (usage {u:04X}:{v:04X}, {n} interface(s) found)',
    'DÉPASSEMENT DE COURSE':
        'OUT OF RANGE',
    '(pas de réponse)':
        '(no answer)',
    'Écriture refusée : {p} = {v} ({m})':
        'Write refused: {p} = {v} ({m})',
    "Boucle fermée refusée : le codeur n'est pas calé depuis l'allumage.":
        'Closed loop refused: the encoder has not been aligned since power-up.',
    '→ erreurs effacées (résistance de freinage réarmée)':
        '→ errors cleared (brake resistor re-armed)',
    'SURVITESSE {v} °/s':
        'OVERSPEED {v} °/s',
    'Erreurs effacées avant la commande : {e}':
        'Errors cleared before the command: {e}',
    '→ état demandé : {s}':
        '→ requested state: {s}',
    '(la carte a retenu {v})':
        '(the board kept {v})',
    '→ centre du volant pris à la position actuelle ({v})':
        '→ wheel center set to the current position ({v})',
    'STOP : axe mis au repos, moteur non alimenté':
        'STOP: axis set to idle, motor not powered',
    'STOP réarmé, moteur laissé au repos':
        'STOP re-armed, motor left idle',
    'STOP réarmé : boucle fermée demandée':
        'STOP re-armed: closed loop requested',
    "STOP réarmé, moteur laissé au repos : le codeur n'est pas calé (onglet Mise en route).":
        'STOP re-armed, motor left idle: the encoder is not aligned (Setup tab).',
    'STOP : commande refusée ({m})':
        'STOP: command refused ({m})',
    'Réglages volant et effets mémorisés (sys.save)':
        'Wheel and effect settings stored (sys.save)',
    "Le moteur ne s'est pas mis au repos : réglages ODrive non mémorisés.":
        'The motor did not go idle: ODrive settings not stored.',
    'moteur pas au repos':
        'motor not idle',
    'Mémorisation volant/effets refusée ({v})':
        'Storing wheel/effects refused ({v})',
    'Axe':
        'Axis',
    'Moteur':
        'Motor',
    'Contrôleur':
        'Controller',
    'Système':
        'System',
    'Course et couple':
        'Range and torque',
    "Effets permanents (s'ajoutent au jeu)":
        'Permanent effects (added to the game)',
    'Butées électroniques':
        'Electronic end stops',
    'Courbe et lissage du couple':
        'Torque curve and smoothing',
    'Gains des effets du jeu':
        'Game effect gains',
    'Filtres passe-bas par effet':
        'Low-pass filters per effect',
    'Égaliseur 3 bandes':
        '3-band equalizer',
    'Calibration moteur':
        'Motor calibration',
    'Contrôle et sécurité vitesse':
        'Control and speed safety',
    'Au démarrage de la carte':
        'At board start-up',
    'Alimentation et protections':
        'Power supply and protections',
    'Résistance de freinage':
        'Brake resistor',
    'Température de la carte':
        'Board temperature',
    'indéfini':
        'undefined',
    'au repos (moteur libre)':
        'idle (motor free)',
    'séquence de démarrage':
        'start-up sequence',
    'calibration complète':
        'full calibration',
    'calibration moteur':
        'motor calibration',
    "recherche de l'index":
        'index search',
    'calage du codeur':
        'encoder alignment',
    'boucle fermée (actif)':
        'closed loop (active)',
    'rotation forcée':
        'lock-in spin',
    'recherche du sens du codeur':
        'encoder direction search',
    "prise d'origine":
        'homing',
    'calibration Hall (polarité)':
        'Hall calibration (polarity)',
    'calibration Hall (phase)':
        'Hall calibration (phase)',
    'Courant fort (moteur classique)':
        'High current (standard motor)',
    'Gimbal (régulation en tension)':
        'Gimbal (voltage control)',
    'Asynchrone (ACIM)':
        'Induction (ACIM)',
    'Incrémental A/B':
        'Incremental A/B',
    'Tension':
        'Voltage',
    'Couple (obligatoire pour le volant)':
        'Torque (required for the wheel)',
    'Vitesse':
        'Speed',
    'Position':
        'Position',
    'Inactif':
        'Inactive',
    'Direct (passthrough)':
        'Direct (passthrough)',
    'Rampe de vitesse':
        'Velocity ramp',
    'Filtre de position':
        'Position filter',
    'Trajectoire trapèze':
        'Trapezoidal trajectory',
    'Rampe de couple':
        'Torque ramp',
    'Désactivé':
        'Disabled',
    'Bouton':
        'Button',
    'Axe analogique':
        'Analog axis',
    'Recentrage du volant':
        'Wheel recenter',
    'Course totale':
        'Total range',
    'Couple maximum':
        'Maximum torque',
    'Force globale':
        'Overall force',
    'Inverser le sens du volant (position)':
        'Invert wheel direction (position)',
    'Inverser uniquement les forces du jeu':
        'Invert game forces only',
    'Ressort au repos (hors jeu)':
        'Idle spring (no game)',
    'Amortissement permanent':
        'Permanent damping',
    'Frottement permanent':
        'Permanent friction',
    'Inertie permanente':
        'Permanent inertia',
    'Raideur des butées':
        'End-stop stiffness',
    'Amortissement des butées':
        'End-stop damping',
    'Limite de variation du couple':
        'Torque slew limit',
    'pts/ms':
        'pts/ms',
    'Courbe exponentielle':
        'Exponential curve',
    'Échelle de la courbe':
        'Curve scale',
    'Gain général':
        'Master gain',
    'Ressort':
        'Spring',
    'Amortissement':
        'Damping',
    'Frottement':
        'Friction',
    'Inertie':
        'Inertia',
    'Force constante : coupure':
        'Constant force: cut-off',
    'Force constante : Q':
        'Constant force: Q',
    'Frottement : coupure':
        'Friction: cut-off',
    'Frottement : Q':
        'Friction: Q',
    'Amortissement : coupure':
        'Damper: cut-off',
    'Amortissement : Q':
        'Damper: Q',
    'Inertie : coupure':
        'Inertia: cut-off',
    'Inertie : Q':
        'Inertia: Q',
    'Poids (5 Hz)':
        'Weight (5 Hz)',
    'Châssis (12 Hz)':
        'Chassis (12 Hz)',
    'Route (25 Hz)':
        'Road (25 Hz)',
    'Type de moteur':
        'Motor type',
    'Paires de pôles':
        'Pole pairs',
    'Constante de couple Kt':
        'Torque constant Kt',
    'Courant maximum':
        'Maximum current',
    'Marge avant défaut de courant':
        'Margin before current fault',
    'Gamme de mesure du courant':
        'Current measurement range',
    'Bande passante de la boucle de courant':
        'Current loop bandwidth',
    'Courant de calibration':
        'Calibration current',
    'Tension max de calibration':
        'Max calibration voltage',
    'Résistance de phase mesurée':
        'Measured phase resistance',
    'Inductance de phase mesurée':
        'Measured phase inductance',
    'Moteur déjà calibré (ne pas refaire au démarrage)':
        "Motor already calibrated (don't redo at start-up)",
    'Type de codeur':
        'Encoder type',
    'Points par tour moteur (CPR)':
        'Counts per motor revolution (CPR)',
    "Utiliser l'index Z":
        'Use Z index',
    'Sens du codeur (trouvé à la calibration)':
        'Encoder direction (found by calibration)',
    'Calage codeur conservé (index ou absolu uniquement)':
        'Keep encoder alignment (index or absolute only)',
    'Bande passante du codeur (PLL)':
        'Encoder bandwidth (PLL)',
    'Tolérance de la calibration':
        'Calibration tolerance',
    'Mode de commande':
        'Control mode',
    "Mode d'entrée":
        'Input mode',
    'Vitesse maxi (anti-emballement)':
        'Max speed (anti-runaway)',
    'Tolérance de survitesse':
        'Overspeed tolerance',
    'Limiter la vitesse en mode couple':
        'Limit speed in torque mode',
    'Couper en cas de survitesse':
        'Cut off on overspeed',
    'Gain de vitesse (limitation)':
        'Velocity gain (limiting)',
    'Calibrer le moteur':
        'Calibrate the motor',
    "Chercher l'index Z":
        'Search the Z index',
    'Caler le codeur (le volant bouge ~1 tour)':
        'Align the encoder (the wheel moves ~1 turn)',
    'Passer en boucle fermée':
        'Enter closed loop',
    'Rapport du pont diviseur de tension':
        'Voltage divider ratio',
    'Coupure tension haute':
        'High-voltage cut-off',
    'Coupure tension basse':
        'Low-voltage cut-off',
    "Courant maxi tiré sur l'alimentation":
        'Max current drawn from the supply',
    "Courant maxi renvoyé vers l'alimentation":
        'Max current sent back to the supply',
    'Courant de récupération autorisé':
        'Allowed regen current',
    'Résistance de freinage branchée':
        'Brake resistor connected',
    'Valeur de la résistance':
        'Resistor value',
    'Protection thermique des transistors':
        'Transistor thermal protection',
    'Début de réduction du courant':
        'Start of current derating',
    'Coupure':
        'Cut-off',
    'Filtre passe-bas sur les axes GPIO':
        'Low-pass filter on GPIO axes',
    'Coupure du filtre':
        'Filter cut-off',
    'Calibration automatique mini/maxi':
        'Automatic min/max calibration',
    'État demandé impossible maintenant (ex. boucle fermée avant calibration).':
        'Requested state impossible now (e.g. closed loop before calibration).',
    "Défaut moteur : voir l'erreur moteur.":
        'Motor fault: see the motor error.',
    'Estimateur sans capteur en défaut.':
        'Sensorless estimator fault.',
    "Défaut codeur : voir l'erreur codeur.":
        'Encoder fault: see the encoder error.',
    "Défaut du contrôleur : voir l'erreur contrôleur.":
        'Controller fault: see the controller error.',
    'Chien de garde expiré.':
        'Watchdog expired.',
    'Fin de course mini appuyé.':
        'Min end switch pressed.',
    'Fin de course maxi appuyé.':
        'Max end switch pressed.',
    "Arrêt d'urgence demandé (CAN).":
        'Emergency stop requested (CAN).',
    "Prise d'origine sans fin de course.":
        'Homing without end switch.',
    "Surchauffe : voir l'erreur moteur.":
        'Overheating: see the motor error.',
    'Position inconnue.':
        'Unknown position.',
    'Résistance de phase hors plage : fil moteur mal serré, ou calibration_current × R > resistance_calib_max_voltage.':
        'Phase resistance out of range: loose motor wire, or calibration_current × R > resistance_calib_max_voltage.',
    'Inductance de phase hors plage : vérifie les fils moteur.':
        'Phase inductance out of range: check the motor wires.',
    'Le driver de grilles (DRV8301) a signalé un défaut.':
        'The gate driver (DRV8301) reported a fault.',
    'Boucle de commande en retard.':
        'Control loop late.',
    'Tension du bus insuffisante pour le courant demandé (resistance_calib_max_voltage ≤ moitié de la tension bus).':
        'Bus voltage too low for the requested current (resistance_calib_max_voltage ≤ half the bus voltage).',
    'Mesure de courant saturée : current_lim > requested_current_range.':
        'Current measurement saturated: current_lim > requested_current_range.',
    'Courant au-delà de current_lim + current_lim_margin.':
        'Current above current_lim + current_lim_margin.',
    'Calcul de modulation invalide.':
        'Invalid modulation computation.',
    'Thermistance moteur trop chaude.':
        'Motor thermistor too hot.',
    'Transistors de puissance trop chauds.':
        'Power transistors too hot.',
    'Mise à jour du timer manquée.':
        'Timer update missed.',
    'Mesure de courant indisponible.':
        'Current measurement unavailable.',
    'Le contrôleur de courant (FOC) a échoué.':
        'The current controller (FOC) failed.',
    'Courant bus hors des limites I_bus_hard_min/max.':
        'Bus current outside I_bus_hard_min/max.',
    'Résistance de freinage désarmée : efface les erreurs ou redémarre la carte.':
        'Brake resistor disarmed: clear the errors or reboot the board.',
    'Erreur système (tension, courant bus…) : détail dans Réglages › Alimentation.':
        'System error (voltage, bus current…): details in Settings › Power supply.',
    'Boucle principale désynchronisée.':
        'Main loop out of sync.',
    "Position du rotor inconnue : le calage du codeur n'a pas été fait depuis l'allumage.":
        'Rotor position unknown: the encoder alignment has not been done since power-up.',
    'Vitesse électrique inconnue.':
        'Electrical speed unknown.',
    'Consigne de couple invalide.':
        'Invalid torque setpoint.',
    'Consigne de courant invalide.':
        'Invalid current setpoint.',
    'Mesure de courant invalide.':
        'Invalid current measurement.',
    'Tension bus inconnue.':
        'Bus voltage unknown.',
    'Gains du codeur instables (bandwidth).':
        'Unstable encoder gains (bandwidth).',
    "CPR et paires de pôles incohérents : le moteur n'a pas tourné de la distance attendue.":
        'CPR and pole pairs inconsistent: the motor did not turn the expected distance.',
    'Le codeur ne répond pas : A/B, 5 V, GND, résistances de tirage.':
        'The encoder does not respond: A/B, 5 V, GND, pull-up resistors.',
    'Mode de codeur non géré.':
        'Encoder mode not supported.',
    'État Hall impossible.':
        'Impossible Hall state.',
    'Index Z pas encore trouvé.':
        'Z index not found yet.',
    'Codeur SPI : délai dépassé.':
        'SPI encoder: timeout.',
    'Codeur SPI : échec de communication.':
        'SPI encoder: communication failure.',
    'Codeur SPI pas prêt.':
        'SPI encoder not ready.',
    'Capteurs Hall pas encore calibrés.':
        'Hall sensors not calibrated yet.',
    'Survitesse : vitesse > vel_limit × vel_limit_tolerance.':
        'Overspeed: speed > vel_limit × vel_limit_tolerance.',
    "Mode d'entrée invalide.":
        'Invalid input mode.',
    'Gains instables.':
        'Unstable gains.',
    'Axe miroir invalide.':
        'Invalid mirror axis.',
    'Codeur de charge invalide.':
        'Invalid load encoder.',
    'Estimation de position/vitesse invalide.':
        'Invalid position/velocity estimate.',
    'Plage circulaire invalide.':
        'Invalid circular range.',
    'Emballement détecté (puissance mécanique/électrique incohérente).':
        'Spin-out detected (mechanical/electrical power mismatch).',
    'Itération de commande manquée.':
        'Control iteration missed.',
    'Tension bus sous le seuil bas (batterie vide ou seuil trop haut).':
        'Bus voltage below the low threshold (empty battery or threshold too high).',
    'Tension bus au-dessus du seuil haut (freinage, batterie pleine).':
        'Bus voltage above the high threshold (braking, full battery).',
    "Trop de courant renvoyé vers l'alimentation.":
        'Too much current sent back to the supply.',
    "Trop de courant tiré sur l'alimentation.":
        'Too much current drawn from the supply.',
    'Temps mort de la résistance de freinage violé.':
        'Brake resistor dead-time violated.',
    'Rapport cyclique de freinage invalide.':
        'Invalid brake duty cycle.',
    'Valeur de résistance de freinage invalide.':
        'Invalid brake resistance value.',
    'Angle total de butée à butée (900° = 450° de chaque côté). Les jeux le règlent souvent eux-mêmes.':
        'Total lock-to-lock angle (900° = 450° each side). Games often set it themselves.',
    'Couple qui correspond à 100 % de force du jeu. Plafonné à 40 N·m par le firmware. Commence bas (3 N·m) et monte par paliers.':
        'Torque matching 100 % game force. Capped at 40 N·m by the firmware. Start low (3 N·m) and go up in steps.',
    'Atténuateur général des effets du jeu. Baisse-le si le couple sature (clipping).':
        'Overall attenuator of the game effects. Lower it if the torque saturates (clipping).',
    'Inverse la position envoyée au jeu ET le sens des forces du jeu.':
        'Inverts the position sent to the game AND the direction of the game forces.',
    'Pour les jeux ou outils qui envoient la force avec le mauvais signe.':
        'For games or tools that send the force with the wrong sign.',
    "Ressort de centrage quand aucun jeu n'envoie de force.":
        'Centering spring when no game sends force.',
    'Freinage proportionnel à la vitesse, toujours actif. Stabilise un volant qui oscille.':
        'Speed-proportional braking, always active. Stabilises an oscillating wheel.',
    'Force du ressort qui bloque le volant en bout de course.':
        'Strength of the spring that holds the wheel at the end of its range.',
    'Évite le rebond contre la butée.':
        'Prevents bouncing off the end stop.',
    'Variation maximale du couple par milliseconde, en points internes (32767 = couple maximum). 0 = pas de limite.':
        'Maximum torque change per millisecond, in internal points (32767 = maximum torque). 0 = no limit.',
    '0 = linéaire. Positif : plus de détail sur les petites forces.':
        '0 = linear. Positive: more detail on small forces.',
    '255 = 100 %. Le jeu peut aussi le modifier.':
        '255 = 100 %. The game can also change it.',
    'Le filtre le plus important : plus bas = plus doux, plus haut = plus de détails (bordures).':
        'The most important filter: lower = smoother, higher = more detail (kerbs).',
    'Le couple constant en virage ne change jamais. Monter « Poids » réduit le reste par contraste.':
        'Constant cornering torque never changes. Raising “Weight” reduces the rest by contrast.',
    'Monter « Route » fait ressortir bordures et texture de la piste.':
        'Raising “Road” brings out kerbs and track texture.',
    "Nombre d'aimants ÷ 2. Moteur de hoverboard : souvent 15. Une valeur fausse fait échouer le calage.":
        'Number of magnets ÷ 2. Hoverboard motor: often 15. A wrong value makes the alignment fail.',
    'Kt ≈ 8,27 / KV. Sert à convertir le couple demandé en courant.':
        'Kt ≈ 8.27 / KV. Used to convert the requested torque into current.',
    'Plafond réel du couple : couple maxi ≈ Kt × courant maxi. Commence à 10 A.':
        'Real torque ceiling: max torque ≈ Kt × max current. Start at 10 A.',
    'Doit rester au-dessus du courant maximum. Pris en compte au redémarrage.':
        'Must stay above the maximum current. Applied after reboot.',
    'Plus haut = réponse plus nette mais plus de bruit moteur. 1000 par défaut, souvent 200–1000 sur un moteur de hoverboard.':
        'Higher = crisper response but more motor noise. 1000 by default, often 200–1000 on a hoverboard motor.',
    'Doit dépasser courant de calibration × résistance, et rester sous la moitié de la tension bus.':
        'Must exceed calibration current × resistance, and stay below half the bus voltage.',
    'Incrémental : PPR × 4 × rapport de transmission. Ex. codeur 2500 PPR, courroie 72/16 : 2500 × 4 × 72/16 = 45000.':
        'Incremental: PPR × 4 × gear ratio. E.g. 2500 PPR encoder, 72/16 belt: 2500 × 4 × 72/16 = 45000.',
    'À laisser décoché si le codeur est entraîné par courroie avec un rapport non entier.':
        'Leave unticked if the encoder is belt-driven with a non-integer ratio.',
    'Ne coche PAS avec un codeur incrémental sans index : le calage serait faux au prochain allumage.':
        'Do NOT tick with an incremental encoder without index: the alignment would be wrong at the next power-up.',
    "Lissage de la vitesse estimée, utilisée par l'amortissement, le frottement et l'inertie.":
        'Smoothing of the estimated speed, used by damping, friction and inertia.',
    'Le volant fonctionne en commande de couple.':
        'The wheel works in torque control.',
    'Au-delà, le couple est réduit ; × tolérance, la carte coupe avec une erreur de survitesse.':
        'Above it, torque is reduced; × tolerance, the board cuts off with an overspeed error.',
    'Utilisé seulement pour freiner au-delà de la vitesse maxi.':
        'Only used to brake above the max speed.',
    'Indispensable avec un codeur incrémental sans index.':
        'Required with an incremental encoder without index.',
    '19 sur ODrive v3.6-56V et MKS, 11 sur la version 24 V. Toutes les protections en dépendent.':
        '19 on ODrive v3.6-56V and MKS, 11 on the 24 V version. Every protection depends on it.',
    'Ex. batterie 10S (42 V pleine) : 46 V.':
        'E.g. 10S battery (42 V full): 46 V.',
    'Ex. batterie 10S : 32 V (3,2 V par cellule).':
        'E.g. 10S battery: 32 V (3.2 V per cell).',
    '0 = tout le freinage part dans la résistance.':
        '0 = all braking goes into the resistor.',
    'Valeur exacte gravée sur la résistance (ex. 2 Ω).':
        'Exact value printed on the resistor (e.g. 2 Ω).',
    'Mode':
        'Mode',
    "Bit d'erreur inconnu.":
        'Unknown error bit.',
    'N° bouton / axe':
        'Button / axis no.',
    'Inverser':
        'Invert',
    'Mini':
        'Min',
    'Maxi':
        'Max',
    'Retour de force non ouvert':
        'Force feedback not opened',
    'SDL2 indisponible':
        'SDL2 unavailable',
    'Aucun périphérique à retour de force DirectInput trouvé (':
        'No DirectInput force-feedback device found (',
    'efface toute la configuration ODrive':
        'erases the whole ODrive configuration',
    'passe la carte en mode DFU':
        'puts the board in DFU mode',
    'efface la mémoire des réglages volant':
        'erases the wheel settings memory',
    'Tension du bus':
        'Bus voltage',
    'Courant du bus':
        'Bus current',
    'Erreur système (tension, courant…)':
        'System error (voltage, current…)',
    "État de l'axe (1 repos, 8 boucle fermée)":
        'Axis state (1 idle, 8 closed loop)',
    "Erreur de l'axe":
        'Axis error',
    'Erreur moteur':
        'Motor error',
    'Erreur codeur':
        'Encoder error',
    'Erreur contrôleur':
        'Controller error',
    'Compteur du codeur':
        'Encoder counter',
    'Codeur calé ?':
        'Encoder aligned?',
    'Moteur au repos (libre)':
        'Motor idle (free)',
    'Calibration moteur (le moteur siffle)':
        'Motor calibration (the motor beeps)',
    'Calage du codeur (le moteur tourne ~1 tour)':
        'Encoder alignment (the motor turns ~1 turn)',
    'Boucle fermée (moteur actif)':
        'Closed loop (motor active)',
    'Mémoriser la config ODrive et redémarrer (moteur au repos)':
        'Store the ODrive config and reboot (motor idle)',
    'Mémoriser les réglages volant/effets':
        'Store the wheel/effect settings',
    'Résumé FFB : actif, position, vitesse, couple, effets':
        'FFB summary: active, position, speed, torque, effects',
    'Prendre la position actuelle comme centre':
        'Use the current position as center',
    'Résultat de la dernière mémorisation':
        'Result of the last store',
    'Diagnostic de la mémoire des réglages volant':
        'Wheel settings memory diagnostics',
    'Pics de courant et de tension depuis le démarrage':
        'Current and voltage peaks since start-up',
    'Température des transistors':
        'Transistor temperature',
    'Temps depuis le démarrage':
        'Time since start-up',
    'Liste des commandes OpenFFBoard':
        'OpenFFBoard command list',
    'Console série':
        'Serial console',
    'Commande (Entrée pour envoyer, ↑/↓ historique)…':
        'Command (Enter to send, ↑/↓ history)…',
    'Envoyer':
        'Send',
    'Effacer':
        'Clear',
    'Commandes utiles':
        'Useful commands',
    'Envoie des commandes à la carte. ODrive : « r chemin » lit, « w chemin valeur » écrit (muet si accepté). OpenFFBoard : « classe.cmd? » lit, « = » écrit, « ! » exécute. Les modifications ne sont pas mémorisées sans « ss » ou « sys.save! ».':
        'Sends commands to the board. ODrive: “r path” reads, “w path value” writes (silent if accepted). OpenFFBoard: “class.cmd?” reads, “=” writes, “!” executes. Changes are not stored without “ss” or “sys.save!”.',
    'Double-clic pour copier dans la ligne de commande.':
        'Double-click to copy into the command line.',
    'Commande sensible':
        'Sensitive command',
    'Port série {p} ouvert.':
        'Serial port {p} open.',
    '« {c} » {d}. Continuer ?':
        '“{c}” {d}. Continue?',
    'Port série fermé ({w}).':
        'Serial port closed ({w}).',
    'Compteurs ODrive (port série)':
        'ODrive counters (serial port)',
    'Lecture continue (4 fois par seconde)':
        'Continuous reading (4 times per second)',
    'Configuration':
        'Configuration',
    'Relire la configuration':
        'Read configuration again',
    'Signal Z (index)':
        'Z signal (index)',
    'Impulsions Z acceptées':
        'Accepted Z pulses',
    'Parasites Z rejetés':
        'Rejected Z glitches',
    'Remettre les compteurs Z à zéro':
        'Reset Z counters',
    'Qualité du signal (position remontée à 1 kHz)':
        'Signal quality (position reported at 1 kHz)',
    'Échantillons analysés':
        'Samples analysed',
    'Sauts anormaux':
        'Abnormal jumps',
    'Plus gros écart position/vitesse':
        'Largest position/speed mismatch',
    'Angle':
        'Angle',
    'Remettre à zéro':
        'Reset',
    'Compteur total':
        'Total count',
    'pts':
        'cts',
    'Position dans le tour':
        'Position in revolution',
    'Position estimée':
        'Estimated position',
    'tours':
        'turns',
    'Vitesse estimée':
        'Estimated speed',
    'tr/s':
        'rev/s',
    'Codeur calé (prêt)':
        'Encoder aligned (ready)',
    'Index Z trouvé':
        'Z index found',
    'Décalage de phase (calage)':
        'Phase offset (alignment)',
    'Type':
        'Type',
    'Sens':
        'Direction',
    'Index utilisé':
        'Index used',
    'Calage conservé':
        'Alignment kept',
    'Bande passante':
        'Bandwidth',
    'Points par pas électrique':
        'Counts per electrical step',
    "Le firmware compte les impulsions Z reçues, même si l'index n'est pas utilisé. Avec une courroie 72/16, le Z doit rester débranché : le compteur doit rester à 0.":
        'The firmware counts received Z pulses, even when the index is not used. With a 72/16 belt the Z must stay unplugged: the counter must stay at 0.',
    'Chaque milliseconde, la carte envoie la position et la vitesse. Un saut de position qui ne correspond pas à la vitesse mesurée trahit des impulsions perdues ou parasites (câble codeur trop long, masse, pas de résistances de tirage). Tourne le volant à la main, moteur au repos.':
        'Every millisecond the board sends position and speed. A position jump that does not match the measured speed reveals lost or spurious pulses (encoder cable too long, ground, no pull-up resistors). Turn the wheel by hand, motor idle.',
    'Seuil de saut':
        'Jump threshold',
    'Moins de 50 points par pas électrique : résolution trop faible pour un couple régulier.':
        'Fewer than 50 counts per electrical step: resolution too low for smooth torque.',
    '⚠ Calage conservé sans index : dangereux avec un codeur incrémental.':
        '⚠ Alignment kept without index: dangerous with an incremental encoder.',
    'oui':
        'yes',
    'non':
        'no',
    '0 (pas encore calibré)':
        '0 (not calibrated yet)',
    'attendu ±{e}°':
        'expected ±{e}°',
    'Sinus':
        'Sine',
    'Dent de scie ↑':
        'Sawtooth ↑',
    'Dent de scie ↓':
        'Sawtooth ↓',
    'Ressort (centrage)':
        'Spring (centering)',
    "Le volant revient au centre, d'autant plus fort qu'on s'en éloigne. « Centre » décale le point de repos.":
        'The wheel returns to center, harder the further you move it. "Center" shifts the rest point.',
    'Force constante':
        'Constant force',
    "Pousse en continu d'un côté : négatif = vers la gauche, positif = vers la droite. Vérifie que le sens correspond à celui du jeu.":
        'Pushes continuously to one side: negative = left, positive = right. Check the direction matches the game.',
    'Vibration (périodique)':
        'Vibration (periodic)',
    'Vibration régulière. Période courte = vibration rapide (bruit de route), longue = balancement.':
        'Regular vibration. Short period = fast buzz (road noise), long period = slow sway.',
    'Résistance constante quand on tourne, quelle que soit la vitesse.':
        'Constant resistance when turning, whatever the speed.',
    "Résistance proportionnelle à la vitesse : lentement c'est léger, vite c'est dur.":
        'Resistance proportional to speed: light when slow, heavy when fast.',
    "Le volant paraît plus lourd au démarrage et à l'arrêt.":
        'The wheel feels heavier when starting and stopping.',
    'Rampe':
        'Ramp',
    "La force passe progressivement de « Départ » à « Arrivée » pendant la durée, puis s'arrête.":
        'The force ramps from "Start" to "End" over the duration, then stops.',
    'Force max des essais':
        'Max test force',
    'Coupure si survitesse >':
        'Cut off if speed >',
    'Pendant un essai, le moteur est mis au repos (STOP) si la vitesse mesurée par la carte dépasse le seuil, ou si le volant sort de la course réglée.':
        'During a test the motor is set to idle (STOP) if the speed measured by the board exceeds the threshold, or if the wheel leaves its set range.',
    '1. Source':
        '1. Source',
    'Fermé':
        'Closed',
    'Ouvrir':
        'Open',
    'Gain DirectInput':
        'DirectInput gain',
    'Tester si la carte répond':
        'Test whether the board responds',
    'Envoie une force constante à gauche puis à droite (limitée par la force max) et vérifie que le couple mesuré par la carte suit. Volant lâché, moteur actif.':
        'Sends a constant force to the left then to the right (limited by the max force) and checks that the torque measured by the board follows. Wheel released, motor active.',
    '2. Effet':
        '2. Effect',
    '3. Réglages':
        '3. Settings',
    'Ce que fait le volant':
        'What the wheel does',
    'Couple mesuré':
        'Measured torque',
    'Courant moteur':
        'Motor current',
    'Du couple maxi':
        'Of max torque',
    'Commande envoyée':
        'Command sent',
    'Retour de force ouvert':
        'Force feedback open',
    'Test en cours… volant lâché.':
        'Testing… hands off.',
    'Raideur':
        'Stiffness',
    'Centre':
        'Center',
    'Saturation':
        'Saturation',
    'Zone morte':
        'Deadband',
    'Niveau  (← gauche · droite →)':
        'Level  (← left · right →)',
    'Amplitude':
        'Amplitude',
    'Période':
        'Period',
    'Décalage':
        'Offset',
    'Coefficient':
        'Coefficient',
    'Départ':
        'Start',
    'Arrivée':
        'End',
    'Durée':
        'Duration',
    'DirectInput — le même chemin que les jeux.':
        'DirectInput — the same path as games.',
    "Barre bleue = couple de sortie de la carte, en % du couple maximum du volant. Commence volant lâché : un ressort doit ramener le volant au centre, jamais l'emmener tout seul.":
        "Blue bar = board output torque, in % of the wheel's maximum torque. Start with the wheel released: a spring must bring the wheel back to center, never drive it away on its own.",
    "■  ARRÊTER L'EFFET":
        '■  STOP EFFECT',
    "▶  LANCER L'EFFET":
        '▶  START EFFECT',
    'STOP enclenché : réarme-le en haut avant de lancer un effet.':
        'STOP latched: release it at the top before starting an effect.',
    'Carte non connectée ou STOP enclenché.':
        'Board not connected or STOP latched.',
    'Le moteur doit être actif (boucle fermée) : bouton « Activer le moteur » en haut, ou onglet Mise en route.':
        'The motor must be active (closed loop): “Enable motor” button at the top, or the Setup tab.',
    'Test interrompu par la sécurité.':
        'Test interrupted by the safety cut-off.',
    'même sens':
        'same direction',
    'sens inversé':
        'inverted direction',
    'actif':
        'active',
    'Forme':
        'Shape',
    '✔ La carte applique la force : {n} / {p} N·m pour ∓{l} % demandés ({s}).':
        '✔ The board applies the force: {n} / {p} N·m for ∓{l} % requested ({s}).',
    'au repos':
        'idle',
    "Gain à 0 : l'effet ne fera rien (Réglages › Effets du jeu).":
        'Gain at 0: the effect will do nothing (Settings › Game effects).',
    '100 % = {m} N·m (couple maximum du volant).':
        '100 % = {m} N·m (wheel maximum torque).',
    "Le moteur n'est pas actif (état : {s}) : l'effet ne fera rien tant qu'il n'est pas en boucle fermée.":
        'The motor is not active (state: {s}): the effect will do nothing until it is in closed loop.',
    'Erreur {k} : {e}':
        '{k} error: {e}',
    'Retour de force ouvert. Non annoncés par le pilote : {l}':
        'Force feedback open. Not advertised by the driver: {l}',
    '✖ Aucune réaction du couple (repos {b}, gauche {n}, droite {p} N·m). Vérifie : moteur actif, force globale, couple maximum, gain DirectInput.':
        '✖ No torque response (rest {b}, left {n}, right {p} N·m). Check: motor active, overall force, maximum torque, DirectInput gain.',
    'Gain de cet effet dans la carte : {g}/255 ({p} %).':
        'Board gain for this effect: {g}/255 ({p} %).',
    'DirectInput indisponible : {e}':
        'DirectInput unavailable: {e}',
    'Attendu environ ±{e} N·m (hors gains des effets et filtres).':
        'About ±{e} N·m expected (excluding effect gains and filters).',
    'Actualiser':
        'Refresh',
    'RAZ pas max':
        'Reset max step',
    'Journal CSV…':
        'CSV log…',
    'Axes  —  valeur brute (-32768…32767), pas entre deux lectures, pas max':
        'Axes  —  raw value (-32768…32767), step between reads, max step',
    'Boutons':
        'Buttons',
    'Chapeaux (POV)':
        'Hats (POV)',
    'Périphérique :':
        'Device:',
    'Aucun joystick détecté':
        'No joystick detected',
    'Valeur':
        'Value',
    'Pas':
        'Step',
    'Pas max':
        'Max step',
    '■ Arrêter le journal':
        '■ Stop log',
    'Ouverture impossible : {e}':
        'Cannot open: {e}',
    "SDL2 indisponible : {e}. Lance l'appli avec SimForge Studio.bat pour installer les dépendances.":
        'SDL2 unavailable: {e}. Start the app with SimForge Studio.bat to install dependencies.',
    'Axe {n}':
        'Axis {n}',
    'Volant':
        'Wheel',
    'Couple':
        'Torque',
    'Alimentation':
        'Power supply',
    'Carte':
        'Board',
    'Courbes (10 s)':
        'Plots (10 s)',
    'Courants':
        'Currents',
    'Tension bus':
        'Bus voltage',
    'Enregistrer en CSV…':
        'Record CSV…',
    'Figer':
        'Freeze',
    'Extrêmes depuis la remise à zéro':
        'Extremes since reset',
    'Courant tiré (− = renvoyé)':
        'Current drawn (− = sent back)',
    'Courant résistance de freinage':
        'Brake resistor current',
    'Puissance dans la résistance':
        'Power in the resistor',
    "Puissance tirée sur l'alimentation":
        'Power drawn from the supply',
    'Température transistors':
        'Transistor temperature',
    'Température moteur':
        'Motor temperature',
    "État de l'axe":
        'Axis state',
    'Rapports HID reçus':
        'HID reports received',
    'Boutons GPIO':
        'GPIO buttons',
    'La tension maxi montre ce que le freinage fait monter : garde-la sous le seuil de coupure haute.':
        'Max voltage shows how high braking pushes it: keep it below the high-voltage cut-off.',
    'Fichier CSV':
        'CSV file',
    "■ Arrêter l'enregistrement":
        '■ Stop recording',
    'Aucune erreur.':
        'No error.',
    'courant résistance':
        'resistor current',
    'Tension mini (creux)':
        'Min voltage (sag)',
    'Tension maxi (freinage)':
        'Max voltage (braking)',
    'Courant tiré maxi':
        'Max current drawn',
    'Courant renvoyé maxi':
        'Max current sent back',
    'Courant moteur maxi':
        'Max motor current',
    'Couple maxi':
        'Max torque',
    'Vitesse maxi':
        'Max speed',
    'Courant résistance maxi':
        'Max resistor current',
    'volant':
        'wheel',
    'courant tiré':
        'current drawn',
    'courant moteur':
        'motor current',
    'Courants :':
        'Currents:',
    'Couple en % du maxi':
        'Torque in % of max',
    'Barre de couple':
        'Torque bar',
    'Couple crête (3 s)':
        'Peak torque (3 s)',
    'Saturation du couple (5 s)':
        'Torque clipping (5 s)',
    'Tension mini (10 s)':
        'Min voltage (10 s)',
    'Courant tiré':
        'Current drawn',
    'Puissance tirée':
        'Power drawn',
    'Puissance résistance (moy. 5 s)':
        'Resistor power (5 s avg.)',
    'Course utilisée':
        'Range used',
    'Rapports / s':
        'Reports / s',
    'État (connexion / moteur / erreurs)':
        'Status (connection / motor / errors)',
    'Informations affichées':
        'Displayed information',
    'Apparence':
        'Appearance',
    'Opacité du fond':
        'Background opacity',
    'Taille du texte':
        'Text size',
    'Disposition horizontale':
        'Horizontal layout',
    'Laisser passer les clics (overlay non déplaçable)':
        "Click-through (overlay can't be moved)",
    'Overlay':
        'Overlay',
    "Afficher l'overlay":
        'Show overlay',
    'Replacer en haut à gauche':
        'Move to top left',
    'Aperçu':
        'Preview',
    'Saturation = part du temps où le couple atteint le couple maximum du volant (ou le courant maximum du moteur). Au-delà de quelques %, baisse la force dans le jeu ou monte le couple maximum.':
        "Saturation = share of time the torque reaches the wheel's maximum torque (or the motor's maximum current). Above a few %, lower the force in the game or raise the maximum torque.",
    'Affichage':
        'Display',
    'Valeurs':
        'Values',
    'Courbes':
        'Curves',
    'Durée des courbes':
        'Curve length',
    "Fenêtre toujours au premier plan, déplaçable à la souris. Elle s'affiche par-dessus les jeux en mode fenêtré ou plein écran fenêtré (borderless), pas en plein écran exclusif.":
        'Always-on-top window, drag it with the mouse. It shows over games in windowed or borderless fullscreen mode, not in exclusive fullscreen.',
    "Masquer l'overlay":
        'Hide overlay',
    'en attente de la carte…':
        'waiting for the board…',
    'ERREUR':
        'ERROR',
    'Ces effets agissent toujours, jeu lancé ou non (0 = désactivé, 255 = maximum).':
        'These effects always act, game running or not (0 = off, 255 = maximum).',
    'Proportion de chaque effet envoyé par le jeu (255 = 100 %).':
        'Share of each effect sent by the game (255 = 100 %).',
    'Filtres appliqués aux effets du jeu. Q : 0,70 = réponse plate.':
        'Filters applied to the game effects. Q: 0.70 = flat response.',
    'Ce que fait la carte à chaque allumage. Avec un codeur incrémental sans index : moteur déjà calibré, calage du codeur, puis boucle fermée.':
        'What the board does at each power-up. With an incremental encoder without index: motor already calibrated, encoder alignment, then closed loop.',
    'Toutes ces protections dépendent du pont diviseur : vérifie une fois la tension affichée au multimètre.':
        'Every protection depends on the voltage divider: check the displayed voltage once with a multimeter.',
    'Résistance et inductance sont mesurées par la calibration moteur (onglet Mise en route).':
        'Resistance and inductance are measured by the motor calibration (Setup tab).',
    'Effets du jeu':
        'Game effects',
    'Moteur et codeur':
        'Motor and encoder',
    'Valeur lue dans la carte.':
        'Value read from the board.',
    'Modifié, pas encore envoyé.':
        'Changed, not sent yet.',
    'Envoyé, en attente de relecture.':
        'Sent, waiting for read-back.',
    'Appliqué dans la carte, pas encore mémorisé (« Enregistrer »).':
        'Applied on the board, not stored yet (“Save”).',
    'Appliquer en direct les réglages du volant et des effets':
        'Apply wheel and effect settings live',
    'Réglages avancés':
        'Advanced settings',
    "Affiche aussi les réglages rarement utiles (filtres détaillés, égaliseur, courbe, boucles de régulation, températures, entrées GPIO). Leurs valeurs d'usine conviennent.":
        'Also shows rarely needed settings (detailed filters, equalizer, curve, control loops, temperatures, GPIO inputs). Their factory values are fine.',
    "Les réglages volant/effets sont envoyés dès qu'on les change (comme l'outil web). Les réglages ODrive (moteur, codeur, alimentation) attendent « Appliquer ».":
        'Wheel/effect settings are sent as soon as they change (like the web tool). ODrive settings (motor, encoder, power) wait for “Apply”.',
    'Relire la carte':
        'Read board',
    'Annuler les modifications':
        'Undo changes',
    'Appliquer':
        'Apply',
    'Envoie les modifications en attente dans la carte (sans les mémoriser).':
        'Sends the pending changes to the board (without storing them).',
    'Entrées GPIO':
        'GPIO inputs',
    'Carte et profils':
        'Board and profiles',
    'Entrées GPIO du connecteur':
        'Connector GPIO inputs',
    'Lire les entrées maintenant':
        'Read inputs now',
    'Traitement des axes analogiques':
        'Analog axis processing',
    'Contrôles de cohérence':
        'Consistency checks',
    'Réglages pas encore lus.':
        'Settings not read yet.',
    'Profils':
        'Profiles',
    'Exporter la configuration…':
        'Export configuration…',
    'Importer un profil…':
        'Import a profile…',
    'Zone dangereuse':
        'Danger zone',
    'Effacer la configuration ODrive…':
        'Erase ODrive configuration…',
    'Exporter la configuration':
        'Export configuration',
    'Importer un profil':
        'Import a profile',
    "Codeur incrémental sans index marqué « calage conservé » : au prochain allumage la carte réutiliserait un calage faux (risque d'emballement). Décoche-le.":
        'Incremental encoder without index marked “alignment kept”: at the next power-up the board would reuse a wrong alignment (runaway risk). Untick it.',
    "Boucle fermée au démarrage sans calage du codeur : la carte s'arrêtera en erreur UNKNOWN_PHASE_ESTIMATE à chaque allumage. Active « Caler le codeur ».":
        'Closed loop at start-up without encoder alignment: the board will stop with a UNKNOWN_PHASE_ESTIMATE error at every power-up. Enable “Align the encoder”.',
    'Calage du codeur au démarrage sans moteur calibré : il échouera. Marque le moteur comme calibré après sa calibration.':
        'Encoder alignment at start-up without a calibrated motor: it will fail. Mark the motor as calibrated after its calibration.',
    "Le mode de commande n'est pas « Couple » : le volant ne fonctionnera pas normalement.":
        'Control mode is not “Torque”: the wheel will not work normally.',
    "Coupure de survitesse désactivée : plus de protection en cas d'emballement.":
        'Overspeed cut-off disabled: no more protection in case of a runaway.',
    'Coupure tension haute au-delà de 56 V : au-dessus de la tension maxi de la carte.':
        "High-voltage cut-off above 56 V: above the board's maximum voltage.",
    "Résistance de freinage désactivée : l'énergie de freinage repart dans l'alimentation (surtension possible, dangereux pour une batterie pleine).":
        'Brake resistor disabled: braking energy goes back into the supply (possible overvoltage, dangerous for a full battery).',
    "Moteur marqué calibré alors qu'aucune résistance de phase n'est enregistrée.":
        'Motor marked calibrated although no phase resistance is stored.',
    "Chaque GPIO peut devenir un bouton (contact vers GND), un axe analogique (0–3,3 V, GPIO 1 à 4 seulement) ou un bouton de recentrage. GPIO 1 et 2 servent aussi à l'UART A de l'ODrive : désactive-le (config.enable_uart_a) avant de t'en servir. Ne branche jamais plus de 3,3 V.":
        'Each GPIO can become a button (contact to GND), an analog axis (0–3.3 V, GPIO 1 to 4 only) or a recenter button. GPIO 1 and 2 are also used by the ODrive UART A: disable it (config.enable_uart_a) before using them. Never apply more than 3.3 V.',
    'GPIO':
        'GPIO',
    'Lecture brute':
        'Raw reading',
    'Matériel':
        'Hardware',
    'Base ODrive':
        'ODrive base',
    'N° de série':
        'Serial no.',
    'Identifiant STM32':
        'STM32 ID',
    'Décalage du centre':
        'Center offset',
    'Port série':
        'Serial port',
    'Vérifications faites sur les valeurs de la carte (et les modifications en attente).':
        'Checks made on the board values (and pending changes).',
    "Fichier JSON au même format que l'export de l'outil web Odrive-Wheel : les deux sont interchangeables. L'import ne fait que préparer les modifications : tu les vois en orange avant de cliquer « Appliquer ».":
        'JSON file in the same format as the Odrive-Wheel web tool export: both are interchangeable. Import only prepares the changes: you see them in orange before clicking “Apply”.',
    "Effacer la configuration ODrive remet tous les réglages moteur, codeur et alimentation d'usine, puis redémarre. Exporte d'abord ta configuration.":
        'Erasing the ODrive configuration resets every motor, encoder and power setting to factory values, then reboots. Export your configuration first.',
    "La carte n'est pas connectée.":
        'The board is not connected.',
    'Exporter':
        'Export',
    'Rien à exporter : réglages pas encore lus.':
        'Nothing to export: settings not read yet.',
    '{f} : {c} modification(s) préparée(s), {s} déjà identique(s).':
        '{f}: {c} change(s) prepared, {s} already identical.',
    'Effacer la configuration ODrive':
        'Erase ODrive configuration',
    "Tous les réglages moteur, codeur et alimentation vont être remis d'usine et la carte va redémarrer. Les réglages du volant et des effets ne sont pas touchés.\n\nContinuer ?":
        'Every motor, encoder and power setting will be reset to factory values and the board will reboot. Wheel and effect settings are not touched.\n\nContinue?',
    'Refusé par la carte : {m}':
        'Refused by the board: {m}',
    'Tension mesurée':
        'Measured voltage',
    'Courant dans la résistance':
        'Current in the resistor',
    'La carte répond 0.0.0 : Odrive-Wheel ne renseigne pas la version ODrive (fichier figé dans ses sources). Sa base est la 0.5.6.':
        'The board answers 0.0.0: Odrive-Wheel does not fill in the ODrive version (file frozen in its sources). Its base is 0.5.6.',
    'Réponse limitée à 9 caractères par le firmware : n° tronqué.':
        'Answer limited to 9 characters by the firmware: number truncated.',
    'Aucune erreur système.':
        'No system error.',
    'Moteur actif':
        'Motor active',
    'Exporté : {f} ({n} réglages).':
        'Exported: {f} ({n} settings).',
    'format inattendu':
        'unexpected format',
    'Importer':
        'Import',
    'Vérifie les valeurs en orange, puis « Appliquer » et « Enregistrer ».':
        'Check the values in orange, then “Apply” and “Save”.',
    'Non lu : absent de ce firmware ou réponse illisible ({t}).':
        'Not read: absent from this firmware or unreadable answer ({t}).',
    "Vitesse maxi {v} tr/s : très au-dessus d'un volant (2–8 tr/s). La protection anti-emballement réagira tard.":
        'Max speed {v} rev/s: far above a wheel (2–8 rev/s). The anti-runaway protection will react late.',
    'Valeur de résistance de freinage inhabituelle ({r} Ω) : mets la valeur gravée dessus.':
        'Unusual brake resistor value ({r} Ω): enter the value printed on it.',
    'Courant maximum ({i} A) trop près de la gamme de mesure ({r} A) : erreur de saturation possible.':
        'Maximum current ({i} A) too close to the measurement range ({r} A): saturation error possible.',
    'Courant de calibration × résistance ({x} V) au-dessus de la tension max de calibration ({m} V) : la calibration échouera.':
        'Calibration current × resistance ({x} V) above the max calibration voltage ({m} V): calibration will fail.',
    'Couple maximum du volant ({m} N·m) au-dessus de ce que permet le courant maximum (Kt × I = {k} N·m) : les fortes forces seront écrêtées.':
        'Wheel maximum torque ({m} N·m) above what the maximum current allows (Kt × I = {k} N·m): strong forces will be clipped.',
    'Appliquer ({n})':
        'Apply ({n})',
    'Aucun problème détecté.':
        'No problem detected.',
    'Ignorés : {l}':
        'Ignored: {l}',
    'Non lus dans la carte : {n}':
        'Not read on the board: {n}',
    'Non gérés par SimForge (laissés tels quels) : {n}':
        'Not handled by SimForge (left as is): {n}',
    'Coupure tension haute ({o} V) trop proche de la tension actuelle ({v} V) : la carte va couper au moindre freinage.':
        'High-voltage cut-off ({o} V) too close to the current voltage ({v} V): the board will cut off at the slightest braking.',
    'Coupure tension basse ({u} V) au-dessus de la tension actuelle ({v} V).':
        'Low-voltage cut-off ({u} V) above the current voltage ({v} V).',
    'Bandes du firmware : poids {a} Hz (Q {qa}), châssis {b} Hz (Q {qb}), route {c} Hz (Q {qc}).':
        'Firmware bands: weight {a} Hz (Q {qa}), chassis {b} Hz (Q {qb}), road {c} Hz (Q {qc}).',
    'Ces réglages ne doivent être changés que moteur au repos :\n{n}\n\nMettre le moteur au repos (il devient libre) puis appliquer ?':
        'These settings must only be changed with the motor idle:\n{n}\n\nSet the motor to idle (it becomes free) then apply?',
    'Problèmes détectés :\n\n{p}\n\nAppliquer quand même ?':
        'Problems detected:\n\n{p}\n\nApply anyway?',
    'La carte a retenu {v} au lieu de la valeur demandée (borne du firmware).':
        'The board kept {v} instead of the requested value (firmware limit).',
    'Fichier illisible : {e}':
        'Unreadable file: {e}',
    'Lecture {i}/{n}…':
        'Reading {i}/{n}…',
    '{p} = 1 ignoré (codeur incrémental sans index)':
        '{p} = 1 ignored (incremental encoder without index)',
    'Valeur inconnue ({v})':
        'Unknown value ({v})',
    'La carte contient {v} : affiché à la borne.':
        'The board holds {v}: shown at the limit.',
    'Valeur de la carte ({v}) hors de la plage habituelle : affichée telle quelle.':
        'Board value ({v}) outside the usual range: shown as is.',
    'État de la carte':
        'Board status',
    'Courant moteur (Iq)':
        'Motor current (Iq)',
    'Avant de commencer':
        'Before you start',
    "Les calibrations font tourner le moteur. Coche chaque point : les boutons de lancement restent grisés tant que tout n'est pas coché.":
        'Calibrations make the motor turn. Tick every item: the start buttons stay greyed out until everything is ticked.',
    'Jante enlevée : rien ne peut être frappé si le moteur tourne':
        'Rim removed: nothing can be hit if the motor turns',
    "Coupure de l'alimentation (interrupteur batterie) à portée de main":
        'Power cut-off (battery switch) within reach',
    'Codeur branché sur le connecteur M0, broche Z vide':
        'Encoder plugged into the M0 connector, Z pin empty',
    'Résistance de freinage branchée et vissée sur une plaque métallique':
        'Brake resistor connected and screwed onto a metal plate',
    'La tension mesurée doit être entre les seuils de coupure, et la résistance de freinage déclarée. Ces réglages se trouvent dans Réglages › Alimentation.':
        'The measured voltage must be between the cut-off thresholds, and the brake resistor declared. These settings are in Settings › Power supply.',
    'Ouvrir Réglages › Alimentation':
        'Open Settings › Power supply',
    "Une erreur présente bloque toute calibration. L'effacement réarme aussi la résistance de freinage.":
        'Any present error blocks every calibration. Clearing also re-arms the brake resistor.',
    "Le moteur siffle quelques secondes sans tourner : la carte mesure la résistance et l'inductance des phases. Paires de pôles et courant de calibration doivent être réglés avant (Réglages › Moteur et codeur).":
        'The motor beeps for a few seconds without turning: the board measures the phase resistance and inductance. Pole pairs and calibration current must be set first (Settings › Motor and encoder).',
    'Lancer la calibration moteur':
        'Start motor calibration',
    'Valider : moteur calibré':
        'Confirm: motor calibrated',
    'Calage du codeur':
        'Encoder alignment',
    "Le moteur tourne lentement d'environ un tour dans un sens puis dans l'autre. Le sens du codeur est trouvé automatiquement : pas besoin d'inverser A et B.":
        'The motor slowly turns about one revolution one way then the other. The encoder direction is found automatically: no need to swap A and B.',
    'Lancer le calage':
        'Start alignment',
    'Vérifier le CPR (un tour à la main)':
        'Check the CPR (one turn by hand)',
    'Moteur au repos : clique « Départ », fais exactement un tour de moteur à la main (repère au feutre), puis « Arrivée ». Le compteur doit avancer du CPR réglé.':
        'Motor idle: click “Start”, turn the motor exactly one revolution by hand (felt-pen mark), then “End”. The counter must advance by the set CPR.',
    'Essai en boucle fermée':
        'Closed-loop test',
    'Repos':
        'Idle',
    "Volant prêt dès l'allumage":
        'Wheel ready at power-up',
    "Sans ce réglage, la carte démarre moteur coupé et il faut refaire l'étape 4 à chaque fois.\nCe bouton règle la carte pour qu'à chaque allumage elle cale le codeur toute seule (le volant bouge d'environ un tour), puis active le moteur.\nÀ faire une seule fois, après les étapes 3 et 4.":
        'Without this, the board starts with the motor off and step 4 must be redone every time.\nThis button sets the board so that at every power-up it aligns the encoder by itself (the wheel moves about one turn), then enables the motor.\nDo it once, after steps 3 and 4.',
    'Régler le démarrage automatique':
        'Set up automatic start-up',
    'En cours…':
        'Running…',
    "C'est réglé, mais pas encore mémorisé. Clique « Enregistrer dans la carte » en bas à droite : la carte redémarre et fait son tour de calage (lâche le volant).":
        'Done, but not stored yet. Click “Save to board” at the bottom right: the board reboots and does its alignment turn (let go of the wheel).',
    'STOP enclenché':
        'STOP latched',
    'Réarme le STOP en haut à droite avant de lancer.':
        'Re-arm the STOP at the top right before starting.',
    'Erreurs présentes':
        'Errors present',
    "Efface d'abord les erreurs (étape 2) : la carte refuserait la commande.":
        'Clear the errors first (step 2): the board would refuse the command.',
    'Moteur marqué comme calibré (à mémoriser avec « Enregistrer »).':
        'Motor marked as calibrated (store it with “Save”).',
    'CPR':
        'CPR',
    "Mets d'abord le moteur au repos (bouton Repos, étape 6).":
        'Set the motor to idle first (Idle button, step 6).',
    'Démarrage automatique':
        'Automatic start-up',
    "Fais d'abord la calibration moteur (étape 3) : « moteur déjà calibré » n'a de sens qu'après.":
        'Do the motor calibration first (step 3): “motor already calibrated” only makes sense afterwards.',
    "Le moteur est actif mais aucun jeu n'envoie de force : à la main, il doit tourner librement (ou freiner légèrement), sans à-coups, sans partir tout seul. Coupure automatique au-delà de {v} °/s.":
        'The motor is active but no game sends force: by hand it must turn freely (or brake slightly), without jerks, without moving on its own. Automatic cut-off above {v} °/s.',
    "Coche d'abord toutes les précautions de l'étape 0 (et connecte la carte).":
        'First tick every precaution of step 0 (and connect the board).',
    "Le moteur n'est pas marqué comme calibré. Le calage échouera si la calibration moteur n'a pas été faite depuis l'allumage. Continuer ?":
        'The motor is not marked as calibrated. The alignment will fail if the motor calibration has not been done since power-up. Continue?',
    "Le moteur va être alimenté. Garde la main sur la coupure d'alimentation. Continuer ?":
        'The motor will be powered. Keep your hand on the power cut-off. Continue?',
    "✖ La carte n'a pas lancé l'opération : ":
        '✖ The board did not start the operation: ',
    '✔ Boucle fermée active. Tourne le moteur à la main pour vérifier.':
        '✔ Closed loop active. Turn the motor by hand to check.',
    "✖ Pas de mesure : la calibration n'a pas abouti (STOP ? erreur ?).":
        '✖ No measurement: the calibration did not complete (STOP? error?).',
    'résistance de freinage désactivée':
        'brake resistor disabled',
    'seuil haut très proche de la tension actuelle':
        'high threshold very close to the current voltage',
    '✖ Échec : ':
        '✖ Failed: ',
    'Valeurs cohérentes pour un moteur de volant.':
        'Consistent values for a wheel motor.',
    'Valeurs inhabituelles : vérifie les fils moteur et les réglages de calibration.':
        'Unusual values: check the motor wires and the calibration settings.',
    '{n} erreur(s) présente(s).':
        '{n} error(s) present.',
    'STOP enclenché.':
        'STOP latched.',
    'aucune erreur remontée, réessaie.':
        'no error reported, try again.',
    '✖ Refusé : ':
        '✖ Refused: ',
    'CPR ou paires de pôles faux : vérifie le CPR (PPR × 4 × rapport) et le nombre de paires de pôles.':
        'Wrong CPR or pole pairs: check the CPR (PPR × 4 × ratio) and the number of pole pairs.',
    'Lecture impossible.':
        'Read failed.',
    'tension {v} V hors de {a}–{b} V':
        'voltage {v} V outside {a}–{b} V',
    '✔ {v} V entre {a} et {b} V · résistance {r} Ω active.':
        '✔ {v} V between {a} and {b} V · {r} Ω resistor active.',
    "l'axe est resté au repos.":
        'the axis stayed idle.',
    'Le codeur ne compte pas : alimentation 5 V, GND, A/B et résistances de tirage.':
        'The encoder does not count: 5 V supply, GND, A/B and pull-up resistors.',
    '✔ Codeur calé, sens trouvé : {d}. Le moteur peut passer en boucle fermée.':
        '✔ Encoder aligned, direction found: {d}. The motor can enter closed loop.',
    'Départ noté ({v}). Fais un tour complet puis « Arrivée ».':
        'Start recorded ({v}). Turn one full revolution then “End”.',
    'valeur de résistance de freinage suspecte ({r} Ω)':
        'suspicious brake resistor value ({r} Ω)',
    '✔':
        '✔',
    '⚠':
        '⚠',
    'Résistance {r} Ω, inductance {l} µH.':
        'Resistance {r} Ω, inductance {l} µH.',
    'codeur pas prêt':
        'encoder not ready',
    "Refais un tour bien exact ; si l'écart persiste, le CPR est faux.":
        'Turn exactly one revolution again; if the difference persists, the CPR is wrong.',
    '{d} points comptés pour {c} réglés ({e} %).':
        '{d} counts for {c} set ({e} %).',
    'Valeur lue dans la carte ({v}) hors de la plage habituelle : affichée telle quelle.':
        'Value read from the board ({v}) is outside the usual range: shown as is.',
    # ---- V3 : pédales, menu
    'Pédales actives détectées (port série de chaque pédale)':
        "Active pedals detected (each pedal's serial port)",
    'Toutes les commandes envoyées et les événements de connexion (volant et pédales).':
        'All commands sent and connection events (wheel and pedals).',
    "Vue d'ensemble":
        'Overview',
    'VOLANT':
        'WHEEL',
    'PÉDALES':
        'PEDALS',
    'OUTILS':
        'TOOLS',
    'Console volant':
        'Wheel console',
    'Aucune pédale détectée':
        'No pedal detected',
    '  —  DÉMO (matériel simulé)':
        '  —  DEMO (simulated hardware)',
    'Pédales {n}':
        'Pedals {n}',
    'pédale non connectée':
        'pedal not connected',
    'configuration mémorisée':
        'settings saved',
    'configuration appliquée':
        'settings applied',
    'Pédale trouvée : {n}':
        'Pedal found: {n}',
    'Pédale déconnectée : {n}':
        'Pedal disconnected: {n}',
    'Pédale {p} : plus de données':
        'Pedal {p}: no more data',
    'Pédale {p} : port perdu ({e})':
        'Pedal {p}: port lost ({e})',
    'Pédale {p} : firmware incompatible (structure v{v}, SimForge attend v{w}). Flashe le firmware fourni (onglet Firmware des pédales).':
        'Pedal {p}: incompatible firmware (structure v{v}, SimForge expects v{w}). Flash the supplied firmware (Pedals › Firmware).',
    'Pédale':
        'Pedal',
    'Embrayage':
        'Clutch',
    'Frein':
        'Brake',
    'Accélérateur':
        'Throttle',
    "Erreur d'assignation":
        'Assignment error',
    'Non assignée':
        'Not assigned',
    'servo non connecté':
        'servo not connected',
    'servo connecté':
        'servo connected',
    'servo en veille':
        'servo idle',
    'servo arrêté':
        'servo stopped',
    'normal':
        'normal',
    'palonnier':
        'rudder',
    'palonnier + frein':
        'rudder + brake',
    'le servo ne répond plus (liaison série du servo)':
        'the servo no longer answers (servo serial link)',
    'ESP-NOW : charge utile invalide':
        'ESP-NOW: invalid payload',
    'ESP-NOW : version différente':
        'ESP-NOW: version mismatch',
    'ESP-NOW : CRC faux':
        'ESP-NOW: bad CRC',
    'Rôle de la pédale':
        'Pedal role',
    'Début de course':
        'Travel start',
    'Fin de course':
        'Travel end',
    'Précharge (force au repos)':
        'Preload (force at rest)',
    'Force maximum':
        'Maximum force',
    'Sortie maxi vers le jeu':
        'Max output to the game',
    'Axe envoyé au jeu':
        'Axis sent to the game',
    'ABS simulé (sans jeu)':
        'Simulated ABS (no game)',
    "Seuil de l'ABS simulé":
        'Simulated ABS threshold',
    "Fréquence de l'ABS":
        'ABS frequency',
    "Amplitude de l'ABS":
        'ABS amplitude',
    "Forme de l'ABS":
        'ABS waveform',
    "L'ABS agit sur":
        'ABS acts on',
    'Régime : fréquence mini':
        'RPM: min frequency',
    'Régime : fréquence maxi':
        'RPM: max frequency',
    'Régime : amplitude':
        'RPM: amplitude',
    'Point de patinage : position':
        'Bite point: position',
    'Point de patinage : amplitude':
        'Bite point: amplitude',
    'Point de patinage : fréquence':
        'Bite point: frequency',
    'Patinage des roues : amplitude':
        'Wheel slip: amplitude',
    'Patinage des roues : fréquence':
        'Wheel slip: frequency',
    'Effet G : multiplicateur':
        'G-force: multiplier',
    'Chocs de la route : multiplicateur':
        'Road impacts: multiplier',
    'Pas de la vis à billes':
        'Ball screw pitch',
    'Capacité du capteur de force':
        'Load cell rating',
    'Inverser le capteur de force':
        'Invert load cell',
    'Inverser le sens du moteur':
        'Invert motor direction',
    'Énergie de freinage du servo':
        'Servo braking energy',
    'Valeur de la résistance externe':
        'External resistor value',
    'Mise en veille du servo':
        'Servo standby',
    'Au démarrage':
        'At power-up',
    'Masse virtuelle':
        'Virtual mass',
    'Amortissement virtuel':
        'Virtual damping',
    "Progressivité de l'amortissement":
        'Damping progressivity',
    'Frottement simulé':
        'Simulated friction',
    'Raideur de la butée':
        'End stop stiffness',
    'Zone de la butée':
        'End stop zone',
    "Filtre de l'axe de jeu":
        'Game axis filter',
    "Filtre de l'axe de jeu : bruit":
        'Game axis filter: noise',
    'Force mini pour les effets':
        'Minimum force for effects',
    'Détection de pas perdus (drapeaux)':
        'Lost step detection (flags)',
    'Seuil de détection des butées':
        'End stop detection threshold',
    'Drapeaux de débogage':
        'Debug flags',
    'pas de la vis entre 1 et 20 mm':
        'screw pitch between 1 and 20 mm',
    'course de la pédale entre 10 et 200 mm':
        'pedal travel between 10 and 200 mm',
    'positions de début/fin entre 0 et 100 %':
        'start/end positions between 0 and 100 %',
    "la fin doit dépasser le début d'au moins 5 %":
        'the end must exceed the start by at least 5 %',
    'capacité du capteur de force ≥ 20 kg':
        'load cell rating ≥ 20 kg',
    'rôle de pédale invalide':
        'invalid pedal role',
    'Position de repos de la pédale, en % de la course mécanique.':
        'Pedal rest position, in % of the mechanical travel.',
    'Force à fond de course (frein : souvent 40 à 80 kg avec un capteur de 100 kg).':
        'Force at full travel (brake: often 40 to 80 kg with a 100 kg load cell).',
    '100 % = le jeu reçoit 100 % à la force maximum.':
        '100 % = the game receives 100 % at maximum force.',
    "La pédale vibre toute seule au-delà du seuil : pratique pour régler l'ABS hors jeu.":
        'The pedal vibrates by itself beyond the threshold: handy for tuning ABS outside a game.',
    'Valeur brute du firmware (0–255).':
        'Raw firmware value (0–255).',
    'Valeur brute du firmware.':
        'Raw firmware value.',
    'mm/tr':
        'mm/rev',
    'Valeur écrite sur le capteur (ex. 100 kg).':
        'Value printed on the load cell (e.g. 100 kg).',
    "Valeur marquée sur la résistance de freinage (10 Ω au réglage d'usine, 0 = 5 Ω). Le firmware en déduit la "
    "puissance qu'elle absorbe et la vitesse de remontée permise : trop basse, la pédale remonte trop vite et la "
    "tension du servo grimpe.":
        "Value marked on the brake resistor (10 Ω factory setting, 0 = 5 Ω). The firmware derives from it the power "
        "the resistor absorbs and the allowed return speed: too low, the pedal comes back too fast and the servo "
        "voltage climbs.",
    'Coupe le servo après ce temps sans appui (LED rouge) ; un appui franc le réveille. 0 = jamais.':
        'Switches the servo off after this time without a press (red LED); a firm press wakes it up. 0 = never.',
    'Valeur brute du firmware ; 0 = jamais.':
        'Raw firmware value; 0 = never.',
    'force maxi entre 1 et 500 kg':
        'max force between 1 and 500 kg',
    'précharge entre 0 et la force maxi':
        'preload between 0 and the max force',
    'Force (frein à capteur)':
        'Force (load cell brake)',
    'Position (course)':
        'Position (travel)',
    'Dent de scie':
        'Sawtooth',
    'la force':
        'force',
    'la course':
        'travel',
    'résistance interne du servo':
        'servo internal resistor',
    '+ résistance externe pilotée':
        '+ controlled external resistor',
    'circuit matériel seul':
        'hardware circuit only',
    'la pédale démarre seule':
        'the pedal starts by itself',
    'attend le logiciel (veille)':
        'waits for the software (standby)',
    'cote {k} entre {lo} et {hi} mm':
        'dimension {k} between {lo} and {hi} mm',
    'Carte non connectée':
        'Board not connected',
    'Pédales':
        'Pedals',
    "Aucune pédale détectée. Branche chaque pédale par son port USB « UART » (puce CH343/CP210x), ou par son port "
    "USB natif avec le firmware « un câble », et ferme SimHub, qui garde les ports ouverts.":
        'No pedal detected. Plug each pedal in through its "UART" USB port (CH343/CP210x chip), or through its '
        'native USB port with the "one cable" firmware, and close SimHub, which keeps the ports open.',
    'Réglages des pédales':
        'Pedal settings',
    'Firmware des pédales':
        'Pedal firmware',
    'Réglages du volant':
        'Wheel settings',
    'Pour vérifier ce que voit le jeu (volant + pédales), utilise Outils › Joy tester.':
        'To check what the game sees (wheel + pedals), use Tools › Joy tester.',
    'pas de capteur':
        'no sensor',
    'Erreur':
        'Error',
    'Course':
        'Travel',
    'Force':
        'Force',
    'Batterie':
        'Battery',
    'Température carte':
        'Board temperature',
    'Firmware incompatible : flashe-le dans Pédales › Firmware.':
        'Incompatible firmware: flash it in Pedals › Firmware.',
    'Calage en cours':
        'Calibrating',
    'Moteur au repos':
        'Motor idle',
    'Erreur {c} : {d}':
        'Error {c}: {d}',
    'code inconnu':
        'unknown code',
    'Flasher le firmware des pédales':
        'Flash the pedal firmware',
    'Tout effacer avant (efface aussi les réglages enregistrés)':
        'Erase everything first (also erases saved settings)',
    'Flasher':
        'Flash',
    "Si le flashage n'arrive pas à se connecter":
        'If flashing cannot connect',
    'Licence':
        'Licence',
    'Flashage en cours…':
        'Flashing…',
    'Firmware open source de ChrGri (DIY-Sim-Racing-FFB-Pedal), compilé pour ton PCB V6 et compatible avec SimForge. Fais une pédale à la fois. Tes réglages enregistrés sont conservés si la version de configuration ne change pas ; sinon la pédale repart des valeurs par défaut.':
        'Open-source firmware by ChrGri (DIY-Sim-Racing-FFB-Pedal), built for your PCB V6 and compatible with SimForge. Do one pedal at a time. Your saved settings are kept if the config version does not change; otherwise the pedal starts again from the defaults.',
    'Port':
        'Port',
    "1. Ferme SimHub (il garde le port ouvert).\n2. Utilise le port USB de la carte relié à la puce série (CH343/CP210x).\n3. Maintiens le bouton BOOT de l'ESP32, appuie puis relâche RESET, relâche BOOT, puis clique de nouveau sur « Flasher ».":
        '1. Close SimHub (it keeps the port open).\n2. Use the board\'s USB port wired to the serial chip (CH343/CP210x).\n3. Hold the ESP32\'s BOOT button, press and release RESET, release BOOT, then click "Flash" again.',
    'Firmware : ChrGri et contributeurs, DIY-Sim-Racing-FFB-Pedal, licence CC BY-NC-SA 4.0 (usage non commercial, partage dans les mêmes conditions). Voir firmware/LICENSE.txt.':
        'Firmware: ChrGri and contributors, DIY-Sim-Racing-FFB-Pedal, licence CC BY-NC-SA 4.0 (non-commercial use, share alike). See firmware/LICENSE.txt.',
    'Aucun firmware trouvé dans le dossier « firmware » de SimForge.':
        'No firmware found in SimForge\'s "firmware" folder.',
    'Choisis un port.':
        'Choose a port.',
    'Terminé. La pédale redémarre ; elle réapparaît dans Pédales › Réglages.':
        'Done. The pedal restarts; it shows up again in Pedals › Settings.',
    "Le module esptool manque : installe-le (pip install esptool) ou relance « SimForge Studio V3.bat » qui l'installe.":
        'The esptool module is missing: install it (pip install esptool) or run "SimForge Studio V3.bat", which installs it.',
    'Essaie la manipulation BOOT/RESET ci-dessous.':
        'Try the BOOT/RESET procedure below.',
    'Flasher « {f} » sur {p} ?\nNe débranche pas la pédale pendant le flashage.':
        'Flash "{f}" on {p}?\nDo not unplug the pedal while flashing.',
    'Échec : {m}':
        'Failed: {m}',
    'voir le journal ci-dessous':
        'see the log below',
    'la courbe doit commencer à 0 % et finir à 100 % de course':
        'the curve must start at 0 % and end at 100 % travel',
    'les positions de la courbe doivent être croissantes':
        'the curve positions must be increasing',
    'Identifier (bip)':
        'Identify (beep)',
    'Relire':
        'Read back',
    'Envoie les réglages à la pédale sans les mémoriser (perdus au redémarrage).':
        'Sends the settings to the pedal without saving them (lost on restart).',
    'Enregistrer dans la pédale':
        'Save to pedal',
    'Exporter…':
        'Export…',
    'Importer…':
        'Import…',
    'Courbe de force':
        'Force curve',
    'Axe de jeu':
        'Game axis',
    'Entrée':
        'Input',
    'Sortie':
        'Output',
    'En direct':
        'Live',
    'Messages texte envoyés par le firmware de la pédale.':
        'Text messages sent by the pedal firmware.',
    'test ABS':
        'ABS test',
    'Nombre de points':
        'Number of points',
    'Modèle':
        'Preset',
    '— choisir —':
        '— choose —',
    'Linéaire':
        'Linear',
    'Progressive (frein)':
        'Progressive (brake)',
    'Très progressive':
        'Very progressive',
    'Dégressive':
        'Regressive',
    'Fichier JSON avec tous les champs de la configuration de la pédale.':
        'JSON file with every field of the pedal configuration.',
    "Aucune pédale détectée. Branche la pédale par son port USB « UART » (puce CH343/CP210x), ou par son port USB "
    "natif avec le firmware « un câble », et ferme SimHub.":
        'No pedal detected. Plug the pedal in through its "UART" USB port (CH343/CP210x chip), or through its '
        'native USB port with the "one cable" firmware, and close SimHub.',
    'états/s':
        'states/s',
    'Fait biper la pédale pour la reconnaître.':
        'Makes the pedal beep so you can tell which one it is.',
    "Indisponible par câble USB avec le firmware de ChrGri : la pédale ne bipe que sur ordre du récepteur sans fil "
    "(ESP-NOW). Le firmware « V6 un câble » de la page Firmware le fait aussi par USB.":
        "Not available over USB with ChrGri's firmware: the pedal only beeps when the wireless receiver (ESP-NOW) "
        "asks it to. The \"V6 one cable\" firmware on the Firmware page also does it over USB.",
    "bip d'identification":
        'identify beep',
    "Tester l'ABS (1 s)":
        'Test ABS (1 s)',
    "Déclenche l'effet ABS pendant 1 seconde, sans jeu : appuie sur la pédale.":
        'Triggers the ABS effect for 1 second, without a game: press the pedal.',
    'firmware {v}':
        'firmware {v}',
    'Firmware incompatible (structure v{v}, attendu v{w}) : flashe le firmware fourni dans Pédales › Firmware.':
        'Incompatible firmware (structure v{v}, expected v{w}): flash the supplied firmware in Pedals › Firmware.',
    'Mémoriser ces réglages dans la pédale ? Ils remplaceront ceux enregistrés.':
        'Save these settings in the pedal? They will replace the saved ones.',
    'En jeu, les effets (ABS, régime, patinage…) ne marchent que si un logiciel envoie la télémétrie du jeu à la pédale (plugin SimHub de ChrGri). Les réglages ci-dessus restent valables.':
        "In a game, the effects (ABS, RPM, slip…) only work if software sends the game telemetry to the pedal (ChrGri's SimHub plugin). The settings above still apply.",
    'Réglages refusés (la pédale les ignorerait) : {e}':
        'Settings rejected (the pedal would ignore them): {e}',
    '{n} champs manquants':
        '{n} fields missing',
    # page Pédales › Réglages organisée comme le plugin SimHub
    'ABS':
        'ABS',
    'Actions':
        'Actions',
    'Angle de la pédale : {c:.0f}°  ·  début de course {s:.0f}°  ·  fin de course {e:.0f}°  ·  débattement {d:.0f}°':
        'Pedal angle: {c:.0f}°  ·  travel start {s:.0f}°  ·  travel end {e:.0f}°  ·  swing {d:.0f}°',
    'Chocs de la route':
        'Road impact',
    'Cinématique':
        'Kinematics',
    'Cote a : capteur de force (B → C)':
        'Dimension a: load cell (B → C)',
    'Cote b : pivot → capteur (O → C)':
        'Dimension b: pivot → load cell (O → C)',
    'Cote c horizontale (O → A)':
        'Dimension c horizontal (O → A)',
    'Cote c verticale (hauteur de B)':
        'Dimension c vertical (height of B)',
    'Cote d : capteur → bout de pédale (C → D)':
        'Dimension d: load cell → pedal tip (C → D)',
    'Cotes impossibles : la pédale ne peut pas se monter ainsi':
        'Impossible dimensions: the pedal cannot be assembled this way',
    'Courbe force-course':
        'Force-travel curve',
    'Course du chariot (depuis A)':
        'Sled travel (from A)',
    'Dynamique':
        'Dynamics',
    'Effet G':
        'G-force',
    'Effets':
        'Effects',
    'Effets globaux':
        'Global effects',
    'Filtre':
        'Filter',
    'Général':
        'General',
    'Messages':
        'Messages',
    'O : pivot bas de la pédale · A : début de la course du chariot · B : articulation du capteur de force sur le chariot · C : articulation du capteur sur la pédale · D : bout de la pédale (appui du pied). Le trait rouge est la course utilisée (entre début et fin de course).':
        'O: lower pedal pivot · A: start of the sled travel · B: load cell joint on the sled · C: load cell joint on the pedal · D: pedal tip (where the foot rests). The red line is the travel in use (between travel start and travel end).',
    'Pas de configuration lue':
        'No configuration read',
    'Patinage des roues':
        'Wheel slip',
    'Point de patinage':
        'Bite point',
    'Pédale non branchée':
        'Pedal not plugged in',
    'Régime':
        'Engine RPM',
    'Servo':
        'Servo',
    'Clique sur une cote du schéma pour la modifier (Entrée pour valider, Échap pour annuler). Les cotes modifiées sont en orange.':
        'Click a dimension on the drawing to change it (Enter to confirm, Esc to cancel). Changed dimensions are shown in orange.',
    'course':
        'travel',
    'Force demandée selon la course. Fais glisser les points orange pour régler la courbe ; le point bleu montre la pédale en direct.':
        'Requested force versus travel. Drag the orange points to shape the curve; the blue dot shows the pedal live.',
    'Valeur envoyée au jeu selon la force (ou la course). Linéaire par défaut. Fais glisser les points pour la régler.':
        'Value sent to the game versus force (or travel). Linear by default. Drag the points to shape it.',
    "Le firmware ne change le rôle d'une pédale déjà assignée qu'en l'enregistrant. Enregistrer tous ces réglages dans la pédale maintenant ?":
        'The firmware only changes the role of an already assigned pedal when the settings are saved. Save all these settings to the pedal now?',
    "Choisit l'axe de manette et les effets reçus. Une pédale déjà assignée ne change de rôle qu'avec « Enregistrer dans la pédale ».":
        'Selects the controller axis and the effects received. An already assigned pedal only changes role with “Save to pedal”.',
    'le 2e point de la courbe de force est à 1 % : le firmware passerait la pédale en mode palonnier (avion). Mets-le à 0 ou 2 % ou plus.':
        'the 2nd point of the force curve is at 1 %: the firmware would switch the pedal to rudder (flight) mode. Set it to 0 or to 2 % or more.',
    'Type de filtre du capteur de force':
        'Load cell filter type',
    'Kalman (vitesse)':
        'Kalman (velocity)',
    'Kalman (accélération)':
        'Kalman (acceleration)',
    'Exponentiel':
        'Exponential',
    'Aucun':
        'None',
    'IMM adaptatif (maintien/mouvement)':
        'IMM adaptive (hold/move)',
    "IMM adaptatif : lisse fort quand le pied tient la pédale immobile, réagit vite quand il bouge (doc ChrGri : "
    "IMM_Loadcell_Filter.md).\nAttention : avec le firmware actuel, ce filtre peut bloquer la pédale en position de "
    "départ (force figée, « [IMM] k_foot=5000 » dans les messages). Si ça arrive, prends un autre filtre.":
        "IMM adaptive: smooths strongly while the foot holds the pedal still, reacts fast when it moves (ChrGri docs: "
        "IMM_Loadcell_Filter.md).\nWarning: with the current firmware, this filter can lock the pedal at its start "
        "position (frozen force, \"[IMM] k_foot=5000\" in the messages). If that happens, pick another filter.",
    'Vitesse du filtre (1 = doux … 255 = rapide)':
        'Filter speed (1 = smooth … 255 = fast)',
    "Plus haut : la pédale suit plus vite le pied mais le bruit du capteur passe davantage (vibration, surtout quand la pédale bouge doucement). Plus bas : plus calme mais plus lourd.\nAvec le filtre IMM, c'est la vitesse en mouvement : 1 ≈ 5 Hz, 128 ≈ 17 Hz, 255 ≈ 60 Hz.":
        'Higher: the pedal follows the foot faster but more load cell noise gets through (vibration, mostly when the pedal moves slowly). Lower: calmer but heavier.\nWith the IMM filter, this is the speed while moving: 1 ≈ 5 Hz, 128 ≈ 17 Hz, 255 ≈ 60 Hz.',
    'Réveiller':
        'Wake up',
    'réveil de la pédale':
        'pedal wake-up',
    'Redémarrer':
        'Restart',
    'Redémarre la pédale (comme débrancher/rebrancher son alimentation USB).':
        'Restarts the pedal (like unplugging and replugging its USB power).',
    'Infos firmware':
        'Firmware info',
    "Demande à la pédale d'écrire ses informations dans les messages.":
        'Asks the pedal to print its information in the messages.',
    'infos firmware':
        'firmware info',
    'Redémarrer la pédale ? Les réglages non enregistrés seront perdus.':
        'Restart the pedal? Settings that were not saved will be lost.',
    'redémarrage de la pédale':
        'pedal restart',
    "Sort la pédale de l'attente du logiciel au démarrage (LED bleue, réglage « Au démarrage : attend le logiciel »). Après la « Mise en veille du servo » (LED rouge), seul un appui franc sur la pédale la réveille.":
        'Takes the pedal out of waiting for the software at power-up (blue LED, “At power-up: waits for the software”). After the “Servo sleep” time (red LED), only a firm press on the pedal wakes it up.',
    'Diagnostic servo':
        'Servo diagnostics',
    "État détaillé envoyé par la pédale : sert à comprendre un servo qui se bloque. Si la tension monte à chaque relâcher jusqu'au blocage, l'énergie de freinage n'est pas évacuée (onglet Général, « Énergie de freinage du servo »).":
        'Detailed state sent by the pedal: helps understand a servo that locks up. If the voltage rises at each release until it locks, the braking energy is not dissipated (General tab, “Servo braking energy”).',
    "Recevoir l'état détaillé du servo":
        'Receive the detailed servo state',
    'Applique (sans mémoriser) le drapeau de débogage 64 + 4 de la pédale. Les modifications en attente ne sont pas envoyées.':
        'Applies (without storing) debug flag 64 + 4 on the pedal. Pending changes are not sent.',
    'Tension du servo':
        'Servo voltage',
    'Tension la plus haute':
        'Highest voltage',
    'Courant du servo':
        'Servo current',
    'Écart de position (consigne − réelle)':
        'Position error (target − actual)',
    'pas':
        'steps',
    'Vitesse du servo':
        'Servo speed',
    'tr/min':
        'rpm',
    'Remettre le maxi à zéro':
        'Reset the maximum',
    'Temps':
        'Time',
    'active':
        'on',
    'inactive':
        'off',
    "Prévu pour la mise à zéro (démarrage, réveil) : le chariot avance jusqu'à ce que le courant du servo dépasse ce seuil, en % de son courant, et le firmware y place la butée (10 à 50 %).\nSans effet avec le firmware fourni (ChrGri, commit 7564dad) : StepperWithLimits.cpp ignore la valeur reçue et garde toujours 30 %.":
        'Meant for homing (power-up, wake-up): the sled moves until the servo current exceeds this threshold, in % of its current, and the firmware puts the endstop there (10 to 50 %).\nNo effect with the bundled firmware (ChrGri, commit 7564dad): StepperWithLimits.cpp ignores the received value and always keeps 30 %.',
    # auto-test des pédales
    "Bêta. Cherche le réglage de filtre le plus réactif qui ne fait pas vibrer la pédale : vitesse du filtre de 255 à 20, puis amortissement si besoin. Environ 2 à 3 min. Rien n'est enregistré dans la pédale pendant le test ; tes modifications en attente ne sont pas envoyées. Garde le pied sur la pédale et suis les consignes ; « Arrêter » remet tes réglages.":
        'Beta. Looks for the most responsive filter setting that does not make the pedal vibrate: filter speed from 255 down to 20, then damping if needed. About 2 to 3 min. Nothing is stored in the pedal during the test; your pending changes are not sent. Keep your foot on the pedal and follow the instructions; “Stop” puts your settings back.',
    "Lancer l'auto-test":
        'Start the auto-test',
    'Arrêter':
        'Stop',
    'Auto-test arrêté : réglages de départ remis.':
        'Auto-test stopped: starting settings restored.',
    'Enregistrer ce réglage dans la pédale':
        'Save this setting to the pedal',
    "Revenir aux réglages d'avant":
        'Go back to the previous settings',
    'Réglage refusé, auto-test arrêté : {e}':
        'Setting rejected, auto-test stopped: {e}',
    'Auto-test lancé sur {p}.':
        'Auto-test started on {p}.',
    'Étape 1 : bruit du capteur':
        'Step 1: load cell noise',
    'Pose le pied sur la pédale SANS appuyer, et ne bouge plus.':
        'Rest your foot on the pedal WITHOUT pressing, and keep still.',
    'Vitesse du filtre {s}, amortissement {d:.2f}':
        'Filter speed {s}, damping {d:.2f}',
    'Attends… puis appuie et relâche doucement, plusieurs fois, comme quand ça vibrait.':
        'Wait… then press and release slowly, several times, like when it vibrated.',
    'Pédale déconnectée : auto-test arrêté.':
        'Pedal disconnected: auto-test stopped.',
    'Appuie et relâche doucement, plusieurs fois… (mesure en cours)':
        'Press and release slowly, several times… (measuring)',
    "La pédale n'envoie pas son état détaillé : auto-test impossible avec ce firmware.":
        'The pedal does not send its detailed state: auto-test not possible with this firmware.',
    'Bruit du capteur au repos : {n:.2f} kg (écart type).':
        'Load cell noise at rest: {n:.2f} kg (standard deviation).',
    'Pédale trop peu bougée ({t:.0f} % de course) : on recommence ce palier.':
        'Pedal moved too little ({t:.0f} % of travel): repeating this step.',
    'Pédale toujours trop peu bougée : palier compté tel quel.':
        'Pedal still moved too little: step counted as is.',
    'Vitesse {s}, amortissement {d:.2f} : {o:.1f} % du temps en oscillation → {r}':
        'Speed {s}, damping {d:.2f}: {o:.1f} % of the time oscillating → {r}',
    'stable':
        'stable',
    'vibre':
        'vibrates',
    "Tous les paliers vibrent : essai avec plus d'amortissement.":
        'Every step vibrates: trying more damping.',
    'Résultat : vitesse du filtre {s}, amortissement {d:.2f}':
        'Result: filter speed {s}, damping {d:.2f}',
    "Réglage appliqué (pas encore enregistré). Essaie la pédale, puis garde-le ou reviens à tes réglages d'avant.":
        'Setting applied (not stored yet). Try the pedal, then keep it or go back to your previous settings.',
    'Aucun réglage stable trouvé':
        'No stable setting found',
    "Même au plus calme, la pédale vibre : réglages d'avant remis. Vérifie la mécanique (jeu, frottements), la précharge et le début de la courbe de force.":
        'Even at the calmest setting the pedal vibrates: previous settings restored. Check the mechanics (play, friction), the preload and the start of the force curve.',
    'Enregistrer ce réglage de filtre dans la pédale ?':
        'Save this filter setting to the pedal?',
    'Réglage enregistré dans la pédale.':
        'Setting saved to the pedal.',
    "Réglages d'avant remis (rien n'a été enregistré).":
        'Previous settings restored (nothing was stored).',
    'Auto-test (bêta)':
        'Auto-test (beta)',
    # fiabilité
    'Déjà réglé ainsi dans la carte.':
        'Already set this way in the board.',
    'Enregistrement arrêté : {e}':
        'Recording stopped: {e}',
    'Préparé mais pas envoyé : vérifie les valeurs en orange dans Réglages puis « Appliquer ».':
        'Prepared but not sent: check the orange values in Settings, then “Apply”.',
    'Pédale {p} : envoi impossible, port perdu ({e})':
        'Pedal {p}: cannot send, port lost ({e})',
    'Réglages pas encore lus dans la carte : {l}. Relis la carte puis réessaie.':
        'Settings not read from the board yet: {l}. Read the board again, then retry.',
    "Test impossible : l'effet DirectInput n'a pas pu être lancé ({e}).":
        'Test not possible: the DirectInput effect could not be started ({e}).',
    'valeurs non numériques : {l}':
        'non-numeric values: {l}',
    'Écriture impossible : {e}':
        'Cannot write: {e}',
    "Lecture DirectInput, comme un jeu. Chaque pédale est une manette séparée (« FFB_Pedal_Brake », « FFB_Pedal_Throttle », « FFB_Pedal_Clutch ») qui n'apparaît que si son port USB natif de l'ESP32-S3 est branché : le port série (puce CH343) sert seulement aux réglages. « Pas » = variation entre deux lectures (≈100 Hz) : au repos il doit être nul ou de quelques unités.":
        'DirectInput reading, like a game. Each pedal is a separate controller (“FFB_Pedal_Brake”, “FFB_Pedal_Throttle”, “FFB_Pedal_Clutch”) that only shows up when the ESP32-S3 native USB port is plugged in: the serial port (CH343 chip) is only used for settings. “Step” = change between two reads (≈100 Hz): at rest it should be zero or a few units.',
    "surtension du servo : l'énergie rendue quand la pédale remonte n'est pas évacuée. Voir "
    "« Énergie de freinage du servo » (onglet Général) et la tension dans « Diagnostic servo ».":
        "servo overvoltage: the energy returned when the pedal comes back up is not dissipated. See "
        "\"Servo braking energy\" (General tab) and the voltage in \"Servo diagnostics\".",
    'sous-tension du servo : alimentation trop faible ou coupée un instant.':
        'servo undervoltage: power supply too weak or briefly cut.',
    'surintensité dans le servo : blocage mécanique ou câblage moteur.':
        'servo overcurrent: mechanical jam or motor wiring.',
    'codeur du servo : connecteur ou servo défectueux.':
        'servo encoder: faulty connector or servo.',
    'la carte ne parle plus au servo : câble entre la carte et le servo, ou servo hors tension.':
        'the board no longer talks to the servo: cable between board and servo, or servo powered off.',
    "courant trop fort pendant 15 s : moteur coupé jusqu'au redémarrage de la pédale.":
        'current too high for 15 s: motor disabled until the pedal is restarted.',
    'servo en veille (LED rouge) : un appui franc sur la pédale le réveille.':
        'servo asleep (red LED): a firm press on the pedal wakes it up.',
    'lecture et effacement des alarmes du servo':
        'reading and clearing servo alarms',
    'Alarmes servo':
        'Servo alarms',
    "Le servo peut se mettre en alarme (surtension…) et bloquer la pédale sans que la carte le voie : LED verte, "
    "aucune erreur. Ce bouton écrit l'historique des alarmes dans les messages puis les efface, ce qui relance le "
    "servo sans redémarrer. La pédale se fige 1 s ; les modifications en attente ne sont pas envoyées.":
        "The servo can go into alarm (overvoltage…) and lock the pedal without the board noticing: green LED, no "
        "error. This button writes the alarm history to the messages, then clears the alarms, which restarts the "
        "servo without a reboot. The pedal freezes for 1 s; pending changes are not sent.",
    "le servo n'a pas pu enregistrer ses paramètres : coupe puis rallume son alimentation.":
        'the servo could not save its parameters: switch its power off and on again.',
    "filtre IMM bloqué à sa limite : la pédale ne suit plus le pied. Prends un autre « Type de filtre du capteur "
    "de force » (onglet Filtre).":
        'IMM filter stuck at its limit: the pedal no longer follows the foot. Pick another "Load cell filter type" '
        '(Filter tab).',
    "Aucun réglage stable, le plus calme : vitesse du filtre {s}, amortissement {d:.2f} ({o:.1f} % du temps en "
    "oscillation)":
        "No stable setting, the calmest: filter speed {s}, damping {d:.2f} ({o:.1f} % of the time oscillating)",
    "Réglage le plus calme appliqué (pas encore enregistré). Essaie la pédale : garde-le s'il te convient, sinon "
    "reviens à tes réglages d'avant et vérifie la mécanique (jeu, frottements), la précharge et le début de la "
    "courbe de force.":
        "Calmest setting applied (not saved yet). Try the pedal: keep it if it suits you, otherwise go back to your "
        "previous settings and check the mechanics (play, friction), the preload and the start of the force curve.",
    "Masse ressentie au bout de la pédale. Plus lourde : pédale plus calme mais plus lente à suivre le pied.":
        "Mass felt at the end of the pedal. Heavier: calmer pedal but slower to follow the foot.",
    "Taux d'amortissement : 1 = juste assez pour ne pas rebondir, plus haut = pédale plus freinée, contre les "
    "vibrations. Le firmware ne descend pas sous 0,5.":
        "Damping ratio: 1 = just enough not to bounce, higher = more braked pedal, against vibration. The firmware "
        "does not go below 0.5.",
    "La carte n'a pas activé le moteur (état {s}, erreur d'axe {e}). Regarde le Moniteur, efface les erreurs puis "
    "réessaie.":
        "The board did not enable the motor (state {s}, axis error {e}). Check the Monitor, clear the errors and try "
        "again.",
    "Le volant est hors de sa course réglée (±{r:.0f}°) : ramène-le dans la course, puis active le moteur. Sinon la "
    "butée le renvoie d'un coup.":
        "The wheel is outside its set range (±{r:.0f}°): bring it back within range, then enable the motor. "
        "Otherwise the endstop throws it back at once.",
    'STOP réarmé':
        'STOP released',
    "{p} est le port USB natif de la pédale : le flashage par ce port échoue en général. Branche le câble sur le "
    "port UART (puce CH343) et choisis ce port-là. Essayer quand même ?":
        "{p} is the pedal's native USB port: flashing through it usually fails. Plug the cable into the UART port "
        "(CH343 chip) and pick that port. Try anyway?",
}
