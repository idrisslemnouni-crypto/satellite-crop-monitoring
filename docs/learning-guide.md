# Comprendre le projet

Le problème est de comparer les mêmes lieux à plusieurs dates. Une médiane peut changer simplement parce que les nuages ont masqué d'autres pixels. L'intersection des masques évite ce biais de support ; elle réduit en contrepartie la surface disponible.

Un pixel contient un nombre numérique, pas toujours une réflectance directement exploitable. Ici réflectance = DN × 0,0001 − 0,1, selon STAC. SAVI contient une constante 0,5 : utiliser des DN bruts change donc le sens du calcul. Le test DN=1000 a détecté une petite erreur d'arrondi ; la conversion utilise maintenant float64 avant stockage float32.

Le SWIR et SCL sont à 20 m. Mettre toutes les bandes sur une grille à 20 m évite de promettre une précision à 10 m inexistante. Bilinéaire pour les valeurs continues, voisin le plus proche pour les classes : interpoler une classe de nuage créerait un code sans sens.

NDVI mesure un contraste spectral lié à la végétation ; NDMI est sensible à l'eau et à d'autres facteurs. Une baisse ne démontre pas un stress hydrique. NDWI McFeeters et NDMI utilisent des bandes différentes. Le masque SCL admet végétation, sols et eau : cette étude décrit un paysage, pas une culture identifiée.

Pour apprendre : refaire un calcul NDVI à la main, lire le CRS d'un GeoTIFF, comparer les médianes sur masque propre et commun, puis expliquer pourquoi la zone ombrée d'un graphique représente des différences spatiales plutôt qu'une incertitude statistique. L'alternative serait une composition mensuelle et une validation terrain, qui exigent plus de données et une autre question scientifique.
