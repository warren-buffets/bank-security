# Grille d'evaluation - Soutenance Etape 2 - MVP & Pilotage Projet

## Rappel des livrables pour cette soutenance

1. Presentation groupe devant intervenants. (10 min)
    - Presentation des eventuels nouveaux elements techniques.
    - Presentation de l'outil de gestion de taches et le choix de methodologie.
    - Presentation technique et fonctionelle du **MVP** a son niveau d'avancement actuel.
    - Presentation du code source du projet (Git repo).
    - Un **rapport de pilotage de projet**. (burndown, blocages, decisions)
    - Support libre : PowerPoint, Canva, démo live

## Deroulement de la soutenance

Pour chaque groupe, successivement : 
- **10 minutes de présentation**
- **5 min de Q/R**

## Rappel Barème

- Pertinence des choix techniques (15%)
- Qualite de l'implementation (50%)
- Travail en equipe (15%)
- Clarté & support visuel (20%)

## Grille d'evaluation

Caveats :
- Nous avons parfaitement conscience que pour la plupart des eleves, tous ces points ne pourront pas necessairement etre atteinds au 29 Janvier. Mais ca laisse une marge pour pouvoir noter les top-performers.
- Nous n'attendons pas un projet qui soit fini de bout en bout, ceci sera pour l'Etape 3/la soutenance finale en Avril. Ici nous attendons le projet dans son etat d'avancement actuel (debuts), mais avec toute la rigueur qui va avec. Vous ne devriez pas attendre d'avoir fini l'implementation pour documenter, tester, piloter. Cela doit vivre avec l'implementation.
- Vous n'aurez pas le temps de presenter, en 10 minutes, tout ce que vous avez fait. Je vous conseille de vous concentrer, pendant la presentation, sur ce qui necessite l'impact d'une presentation et l'aspect sensoriel (composition de l'equipe, organisation, sujets empathiques, challenges organisationnels...). Et de laisser la documentation technique et le repository, bien brosses, raconter le cheminement et les denouements techniques.
- Please respectez les 10 minutes de temps sur la presentation. On va commencer a severement punir les depacements (- 10 points). C'est crucial que vous maitrisiez cet aspect en entreprise.


### 1. Pertinence des choix techniques (15 points)

Antoine :
- [ ] Choix de language, de binaires et de librairies pertinents et justifies. (5 pts)
- [ ] Explication du delta entre environement local et un futur environement de prod compris par l'equipe. (ex : choix d'une base PostGre localement, mais utilisation de AWS Aurora en prod) (5 pts)
- [ ] Si pivot depuis l'architecture initiale (definie dans le contrat de livraison), justification. (-2 pts si non justifie)
- [ ] CENSURE (5 pts) (pour eviter que tout soit fait a l'IA et stimuler vos recherches ;))

**Score Antoine** :  / 15


Olivier:
- [ ] Choix de language, de binaires, de modeles, et de librairies pertinents et justifies. (5 pts)
- [ ] Explication du delta entre environement local et un futur environement de prod compris par l'equipe. (ex : choix d'une base PostGre localement, mais utilisation de AWS Aurora en prod) (5 pts)
- [ ] Si pivot depuis l'architecture initiale (definie dans le contrat de livraison), justification. (-2 pts si non justifie)
- [ ] CENSURE (5 pts) (pour eviter que tout soit fait a l'IA et stimuler vos recherches ;))

**Score Olivier** :  / 15


**Score Final (médiane)** :  / 15

**Notes/Commentaires** :
```
Antoine:

Olivier:
```

### 2. Qualite de l'implementation (50 points)

Antoine:
- [ ] Le projet est deployable localement (sur *nix, windows idealement) en 2/3 cmd max, (nous n'enleveront pas de points en cas d'incompatibilite d'archi CPU (e.g : arm vs x86)) (5 pts)
- [ ] Suite de tests logiciel solide (5 pts)
- [ ] Suite de benchmark des modeles ML utilises (5 pts)
TODO (Antoine) : ajouter 5 pts sur un sujet ML 
- [ ] Documentation technique claire (5 pts)
- [ ] CENSURE (5 pts) (pour eviter que tout soit fait a l'IA et stimuler vos recherches ;))
- [ ] Pas de faille de securite evidente (5 pts) 
- [ ] Optimization du code (pas de complexite memoire super-lineaire, ou de complexite temps deconante) (5 pts)
- [ ] BC-compatibility (versionning des APIs, nullables etc) (3 pts)
- [ ] CENSURE (5 pts) (pour eviter que tout soit fait a l'IA et stimuler vos recherches ;))
- [ ] Chiffrement des communications reseaux (self-signed certificates OK) (2 pts)

**Score Antoine** :  / 50

Olivier:
- [ ] Le projet est deployable localement (sur *nix, windows idealement) en 2/3 cmd max, (nous n'enleveront pas de points en cas d'incompatibilite d'archi CPU (e.g : arm vs x86)) (5 pts)
- [ ] Suite de tests logiciel solide (5 pts)
- [ ] Suite de benchmark des modeles ML utilises (5 pts)
TODO (Antoine) : ajouter 5 pts sur un sujet ML 
- [ ] Documentation technique claire (5 pts)
- [ ] CENSURE (5 pts) (pour eviter que tout soit fait a l'IA et stimuler vos recherches ;))
- [ ] Pas de faille de securite evidente (5 pts) 
- [ ] Optimization du code (pas de complexite memoire super-lineaire, ou de complexite temps deconante) (5 pts)
- [ ] BC-compatibility (versionning des APIs, nullables etc) (3 pts)
- [ ] CENSURE (5 pts) (pour eviter que tout soit fait a l'IA et stimuler vos recherches ;))
- [ ] Chiffrement des communications reseaux (self-signed certificates OK) (2 pts)

**Score Olivier** :  / 50


**Score Final (médiane)** :  / 50

**Notes/Commentaires** :
```
Antoine:

Olivier:
```


### 3. Travail en equipe (15 points)

Note : Cette partie peut etre tres dure a evaluer si les groupes n'explicitent pas certains elements (documentation des echanges techniques, explication du deroulement du projet, de l'implication des PMs dans les discussions etc). Ca sera a eux de nous convaincre.

Antoine:
- [ ] Tous les eleves ont mis la main a la patte, soit sur la technique, soit sur la doc, soit sur la presentation, idealement un peu des 3. (7.5 pts)
- [ ] Division du travail pertinente, fonction des appetences et competences. Kudos si vous poussez un des team-members a sortir de sa zone de confort et apprendre de nouvelles competences. (7.5 pts)

**Score Antoine** :  / 15

Olivier:
- [ ] Tous les eleves ont mis la main a la patte, soit sur la technique, soit sur la doc, soit sur la presentation, idealement un peu des 3. (7.5 pts)
- [ ] Division du travail pertinente, fonction des appetences et competences. Kudos si vous poussez un des team-members a sortir de sa zone de confort et apprendre de nouvelles competences. (7.5 pts)

**Score Olivier** :  / 15


**Score Final (médiane)** :  / 15

**Notes/Commentaires** :
```
Antoine:

Olivier:
```

### 4. Clarte et support visuel (20 points)


Antoine:
- [ ] Le backlog est structure et a jour (5 pts)
- [ ] Le rapport de pilotage est fluide et convaincant (5 pts)
- [ ] La documentation fonctionnelle est claire (5 pts)
- [ ] Les echanges et debats (technique, produit, operationnel) sont documentes pour une meilleure comprehension des choix passes (5 pts)

**Score Antoine** :  / 20

Olivier:
- [ ] Le backlog est structure et a jour (5 pts)
- [ ] Le rapport de pilotage est fluide et convaincant (5 pts)
- [ ] La documentation fonctionnelle est claire (5 pts)
- [ ] Les echanges et debats (technique, produit, operationnel) sont documentes pour une meilleure comprehension des choix passes (5 pts)

**Score Olivier** :  / 20

**Score Final (médiane)** :  / 20

**Notes/Commentaires** :
```
Antoine:

Olivier:
```



## Score total Antoine :  / 100
## Score total Olivier :  / 100
## Score total Final (médiane) :  / 100