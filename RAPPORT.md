# Rapport technique — Yalta Chess

---

## 1. Présentation du problème

### 1.1 Le jeu Yalta

Yalta Chess est une variante du jeu d'échecs à **trois joueurs** jouée sur un plateau hexagonal.
Le plateau est composé de **96 cases** réparties en **6 sextants** de 4×4 cases disposés autour
d'un centre commun. Les trois couleurs sont **blanc** (*white*), **rouge** (*red*) et **noir**
(*black*). Chaque joueur dispose d'un jeu complet : roi, dame, 2 tours, 2 fous, 2 cavaliers et
8 pions.

### 1.2 Notation algébrique

Les colonnes sont notées **a–l** (12 colonnes) et les rangées **1–12**. Les coordonnées internes
sont `(x, y)` où `x` est l'index de colonne (0–11) et `y` l'index de rangée (0–11). Seules les
96 cases appartenant aux 6 sextants sont valides (`VALID_SQUARES`).

### 1.3 Défi central : la topologie

La difficulté principale est que les 6 sextants sont physiquement **tournés ou transposés** les
uns par rapport aux autres. Les directions cardinales abstraites N/E/S/W doivent être
**cohérentes à travers toutes les frontières de sextants** pour que les pièces se déplacent
correctement. Cette contrainte a nécessité une conception spécifique (BFS d'étiquetage) décrite
à la section 4.1.

---

## 2. Architecture générale — Patron MVC + Observer

Le projet suit le patron **Modèle–Vue–Contrôleur** complété par le patron **Observer**.

```
main.py
  └── GameController               (Contrôleur)
        ├── Game                   (Modèle — orchestration)
        │    ├── Board             (Modèle — état du plateau)
        │    │    └── Piece*       (Modèle — pièces)
        │    └── Player*           (Modèle — joueurs)
        └── BoardView              (Vue — affichage Pygame)
              └── Observer de Game (via update(game))
```

**Séparation des responsabilités**

| Couche | Fichiers | Rôle |
|--------|----------|------|
| Modèle | `topology.py`, `board.py`, `game.py`, `piece.py`, `pieces/`, `player.py`, `ai.py` | État, règles, IA |
| Vue | `view/board_view.py` | Rendu Pygame, hit-testing |
| Contrôleur | `controller/game_controller.py` | Boucle de jeu, événements, tick IA |

La vue est enregistrée comme observateur de `Game` via `game.add_observer(view)`. Après chaque
coup (`game.apply_move`), `game.notify()` appelle `view.update(game)` pour redessiner le plateau.

**Point d'entrée (`main.py`)**

```python
players = [
    AIPlayer("red",   depth=4),
    AIPlayer("black", depth=2),
    AIPlayer("white", depth=2),
]
controller = GameController(players)
controller.run()
```

La configuration des joueurs (humain / IA, profondeur de recherche) se fait uniquement dans
`main.py`, sans modifier le reste du code.

---

## 3. Diagramme de classes commenté

```
┌───────────────────────────────────────────────────────────────────────┐
│                       topology.py  (module statique)                  │
│                                                                       │
│  POLYGONS         dict[sq → 4 points]    géométrie physique           │
│  EDGE_NEIGHBOR    dict[sq → {N,E,S,W → sq|None}]  voisins cardinaux  │
│  VERTEX_CLASS     dict[(sq,corner) → frozenset]    classes de coins   │
│  KNIGHT_TARGETS   dict[sq → frozenset]             cibles du cavalier │
│  PAWN_FORWARD     dict[sq → direction]             direction des pions│
│  HUB_CORNERS      6 coins du centre (fous)                            │
│                                                                       │
│  rook_ray(sq, dir, blocked)     → générateur de cases                 │
│  bishop_ray(sq, corner, blocked)→ générateur de cases                 │
│  bishop_first_step / bishop_step                                      │
└───────────────────────────────────────────────────────────────────────┘
           ▲ importé par Board, Piece, Pawn, King, …

┌──────────────────────────┐      ┌─────────────────────────────────────┐
│         Board            │      │              Game                   │
│ ──────────────────────── │      │ ───────────────────────────────     │
│ squares: dict[sq→Piece]  │◄─────│ board: Board                        │
│ en_passant: tuple|None   │      │ players: list[Player]               │
│                          │      │ current_index: int                  │
│ apply_move(piece, dest)  │      │ current_player: Player              │
│ _apply_castle(king, dest)│      │ winner: Player|None                 │
│ is_king_in_check(color)  │      │ loser: Player|None                  │
│ move_leaves_king_in_check│      │ _observers: list                    │
│ clone() → Board          │      │                                     │
│ get_pieces(color) → list │      │ apply_move(piece, dest)             │
│ _setup()                 │      │ _en_passant_after(…)                │
└──────────────────────────┘      │ _check_mate(mover)                  │
                                   │ next_turn()                         │
                                   │ is_over() → bool                   │
                                   │ add_observer(obs) / notify()        │
                                   └─────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                    Piece  (ABC)                       │
│ ──────────────────────────────────────────────────── │
│ color: str                                           │
│ position: str                                        │
│ has_moved: bool                                      │
│ value: int                                           │
│                                                      │
│ get_potential_moves(board) → list   [abstrait]       │
│ get_legal_moves(board) → list                        │
│   └─ filtre via move_leaves_king_in_check            │
│ get_symbol() → str                  [abstrait]       │
│ clone() → Piece                     [abstrait]       │
│ is_enemy(other) → bool                               │
└──────────────────────────────────────────────────────┘
    ▲ héritée par :
    │
    ├── Pawn      forward_dir, update_forward_dir(), can_promote()
    ├── Rook      rook_ray × 4 directions
    ├── Bishop    bishop_ray × 4 coins
    ├── Queen     rook_ray + bishop_ray (inlinés, pas d'objets temporaires)
    ├── Knight    KNIGHT_TARGETS[position]
    └── King      _one_step_squares(), _castling_squares(), _find_rook(),
                  _is_attacked(), is_checkmate()

┌──────────────────────────────────┐
│         Player  (ABC)            │
│  color: str                      │
│  is_eliminated: bool             │
│  choose_move(board) [abstrait]   │
└──────────────────────────────────┘
    ▲
    ├── HumanPlayer   (choose_move retourne None — le contrôleur gère les clics)
    └── AIPlayer      depth: int
                      _thread: MinimaxThread|None
                      start_thinking(board, player_order)
                      is_thinking() → bool
                      get_result() → (src, dest)|None

┌──────────────────────────────────┐
│      MinimaxThread (Thread)      │
│  board (snapshot cloné)          │
│  ai_color, depth, player_order   │
│  result: (src, dest)|None        │
│  run() → best_move(…)            │
└──────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                  GameController                       │
│  game: Game                                          │
│  view: BoardView                                     │
│  selected_piece: Piece|None                          │
│  legal_moves: list                                   │
│  ep_moves: set       (en passant)                    │
│  castle_moves: set   (roque)                         │
│  _ai_started: bool                                   │
│                                                      │
│  run()                                               │
│  _handle_click(pos)                                  │
│  _select(piece) / _deselect()                        │
│  _classify_moves(piece) → (ep_moves, castle_moves)   │
│  _tick_ai()                                          │
│  _checked_kings() → set                              │
│  _show_winner()                                      │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                   BoardView                           │
│  window: pygame.Surface                              │
│  sprites: dict[(color,symbol) → Surface]             │
│  polygons: dict[sq → {points, center}]               │
│  _sq_colors: dict[sq → RGB]                          │
│  _labels: dict[sq → Surface]   (pré-rendus)          │
│  _shapely: dict                (cache lazy)           │
│                                                      │
│  draw(board, highlights, selected, …)                │
│  square_at(mouse_pos) → sq|None                      │
│  update(game)   [interface Observer]                 │
└──────────────────────────────────────────────────────┘
```

### Relations principales

- `Game` agrège `Board` et `list[Player]`
- `Board` agrège `dict[sq → Piece]`
- `GameController` agrège `Game` et `BoardView`
- `BoardView` est observateur de `Game` (interface informelle via `update(game)`)
- `AIPlayer` délègue le calcul à `MinimaxThread`
- Toutes les pièces héritent de la classe abstraite `Piece`

---

## 4. Fonctionnalités développées

### 4.1 Topologie du plateau (`model/topology.py`)

C'est le module le plus complexe du projet. Il produit des structures statiques calculées
**une seule fois** au démarrage, puis utilisées par toutes les pièces et par la vue.

**Géométrie physique.**
`_compute_polygons()` calcule les 4 sommets réels de chaque case par des formules
trigonométriques. Ces polygones sont exportés comme `POLYGONS` et réutilisés par la vue —
aucune duplication de calcul.

**Étiquetage des arêtes par BFS.**
Chaque arête est identifiée par une paire de points physiques arrondis (`_edge_key`). Un BFS
part d'une case fixe (`"a1"`) et propage les labels N/E/S/W de façon cohérente :

1. La fonction `_classify_edges(pts)` attribue des labels bruts depuis la géométrie (angle du
   vecteur centre → milieu d'arête).
2. La fonction `_make_valid_seed()` corrige la case de départ pour garantir les invariants
   (paires opposées N↔S, E↔W ; les deux axes distincts).
3. La fonction `_reorient(geom, edge_index, target_label)` réoriente **atomiquement** les 4
   labels d'une case (échange NS/EW + inversion) pour satisfaire la contrainte de voisinage
   sans créer de doublons.

**Résultat.** `EDGE_NEIGHBOR[sq][d]` donne le voisin dans la direction `d` depuis `sq`, avec
`None` en bordure. C'est la brique fondamentale du déplacement de toutes les pièces linéaires.

**Mouvement de la tour (`rook_ray`).**
Générateur qui suit une direction en recalculant à chaque étape la direction de sortie depuis
l'arête d'entrée — nécessaire aux frontières de sextants où l'orientation change.

**Mouvement du fou (`bishop_ray`, `VERTEX_CLASS`).**
Les coins partagés physiquement entre cases sont regroupés en classes d'équivalence par un
algorithme Union-Find. Le centre du plateau est un hub de 6 coins formant 2 triangles alternés
(`{S1,S3,S5}` et `{S2,S4,S6}`), ce qui donne au fou deux chemins possibles en traversant le
centre. `bishop_ray` explore ces deux branches via une frontière BFS.

**Cavalier (`KNIGHT_TARGETS`).**
Cibles précalculées = (rook + bishop) ∪ (bishop + rook), moins les cases adjacentes directes.

**Direction des pions (`PAWN_FORWARD`).**
Initialisée depuis les rangées de départ (3 rangées selon la couleur), puis propagée par BFS
sur tout le plateau en recalculant la direction de sortie depuis l'arête d'entrée à chaque
franchissement de frontière.

### 4.2 Hiérarchie des pièces (`model/pieces/`)

La classe abstraite `Piece` impose le contrat suivant à toutes les pièces :

```
get_potential_moves(board) → list   # coups sans vérification du roi
get_legal_moves(board) → list       # filtre via move_leaves_king_in_check
get_symbol() → str
clone() → Piece
```

`get_legal_moves` est implémentée dans `Piece` : elle itère sur les coups potentiels et rejette
ceux qui laisseraient le propre roi en échec (via un clone du plateau).

| Pièce  | Valeur | Logique principale |
|--------|--------|--------------------|
| Pawn   | 1      | 1 pas, 2 pas (premier coup), captures diagonales, en passant, promotion |
| Rook   | 5      | `rook_ray` × 4 directions |
| Bishop | 3      | `bishop_ray` × 4 coins |
| Queen  | 9      | `rook_ray` + `bishop_ray` inlinés (pas d'objets temporaires) |
| Knight | 3      | Lookup `KNIGHT_TARGETS[sq]` |
| King   | 1000   | 1 pas (rook + bishop), roque, détection d'échec |

### 4.3 Prise en passant

**Règle.** Un pion latéralement adjacent à un pion adverse ayant avancé de deux cases peut le
capturer immédiatement en se plaçant sur la case sautée.

**Implémentation en 4 étapes :**

1. Après chaque coup, `Game._en_passant_after()` vérifie que le pion a avancé de deux cases en
   contrôlant `EDGE_NEIGHBOR[skipped][OPPOSITE_DIR[fwd]] == src` (la case derrière la case
   sautée est bien la case de départ). Elle stocke `board.en_passant = (skipped_sq, pawn_sq)`.

2. `Pawn.get_potential_moves()` ajoute `ep_target` si un voisin latéral de la pièce est le
   pion cible en passant.

3. `Board.apply_move()` supprime le pion capturé (`squares[ep_pawn_sq] = None`) lorsque la
   destination est la case en passant.

4. Le contrôleur surligne la case en passant en **rose** (`HIGHLIGHT_EP`), distinguée
   visuellement des coups normaux (vert).

### 4.4 Roque

**Règle.** Le roi n'a pas bougé, n'est pas en échec, les cases intermédiaires sont libres et
non attaquées, et une tour alliée non bougée existe dans la direction.

**Implémentation :**

1. `King._castling_squares()` vérifie les 4 directions cardinales : les 2 cases libres devant
   le roi, l'existence d'une tour alliée non bougée (`_find_rook`), et l'absence d'attaque sur
   le roi, la case intermédiaire et la case de destination (`_is_attacked`).

2. `King._is_attacked(board, sq)` consulte les coups potentiels de chaque pièce ennemie. Les
   rois ennemis sont traités **directement** (portée à 1 pas dans 4 directions + 4 diagonales)
   pour éviter une récursion infinie.

3. `Board._apply_castle()` détecte le déplacement de 2 cases du roi et repositionne la tour
   sur la case adjacente au roi côté opposé.

4. Le contrôleur (`_classify_moves`) distingue les cases de roque des coups normaux et les
   surligne en **bleu** (`HIGHLIGHT_CASTLE`).

### 4.5 Promotion automatique

Quand un pion n'a plus de case devant lui
(`EDGE_NEIGHBOR[pos][fwd] is None`), il est automatiquement remplacé par une Dame dans
`Board.apply_move()`. `Pawn.update_forward_dir(src)` recalcule la direction forward après
chaque déplacement en cherchant l'arête d'entrée dans la nouvelle case — indispensable aux
franchissements de frontières de sextants.

### 4.6 Gestion des échecs et mat

- `Board.is_king_in_check(color)` : vérifie qu'au moins une pièce ennemie peut atteindre la
  case du roi via ses coups potentiels.
- `Board.move_leaves_king_in_check(piece, dest)` : clone le plateau, applique le coup, vérifie
  l'échec — c'est le filtre utilisé par `get_legal_moves`.
- `King.is_checkmate(board)` : le roi est en échec **et** aucune pièce alliée n'a de coup légal.
- En fin de tour, `Game._check_mate(mover)` vérifie si un adversaire est en état de mat.

Les rois en échec sont surlignés en **rouge** dans la vue.

### 4.7 Intelligence artificielle (`model/ai.py`, `model/player.py`)

**Algorithme.** Minimax à 3 joueurs avec élagage alpha-bêta :
- Le joueur IA est le nœud MAX ; les deux autres joueurs sont des nœuds MIN.
- Profondeur configurable par joueur (ex. `depth=4` pour rouge, `depth=2` pour noir et blanc).
- Fonction d'évaluation : somme des valeurs des pièces alliées moins somme des valeurs de
  toutes les pièces ennemies.

**Exécution asynchrone.** `AIPlayer.start_thinking()` lance `MinimaxThread` (thread daemon) qui
travaille sur un **clone isolé** du plateau (`board.clone()`). Le contrôleur interroge
`is_thinking()` et `get_result()` à chaque frame (60 fps) — l'interface reste fluide pendant le
calcul. Une fois le résultat disponible, `_tick_ai()` applique le coup via `game.apply_move`.

**Ordre des joueurs.** `GameController._player_order()` construit la liste des couleurs en ordre
de jeu à partir du joueur courant, transmise à `MinimaxThread` pour que le minimax tourne dans
le bon ordre de tours.

### 4.8 Vue et interface (`view/board_view.py`)

- **`BoardView`** dessine les 96 polygones avec Pygame en utilisant `POLYGONS` importé depuis
  `topology.py` — aucune duplication du calcul géométrique.
- **Surlignages distincts** :
  - Vert : coups légaux normaux
  - Jaune : pièce sélectionnée
  - Rose : prise en passant (`HIGHLIGHT_EP`)
  - Bleu : roque (`HIGHLIGHT_CASTLE`)
  - Rouge : roi en échec (`CHECK_COLOR`)
- **Labels de cases** (`a1`–`l12`) pré-rendus une fois à l'initialisation en `Surface` Pygame
  (`_prerender_labels`), évitant un rendu de police à chaque frame.
- **Hit-testing** via Shapely (`shapely.geometry.Polygon.contains`) pour convertir un clic
  souris en case algébrique. Les polygones Shapely sont construits **lazily** lors du premier
  clic (`_get_shapely()`), sans ralentir le démarrage.
- **Sprites** : images PNG 42×42 px chargées pour chaque combinaison (couleur × type de pièce).

---

## 5. Difficultés rencontrées

### 5.1 Étiquetage cohérent des arêtes (problème principal)

**Problème.** La première version assignait les labels N/E/S/W depuis la géométrie brute (angle
du vecteur centre → milieu d'arête). Aux frontières de sextants, deux cases adjacentes
recevaient des labels contradictoires : l'arête Nord d'une case ne pointait pas vers le voisin
attendu.

**Solution.** Réécriture complète de l'étiquetage par BFS partant de `"a1"`. La clé est la
fonction `_reorient()` qui recalcule les 4 labels d'une case en une seule opération atomique
(échange d'axe NS/EW + inversion) plutôt que de corriger une seule arête, évitant tout doublon
ou incohérence de paires opposées.

### 5.2 Labels de coins incohérents avec le BFS

**Problème.** `_CORNER_LABEL` était dérivé des labels géométriques bruts, pas des labels BFS
corrigés. Les coins aux frontières de sextants ne correspondaient plus aux directions réelles,
rendant le mouvement du fou erroné.

**Solution.** Recalcul de `_CORNER_LABEL` **après** le BFS, à partir de `_edge_labels` (BFS).
Chaque coin est identifié par la combinaison des deux arêtes adjacentes corrigées.

### 5.3 Direction des pions aux frontières de sextants

**Problème.** Le pion conservait sa direction initiale même après avoir traversé une frontière
de sextant — il proposait alors des cases incorrectes ou ne pouvait plus avancer.

**Solution.** `Pawn.update_forward_dir(src)` est appelé après chaque déplacement dans
`Board.apply_move`. Il cherche quelle direction du nouveau plateau mène à la case d'origine
(`src`) et en déduit la nouvelle direction forward : `OPPOSITE_DIR[entry]`.

### 5.4 Récursion infinie dans le roque

**Problème.** `King._is_attacked()` appelait `p.get_potential_moves(board)` sur les rois
ennemis, lesquels appelaient `_castling_squares()`, qui rappelait `_is_attacked()` → boucle
infinie.

**Solution.** Dans `_is_attacked()`, les rois ennemis sont traités séparément : leur portée est
calculée directement (1 pas en NESW + 4 coins diagonaux) sans passer par `get_potential_moves`.

### 5.5 Faux positifs en passant

**Problème.** La détection du double avancement ne vérifiait que `was_first_move` et l'absence
de pièce sur la case sautée. Un pion faisant une capture diagonale à son premier coup passait
aussi le test.

**Solution.** Ajout de la vérification
`EDGE_NEIGHBOR[skipped][OPPOSITE_DIR[fwd]] == src` : la case derrière la case sautée doit être
exactement la case de départ, confirmant une avance strictement linéaire sur 2 cases.

### 5.6 BFS non déterministe

**Problème.** `next(iter(VALID_SQUARES))` sur un `frozenset` donne une case différente selon
l'exécution Python (ordre de hachage non garanti) → labels différents d'une run à l'autre.

**Solution.** La case de départ du BFS est fixée à `"a1"` — cas de coin simple avec 2 voisins
connus, ce qui facilite aussi la validation manuelle.

---

## 6. Améliorations possibles

### 6.1 Règles des échecs à 3 joueurs

Actuellement, la partie s'arrête dès qu'un roi est maté. Une règle plus complète éliminerait
le joueur maté et laisserait les deux survivants continuer. Il faudrait aussi décider si les
pièces du joueur éliminé restent en place ou disparaissent.

### 6.2 Choix de promotion

La promotion est automatique en dame. Une fenêtre modale Pygame pourrait proposer le choix
(tour, fou, cavalier, dame) avec des sprites cliquables.

### 6.3 Performances de l'IA

- **Table de transposition** : `get_legal_moves` clone le plateau pour chaque coup candidat ;
  une table de hachage des positions éviterait de réévaluer les états déjà visités.
- **Tri des coups** : trier les captures en premier augmente le taux d'élagage alpha-bêta.
- **Évaluation positionnelle** : bonus pour le contrôle du centre, la mobilité, la sécurité du
  roi — actuellement seul le matériel est évalué.
- **Détection incrémentale des échecs** : recalculer uniquement ce qui change plutôt que de
  tout cloner à chaque nœud.

### 6.4 Interface utilisateur

- Afficher un historique des coups en notation algébrique.
- Permettre l'annulation d'un coup (undo) avec une pile d'états clonés.
- Ajouter un menu de configuration des joueurs (humain / IA, profondeur) sans modifier `main.py`.
- Timer par joueur.

### 6.5 Réseau / multijoueur

Séparer le modèle du transport permettrait de jouer en réseau (TCP ou WebSocket) avec le
contrôleur côté client recevant des événements de coups sérialisés.

### 6.6 Tests automatisés

La logique de topologie et de mouvement est complexe. Une suite de tests unitaires (pytest) sur
`EDGE_NEIGHBOR`, `rook_ray`, `bishop_ray`, les règles spéciales (roque, en passant, promotion)
et la détection du mat garantirait la non-régression lors d'évolutions futures.

---

## 7. Structure des fichiers

```
yalta/
├── main.py                      Point d'entrée ; configure les joueurs
├── controller/
│   └── game_controller.py       Boucle de jeu, événements souris, tick IA
├── model/
│   ├── topology.py              Topologie statique (BFS, polygones, graphes)
│   ├── board.py                 État du plateau, application des coups
│   ├── game.py                  Orchestration, en passant, mat, observateurs
│   ├── piece.py                 Classe de base abstraite Piece
│   ├── player.py                HumanPlayer, AIPlayer
│   ├── ai.py                    Minimax, MinimaxThread
│   └── pieces/
│       ├── pawn.py
│       ├── rook.py
│       ├── bishop.py
│       ├── knight.py
│       ├── queen.py
│       └── king.py
├── view/
│   └── board_view.py            Rendu Pygame + hit-testing Shapely
└── assets/
    └── pieces/                  Sprites PNG (white/black/red × 6 pièces)
```

---

## 8. Dépendances

| Bibliothèque | Usage |
|---|---|
| `pygame` | Rendu graphique, événements souris, sprites |
| `shapely` | Hit-testing pixel → case algébrique |
| `threading` | IA asynchrone (MinimaxThread) |
| `math` | Calcul des polygones (cos, sin, atan2, sqrt) |
| `collections` | `defaultdict` dans `topology.py` |
| `abc` | Classe abstraite `Piece` et `Player` |
