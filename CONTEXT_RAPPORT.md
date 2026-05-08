# Contexte du projet Yalta Chess — Dossier technique

Ce document regroupe l'ensemble des éléments nécessaires à la rédaction d'un rapport technique
sur le projet Yalta Chess : analyse du problème, diagramme de classes commenté, choix de
conception, fonctionnalités développées, difficultés rencontrées et améliorations possibles.

---

## 1. Présentation du problème

### 1.1 Le jeu Yalta

Yalta Chess est une variante du jeu d'échecs à **trois joueurs** jouée sur un plateau hexagonal.
Le plateau est composé de **96 cases** disposées en **6 sextants** de 4×4 cases, répartis autour
d'un centre commun. Les trois couleurs sont **blanc** (White), **rouge** (Red) et **noir** (Black).

Chaque joueur dispose d'un ensemble complet de pièces (roi, dame, 2 tours, 2 fous, 2 cavaliers,
8 pions). Les règles reprennent celles des échecs classiques avec des adaptations liées à la
géométrie hexagonale.

### 1.2 Notation algébrique

Les colonnes sont notées **a–l** (12 colonnes) et les rangées **1–12**.
Les coordonnées internes sont `(x, y)` avec `x` = index de colonne (0–11) et `y` = index de
rangée (0–11). Seules les 96 cases appartenant aux 6 sextants sont valides.

### 1.3 Défi central : la topologie

La difficulté principale du projet est que les cases hexagonales n'ont **pas une orientation
uniforme** : chaque sextant est tourné ou transposé différemment. Les directions cardinales
abstraites N/E/S/W doivent être **cohérentes à travers toutes les frontières de sextants** pour
que le déplacement des pièces soit correct.

---

## 2. Architecture générale — Patron MVC + Observer

Le projet suit le patron **Modèle–Vue–Contrôleur** complété par le patron **Observer** :

```
main.py
  └── GameController          (Contrôleur)
        ├── Game               (Modèle — orchestration)
        │    ├── Board          (Modèle — état du plateau)
        │    │    └── Piece*    (Modèle — pièces)
        │    └── Player*        (Modèle — joueurs)
        └── BoardView          (Vue — affichage Pygame)
              └── Observer de Game
```

- **Modèle** : `topology.py`, `board.py`, `game.py`, `piece.py`, `pieces/`, `player.py`, `ai.py`
- **Vue** : `view/board_view.py`
- **Contrôleur** : `controller/game_controller.py`
- **Point d'entrée** : `main.py`

La vue est enregistrée comme observateur de `Game` via `game.add_observer(view)`.
Après chaque coup (`game.apply_move`), `game.notify()` appelle `view.update(game)` pour
redessiner le plateau.

---

## 3. Diagramme de classes commenté

