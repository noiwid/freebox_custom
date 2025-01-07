# Freebox Custom Integration for Home Assistant

[![Release](https://img.shields.io/github/v/release/noiwid/freebox_custom)](https://github.com/noiwid/freebox_custom/releases)

Une intégration personnalisée pour [Home Assistant](https://www.home-assistant.io) permettant de gérer les équipements connectés de la Freebox Delta (v7), et du pack sécurité optionnel :

- **Volets roulants Somfy RTS** (configuration préalable via l'application Freebox requise)
- **Alarme Freebox** et ses capteurs (mouvements, ouvertures de portes, etc.)
- **Composants liés au pack sécurité** (caméras, détecteurs de mouvement et d'ouverture)
- **Device tracker** : visibilité sur les différents appareils connectés à la box et leur statut (home/away).
- **Monitoring hardware** : accès aux informations matérielles de la Freebox, notamment :
  - Température des composants internes (CPU, disque dur, etc.).
  - Utilisation des ressources (CPU, RAM).
  - Statut du stockage interne et externe.

Cette intégration inclut un **patch compatible avec Home Assistant 2025.1.0**.

## Fonctionnalités

- Contrôle des volets roulants via Home Assistant.
- Gestion de l'alarme et des capteurs connectés (mouvements, ouvertures).
- Correction des erreurs liées aux mises à jour récentes de Home Assistant.
- Prise en charge des certificats SSL configurés dans l'interface Freebox.

## Installation

1. Clonez ou téléchargez ce dépôt.
2. Placez les fichiers dans le répertoire suivant de votre instance Home Assistant : **custom_components/freebox/**
3. Redémarrez Home Assistant.
4. Ajoutez l'intégration Freebox via l'interface de configuration :
- Lors de la configuration, saisissez un domaine personnalisé (préalablement configuré dans l'interface Freebox via Paramètres > Nom de domaine, avec un certificat SSL valide) et le port HTTPS associé.
- Relancez le processus d'authentification (appuyez sur la façade de la Freebox pour accepter).
- Configurez les autorisations dans l'interface Freebox :  
  `Paramètres > Gestion des accès` :
  - Gestion de l’alarme et maison connectée
  - Accès aux caméras
  - Contrôle du Freebox Player
  - Provisionnement des équipements
5. Vérifiez que toutes les entités (volets, alarme, capteurs) sont correctement remontées.

## Dépendances

- Une Freebox compatible avec l'API (Freebox Delta ou Freebox Révolution).
- Les volets ou autres équipements doivent être configurés via l’application Freebox avant d’être intégrés à Home Assistant.

## Limitations

- **Certificat SSL** : Si vous utilisez un sous-domaine `xxxx.freeboxos.fr` avec un certificat SSL auto-signé, l'intégration peut échouer. Pour éviter ce problème, configurez un sous-domaine avec un certificat SSL valide dans `Paramètres > Nom de domaine` de l'interface Freebox. 

## Support

Ce projet est maintenu de manière communautaire. Si vous rencontrez un problème ou avez des questions, vous pouvez ouvrir une issue ou participer aux discussions existantes. Les utilisateurs sont libres d'interagir entre eux pour partager des solutions ou des conseils.

---
## À propos
Cette intégration se réponse sur le travail réalisé par [Quentame](https://github.com/Quentame) & [gvigroux](https://github.com/gvigroux) sur une version précédente de l'intégratoin dont le dépôt ne semble plus disponible. Elle inclut des correctifs et des mises à jour pour assurer la compatibilité avec la dernière version de Home Assistant (2025.1.0).

**Auteur :** [noiwid](https://github.com/noiwid)

**Contributions bienvenues !**
