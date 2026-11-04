# Freebox Custom Integration for Home Assistant

[![Release](https://img.shields.io/github/v/release/noiwid/freebox_custom)](https://github.com/noiwid/freebox_custom/releases)

L'intégration **Freebox officielle** de Home Assistant, avec ce qui lui manque encore pour la Freebox Delta (v7) et son pack sécurité :

- **Volets roulants RTS** (`cover`) : monter, descendre, stop. Les volets doivent d'abord être appairés dans l'application Freebox Home.
- **Volets IO, stores et portes de garage** (`cover`, catégories `shutter` et `opener`) : avec position. Code repris de la version 2025.01, pas encore retesté sur ce matériel : ouvrez une issue si quelque chose cloche.
- **Détecteur de mouvement réactif** : la Freebox ne pousse pas les détections, l'intégration officielle ne les lit qu'au rythme de sa mise à jour générale. Ici le détecteur est interrogé toutes les 2 secondes.

Tout le reste vient de l'intégration officielle, sans modification : alarme, détecteurs d'ouverture et de mouvement, caméras, suivi des appareils du réseau, débits, températures, ventilateurs, disques, Wi-Fi, appels manqués, redémarrage de la box.

**Version actuelle : 2026.10.4.1**, basée sur l'intégration officielle de Home Assistant 2026.10.4 (`freebox-api` 1.3.1).

## Installation

1. Copiez les fichiers de ce dépôt dans `custom_components/freebox/` de votre Home Assistant.
2. Redémarrez Home Assistant. Le dossier remplace l'intégration officielle Freebox, qui porte le même nom.
3. Si la Freebox n'est pas encore configurée : Paramètres > Appareils et services > Ajouter une intégration > Freebox, puis appuyez sur la flèche droite de la box pour valider.
4. Dans Freebox OS, `Paramètres > Gestion des accès`, donnez à l'application Home Assistant les droits « Gestion de l'alarme et maison connectée », « Accès aux caméras » et « Provisionnement des équipements ».

### Venir de l'ancienne version (2025.01)

L'ancienne version de ce dépôt reposait sur un fork de 2020 de l'intégration. La nouvelle repart de la version officielle à jour :

- les identifiants d'entités (`cover.volet_salon`, `alarm_control_panel.…`) sont conservés ;
- remplacez simplement le contenu de `custom_components/freebox/` puis redémarrez ;
- l'option « use_home_api » disparaît : les équipements Freebox Home sont toujours chargés quand les droits sont donnés.

## Limitations

- **Pas de position pour les volets RTS** : le protocole RTS n'envoie aucun retour. Home Assistant connaît le dernier ordre envoyé, pas la position réelle du volet.
- **À chaque mise à jour de Home Assistant**, ce dossier continue de remplacer l'intégration officielle. Une nouvelle version de ce dépôt suit les versions de Home Assistant qui modifient l'intégration Freebox.
- Les volets sont proposés à l'intégration officielle (PR [home-assistant/core#188666](https://github.com/home-assistant/core/pull/188666)). Une fois fusionnée, ce dépôt ne servira plus qu'au détecteur de mouvement.

## Fichiers modifiés par rapport à l'intégration officielle

| Fichier | Changement |
|---|---|
| `cover.py` | Nouveau : volets RTS (`basic_shutter`), volets IO (`shutter`), stores et portes de garage (`opener`) |
| `const.py` | Catégories `SHUTTER`, `IO_SHUTTER`, `OPENER` chargées, plateforme `cover` ajoutée |
| `entity.py` | `set_home_endpoint_value` accepte une position (entier) |
| `binary_sensor.py` | Détecteur de mouvement interrogé toutes les 2 s |
| `manifest.json` | Champ `version` requis pour une intégration personnalisée |
| `translations/` | `en.json` et `fr.json` (les traductions de l'officielle ne sont pas reprises automatiquement) |

## Support

Ouvrez une issue sur ce dépôt.

---

Basé sur l'intégration Freebox de Home Assistant, de [Quentame](https://github.com/Quentame) et des contributeurs [hacf-fr](https://github.com/hacf-fr), et sur le travail de [gvigroux](https://github.com/gvigroux) pour les volets.

**Auteur :** [noiwid](https://github.com/noiwid)