```
┌───────────────────────────────────────────────────────────────────┐
│                         topology.py (module)                      │
│  Fonctions et constantes statiques — calculées une seule fois     │
│                                                                   │
│  POLYGONS        dict[sq → 4 points]   — géométrie physique       │
│  EDGE_NEIGHBOR   dict[sq → {N,E,S,W → sq|None}]                  │
│  VERTEX_CLASS    dict[(sq,corner) → frozenset]  — fous            │
│  KNIGHT_TARGETS  dict[sq → frozenset]                             │
│  PAWN_FORWARD    dict[sq → direction]                             │
│  HUB_CORNERS     liste des 6 coins du centre (fous)               │
│  rook_ray(sq, dir, blocked)   → générateur de cases               │
│  bishop_ray(sq, corner, blocked) → générateur de cases            │
└───────────────────────────────────────────────────────────────────┘
           ▲ importé par Board, Piece, King, Pawn, …

┌──────────────────────────┐      ┌─────────────────────────────────┐
│         Board            │      │            Game                 │
│ ─────────────────────── │      │ ──────────────────────────────  │
│ squares: dict[sq→Piece]  │◄─────│ board: Board                    │
│ en_passant: tuple|None   │      │ players: list[Player]           │
│                          │      │ current_index: int              │
│ apply_move(piece, dest)  │      │ current_player: Player          │
│ _apply_castle(king,dest) │      │ winner: Player|None             │
│ is_king_in_check(color)  │      │ loser: Player|None              │
│ move_leaves_king_in_check│      │ _observers: list                │
│ clone() → Board          │      │                                 │
│ get_pieces(color) → list │      │ apply_move(piece, dest)         │
│ _setup()                 │      │ _en_passant_after(...)          │
└──────────────────────────┘      │ _check_mate(mover)              │
                                   │ next_turn()                     │
                                   │ is_over() → bool               │
                                   │ add_observer(obs)               │
                                   │ notify()                        │
                                   └─────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                     Piece  (ABC)                     │
│ ──────────────────────────────────────────────────── │
│ color: str                                           │
│ position: str                                        │
│ has_moved: bool                                      │
│ value: int                                           │
│                                                      │
│ get_potential_moves(board) → list   [abstrait]       │
│ get_legal_moves(board) → list                        │
│   └─ filtre via move_leaves_king_in_check            │
│ get_symbol() → str              [abstrait]           │
│ clone() → Piece                 [abstrait]           │
│ is_enemy(other) → bool                               │
└──────────────────────────────────────────────────────┘
    ▲ héritée par :
    │
    ├── Pawn      forward_dir, update_forward_dir, can_promote
    ├── Rook      rook_ray × 4 directions
    ├── Bishop    bishop_ray × 4 coins
    ├── Queen     rook_ray + bishop_ray (inlinés)
    ├── Knight    KNIGHT_TARGETS[position]
    └── King      _one_step_squares, _castling_squares, _is_attacked,
                  is_checkmate

┌──────────────────────────────────┐
│         Player  (ABC)            │
│  color: str                      │
│  choose_move(board) [abstrait]   │
└──────────────────────────────────┘
    ▲
    ├── HumanPlayer   (pas de logique — le contrôleur gère les clics)
    └── AIPlayer      depth: int
                      _thread: MinimaxThread|None
                      start_thinking(board, player_order)
                      is_thinking() → bool
                      get_result() → (src,dest)|None

┌──────────────────────────────────┐
│       MinimaxThread (Thread)     │
│  board (snapshot cloné)          │
│  ai_color, depth, player_order   │
│  result: (src,dest)|None         │
│  run() → best_move(...)          │
└──────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│                 GameController                    │
│  game: Game                                       │
│  view: BoardView                                  │
│  selected_piece: Piece|None                       │
│  legal_moves: list                                │
│  ep_moves: set   (en passant)                     │
│  castle_moves: set                                │
│  _ai_started: bool                                │
│                                                   │
│  run()                                            │
│  _handle_click(pos)                               │
│  _select(piece) / _deselect()                     │
│  _classify_moves(piece) → (ep, castle)            │
│  _tick_ai()                                       │
│  _checked_kings() → set                           │
│  _show_winner()                                   │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│                  BoardView                        │
│  window: pygame.Surface                           │
│  sprites: dict[(color,symbol)→Surface]            │
│  polygons: dict[sq→{points,center}]               │
│  _sq_colors: dict[sq→RGB]                         │
│  _labels: dict[sq→Surface]  (pré-rendus)          │
│  _shapely: dict (cache lazy)                      │
│                                                   │
│  draw(board, highlights, selected, ...)           │
│  square_at(mouse_pos) → sq|None                   │
│  update(game)   [interface Observer]              │
└──────────────────────────────────────────────────┘
```

### Relations principales
- `Game` agrège `Board` et `list[Player]`
- `Board` agrège `dict[sq → Piece]`
- `GameController` agrège `Game` et `BoardView`
- `BoardView` est observateur de `Game` (interface informelle via `update(game)`)
- `AIPlayer` délègue le calcul à `MinimaxThread`
- Toutes les pièces héritent de `Piece` (ABC)

