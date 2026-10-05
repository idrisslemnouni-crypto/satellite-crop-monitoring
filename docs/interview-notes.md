# Préparation entretien

Problème : comparer sept scènes Sentinel-2 réelles sur un paysage agricole de l'Iowa en 2024. Pipeline : STAC figé, lecture COG publique, grille 20 m, calibration, masque qualité, indices, intersection spatiale, cartes et séries. Il n'y a pas de modèle prédictif ni de référence terrain ; les résultats sont des valeurs observées calculées, pas une accuracy.

1. **Pourquoi Sentinel-2 L2A ?** Réflectance de surface et classification de scène disponibles dans une source publique documentée.
2. **Pourquoi 20 m ?** Respecter la résolution des bandes SWIR et SCL, et aligner toutes les dates.
3. **Pourquoi l'offset ?** Les métadonnées imposent −0,1 ; l'ignorer fausse les ratios et SAVI.
4. **Quelle erreur a été rencontrée ?** Une soustraction float32 masquait une réflectance théoriquement nulle ; un test numérique l'a détectée.
5. **Comment traiter les nuages ?** Conserver SCL 4/5/6 et exclure les autres classes ; ce masque a ses propres erreurs.
6. **Pourquoi un masque commun ?** Comparer les mêmes pixels plutôt que confondre changement du paysage et changement de couverture.
7. **NDWI et NDMI sont-ils identiques ?** Non : NDWI McFeeters utilise green/NIR, NDMI NIR/SWIR1.
8. **Peut-on diagnostiquer un stress ?** Non sans observations indépendantes, espèce, stade et conditions locales.
9. **Que représente le ruban des courbes ?** Les quantiles spatiaux 10–90%, pas des intervalles de confiance.
10. **Comment améliorer l'étude ?** Ajouter parcelles et cultures labellisées, observations plus fréquentes, années indépendantes et mesures terrain.

Limites : paysage mixte, sept dates, nuages mal classés possibles et resampling aux frontières. Assistance IA déclarée ; savoir refaire les calculs et expliquer les choix avant candidature.