---

## 4. Fonctionnalités développées

### 4.1 Topologie du plateau (`model/topology.py`)

**Géométrie physique.** Les coordonnées réelles des 4 coins de chaque case sont calculées par
des formules trigonométriques dans `_compute_polygons()`. Ces polygones sont exportés comme
`POLYGONS` et réutilisés à la fois par la topologie et la vue — aucune duplication de calcul.

**Étiquetage des arêtes par BFS.** Chaque arête est identifiée par une paire de points physiques
(`_edge_key`). Un BFS part d'une case fixe (`"a1"`) et propage des étiquettes N/E/S/W cohérentes :
- L'arête de sortie d'une case reçoit le label `d` → l'arête d'entrée du voisin reçoit `OPPOSITE_DIR[d]`.
- La fonction `_reorient(geom, edge_index, target_label)` réoriente atomiquement les 4 labels d'une
  case (échange d'axes + inversion) pour satisfaire cette contrainte sans créer de doublons.
- La fonction `_make_valid_seed()` fixe les labels bruts de la case de départ.

**Résultat.** `EDGE_NEIGHBOR[sq][d]` donne le voisin dans la direction `d` pour toute case `sq`,
avec `None` en bordure de plateau.

**Mouvement de la tour** (`rook_ray`). Générateur qui suit une direction en recalculant à chaque
étape la direction de sortie depuis l'arête d'entrée — nécessaire aux frontières de sextants.

**Mouvement du fou** (`bishop_ray`, `VERTEX_CLASS`). Les coins partagés physiquement entre
cases sont regroupés en classes d'équivalence par un algorithme Union-Find. Le centre du plateau
est un hub de 6 coins formant 2 triangles alternés ({S1,S3,S5} et {S2,S4,S6}), ce qui donne au
fou deux chemins possibles en traversant le centre.

**Cavalier** (`KNIGHT_TARGETS`). Cibles précalculées = (rook + bishop) ∪ (bishop + rook), moins
les cases adjacentes.

**Direction des pions** (`PAWN_FORWARD`). Initialisée depuis les rangées de départ puis propagée
par BFS sur tout le plateau, en recalculant la direction de sortie à partir de l'arête d'entrée.

### 4.2 Pièces (`model/pieces/`)

Chaque pièce hérite de `Piece` et implémente :
- `get_potential_moves(board)` : coups sans vérification du roi
- `get_legal_moves(board)` : filtre via `board.move_leaves_king_in_check`
- `get_symbol()`, `clone()`

| Pièce   | Logique principale |
|---------|-------------------|
| Pawn    | 1 pas, 2 pas (premier coup), captures diagonales, en passant, promotion |
| Rook    | `rook_ray` × 4 directions |
| Bishop  | `bishop_ray` × 4 coins |
| Queen   | Rook + Bishop inlinés (pas d'objets temporaires) |
| Knight  | Lookup `KNIGHT_TARGETS[sq]` |
| King    | 1 pas (rook + bishop), roque, détection d'échec |

### 4.3 Prise en passant

**Règle.** Un pion latéralement adjacent au pion adverse ayant avancé de deux cases peut le
capturer immédiatement en se plaçant sur la case sautée.

**Implémentation.**
1. Après chaque coup, `Game._en_passant_after()` détecte un double avancement en vérifiant que
   `EDGE_NEIGHBOR[skipped][OPPOSITE_DIR[fwd]] == src` (l'avance est bien linéaire et double).
   Elle stocke `board.en_passant = (skipped_sq, pawn_sq)`.
2. `Pawn.get_potential_moves()` ajoute `ep_target` si un voisin latéral est le pion cible.
3. `Board.apply_move()` supprime le pion capturé (`squares[ep_pawn_sq] = None`) quand la
   destination est la case en passant.
4. La vue surligne la case en passant en **rose** (`HIGHLIGHT_EP`).

### 4.4 Roque

**Règle.** Le roi n'a pas bougé, n'est pas en échec, les cases intermédiaires sont libres et
non attaquées, et une tour alliée non bougée existe dans la direction.

**Implémentation.**
1. `King._castling_squares()` vérifie les 4 directions cardinales.
2. `King._find_rook()` cherche la première tour alliée non bougée dans une direction.
3. `King._is_attacked()` vérifie l'attaque sur le roi, la case intermédiaire et la destination.
   Les rois ennemis sont traités séparément (calcul direct de leur portée à 1 pas) pour éviter
   une récursion infinie.
4. `Board._apply_castle()` déplace la tour à la case adjacente au roi (côté opposé).
5. Le contrôleur distingue les cases de roque des coups normaux dans `_classify_moves()`.
6. La case de destination du roque est surlignée en **bleu** (`HIGHLIGHT_CASTLE`).

### 4.5 Promotion automatique

Quand un pion n'a plus de case devant lui (`EDGE_NEIGHBOR[pos][fwd] is None`), il est
automatiquement remplacé par une Dame dans `Board.apply_move()`.

La méthode `Pawn.update_forward_dir(src)` recalcule la direction forward après chaque déplacement
en cherchant l'arête d'entrée dans la nouvelle case — essentiel aux frontières de sextants.

### 4.6 Gestion des échecs et mat

- `Board.is_king_in_check(color)` : un ennemi peut atteindre la case du roi.
- `Board.move_leaves_king_in_check(piece, dest)` : clone le plateau, applique le coup, vérifie.
- `King.is_checkmate(board)` : le roi est en échec ET aucune pièce alliée n'a de coup légal.
- En fin de tour, `Game._check_mate(mover)` vérifie si un adversaire est maté.

### 4.7 Intelligence artificielle

**Algorithme.** Minimax à 3 joueurs avec élagage alpha-bêta :
- Le joueur IA est MAX ; les deux autres sont traités comme MIN.
- Profondeur configurable par joueur (ex. `depth=4` pour rouge, `depth=2` pour noir).
- Évaluation : somme des valeurs des pièces alliées moins somme des pièces ennemies.

**Threaded.** `AIPlayer.start_thinking()` lance `MinimaxThread` en arrière-plan. Le contrôleur
interroge `is_thinking()` / `get_result()` à chaque frame — l'interface reste fluide pendant
le calcul. Le thread travaille sur un clone du plateau (`board.clone()`).

### 4.8 Vue et interface

- **`BoardView`** dessine les 96 polygones avec Pygame, superpose les sprites de pièces.
- Surlignages distincts : vert (coups légaux), jaune (sélection), rose (en passant),
  bleu (roque), rouge (roi en échec).
- **Labels de cases** pré-rendus une fois à l'initialisation (optimisation).
- **Hit-testing** par Shapely (`shapely.geometry.Polygon.contains`) pour convertir un clic
  souris en case algébrique ; les polygones Shapely sont mis en cache lazily.
- `POLYGONS` est calculé une seule fois dans `topology.py` et importé par la vue —
  aucune duplication du code de géométrie.

---

## 5. Difficultés rencontrées

### 5.1 Étiquetage cohérent des arêtes (bug principal)

**Problème.** La première version assignait les labels N/E/S/W depuis la géométrie brute (angle
du vecteur centre→milieu d'arête). Aux frontières de sextants, deux cases adjacentes pouvaient
recevoir des labels contradictoires : e.g. l'arête Nord de `e9` ne pointait pas vers `e10` mais
vers `i9`.

**Solution.** Réécriture complète de l'étiquetage par BFS partant d'une case fixe `"a1"`.
La clé est la fonction `_reorient()` qui recalcule les 4 labels d'un coup (échange d'axe NS/EW
+ inversion) plutôt que de ne corriger qu'une arête, évitant ainsi tout doublon.

### 5.2 Labels de coins incohérents avec le BFS

**Problème.** Les coins (`_CORNER_LABEL`) étaient dérivés des labels géométriques bruts, pas
des labels BFS corrigés → les coins aux frontières de sextants ne correspondaient plus aux
directions réelles → le mouvement du fou était erroné.

**Solution.** Recalcul de `_CORNER_LABEL` après le BFS, à partir de `_edge_labels` (corrigés).

### 5.3 Direction des pions aux frontières de sextants

**Problème.** Le pion conservait sa direction initiale même après avoir traversé une frontière
de sextant → il proposait des cases incorrectes.

**Solution.** `Pawn.update_forward_dir(src)` recalcule la direction depuis l'arête d'entrée
dans la nouvelle case après chaque déplacement.

### 5.4 Récursion infinie dans le roque

**Problème.** `King._is_attacked()` appelait `p.get_potential_moves(board)` sur les rois
ennemis → ceux-ci appelaient `_castling_squares()` → qui rappelait `_is_attacked()` → boucle
infinie.

**Solution.** Dans `_is_attacked()`, les rois ennemis sont traités séparément : leur portée
est calculée directement (1 pas dans 4 directions + 4 coins diagonaux) sans appeler
`get_potential_moves()`.

### 5.5 Faux positifs en passant

**Problème.** La détection du double avancement ne vérifiait que `was_first_move` et que la
case sautée était vide. Un pion faisant une capture diagonale à son premier coup passait aussi
le test.

**Solution.** Ajout de la vérification `EDGE_NEIGHBOR[skipped][OPPOSITE_DIR[fwd]] == src`
pour confirmer que l'avance est exactement linéaire sur 2 cases.

### 5.6 BFS non déterministe

**Problème.** `next(iter(VALID_SQUARES))` sur un frozenset donne une case différente selon
l'exécution Python → labels différents d'une run à l'autre.

**Solution.** La case de départ est fixée à `"a1"`.

---

## 6. Améliorations possibles

### 6.1 Règles des échecs à 3 joueurs

Actuellement, quand un roi est maté, la partie s'arrête immédiatement. Une règle plus complète
prévoirait que le joueur maté est éliminé et que les deux survivants continuent. Il faudrait
aussi définir si les pièces du joueur éliminé restent sur le plateau ou disparaissent.

### 6.2 Choix de promotion

La promotion est automatique en dame. Une interface graphique pourrait proposer le choix
(tour, fou, cavalier, dame) via une fenêtre modale Pygame.

### 6.3 Performances de l'IA

- **Mise en cache des coups légaux** : `get_legal_moves` clone le plateau pour chaque coup
  candidat ; une table de transposition réduirait les calculs répétés.
- **Élagage alpha-bêta amélioré** : tri des coups (captures d'abord) pour augmenter le taux
  d'élagage.
- **Évaluation positionnelle** : bonus pour le contrôle du centre, la mobilité des pièces,
  la sécurité du roi — actuellement seul le matériel est évalué.
- **Détection incrémentale des échecs** : recalculer uniquement ce qui change plutôt que de
  tout cloner.

### 6.4 Interface utilisateur

- Afficher un historique des coups en notation algébrique.
- Permettre l'annulation d'un coup (undo).
- Ajouter un menu de configuration des joueurs (humain / IA, profondeur) sans modifier `main.py`.
- Timer par joueur.

### 6.5 Réseau / multijoueur

Séparer le modèle du transport permettrait de jouer en réseau (TCP ou WebSocket) avec le
contrôleur côté client recevant des événements de coups sérialisés.

### 6.6 Tests automatisés

La logique de topologie et de mouvement est complexe ; une suite de tests unitaires (pytest)
sur `EDGE_NEIGHBOR`, `rook_ray`, `bishop_ray`, les règles spéciales (roque, en passant,
promotion) et la détection du mat garantirait la non-régression lors d'évolutions futures.

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
| `collections` | defaultdict dans topology.py |
