# topologie du plateau yalta : graphes statiques pour le mouvement des pieces.
#
# notation algebrique : colonnes a-l, rangees 1-12. coordonnees internes (x, y)
# ou x est l'index de colonne (0-11) et y l'index de rangee (0-11).
# les 6 sextants sont des blocs 4x4 disposes en hexagone autour d'un hub central.
#
# les sextants ont des orientations differentes (rotations/transpositions),
# donc les adjacences n/e/s/w et les sommets partages ne suivent pas la grille brute.
# edge_neighbor et vertex_class sont derives de la geometrie physique reelle
# pour que les mouvements des tours, fous et cavaliers correspondent a la topologie reelle.

from collections import defaultdict
from math import sqrt, cos, sin, radians, atan2

FILES = "abcdefghijkl"


# convertit (x, y) en notation algebrique (ex: 0,0 -> "a1")
def to_algebraic(x: int, y: int) -> str:
    return FILES[x] + str(y + 1)


# convertit la notation algebrique en (x, y) (ex: "a1" -> (0,0))
def from_algebraic(s: str) -> tuple:
    return (FILES.index(s[0]), int(s[1:]) - 1)


# bornes des sextants : (plage_x, plage_y)
SEXTANTS = [
    ((0, 4),  (0, 4)),
    ((0, 4),  (4, 8)),
    ((8, 12), (4, 8)),
    ((8, 12), (8, 12)),
    ((4, 8),  (8, 12)),
    ((4, 8),  (0, 4)),
]

# transformation (flip_x, flip_y, transpose) par sextant, partage avec la vue
SEXTANT_TRANSFORM = [
    (False, False, False),
    (False, True,  True),
    (True,  True,  False),
    (True,  True,  True),
    (True,  True,  False),
    (True,  False, True),
]

# sextants dont il faut inverser la parite de couleur pour rester coherent
COLOR_FLIP_SEXTANTS = {1, 5}

OPPOSITE_DIR    = {"N": "S", "S": "N", "E": "W", "W": "E"}
OPPOSITE_CORNER = {"NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}
CORNERS         = ("NE", "SE", "SW", "NW")


# retourne l'index du sextant contenant (x, y), ou None hors plateau
def _sextant_of(x, y):
    for i, ((x1, x2), (y1, y2)) in enumerate(SEXTANTS):
        if x1 <= x < x2 and y1 <= y < y2:
            return i
    return None


VALID_COORDS = frozenset(
    (x, y)
    for (x1, x2), (y1, y2) in SEXTANTS
    for x in range(x1, x2)
    for y in range(y1, y2)
)
VALID_SQUARES = frozenset(to_algebraic(x, y) for x, y in VALID_COORDS)
SEXTANT       = {sq: _sextant_of(*from_algebraic(sq)) for sq in VALID_SQUARES}


# retourne la couleur de la case (x, y) : "dark" ou "light"
def _color(x, y):
    i = _sextant_of(x, y)
    parity = (x + y + i) % 2
    if i in COLOR_FLIP_SEXTANTS:
        parity = 1 - parity
    return "dark" if parity == 0 else "light"


COLOR = {sq: _color(*from_algebraic(sq)) for sq in VALID_SQUARES}


# polygones physiques (meme geometrie que la vue)

# calcule le polygone a 4 sommets pour chaque case du plateau
def _compute_polygons():
    polygons = {}
    mid_x = mid_y = 400.0
    size   = 400.0
    height = sqrt(size ** 2 - (size / 2) ** 2)
    cos30, sin30 = cos(radians(30)), sin(radians(30))

    v123 = [
        (-size * cos(radians(60)), -height),
        ( size * cos(radians(60)), -height),
        ( size,                     0),
        ( size * cos(radians(60)),  height),
        (-size * cos(radians(60)),  height),
        (-size,                     0),
    ]
    vabc = [
        (-height * cos30, -height * sin30),
        (0,               -height),
        ( height * cos30, -height * sin30),
        ( height * cos30,  height * sin30),
        (0,                height),
        (-height * cos30,  height * sin30),
    ]

    for i, ((x1, x2), (y1, y2)) in enumerate(SEXTANTS):
        flip_x, flip_y, transpose = SEXTANT_TRANSFORM[i]
        s1x, s1y = v123[i][0] * 0.5,          v123[i][1] * 0.5
        s2x, s2y = v123[(i + 2) % 6][0] * 0.5, v123[(i + 2) % 6][1] * 0.5
        vax, vay = vabc[(i + 1) % 6]
        cx = mid_x + v123[(i + 4) % 6][0]
        cy = mid_y + v123[(i + 4) % 6][1]

        # interpolation bilineaire dans le sextant (rx, ry dans [0, 1])
        def pt(rx, ry, s1x=s1x, s1y=s1y, s2x=s2x, s2y=s2y,
               vax=vax, vay=vay, cx=cx, cy=cy):
            ux = vax * ry - s1x * ry + s2x
            uy = vay * ry - s1y * ry + s2y
            return (cx + s1x * ry + ux * rx, cy + s1y * ry + uy * rx)

        for x in range(x1, x2):
            for y in range(y1, y2):
                lx, ly = x % 4, y % 4
                if flip_x:  lx = 3 - lx
                if flip_y:  ly = 3 - ly
                if transpose: lx, ly = ly, lx
                rx1, ry1 = lx / 4,       ly / 4
                rx2, ry2 = (lx + 1) / 4, (ly + 1) / 4
                polygons[to_algebraic(x, y)] = (
                    pt(rx1, ry1), pt(rx2, ry1), pt(rx2, ry2), pt(rx1, ry2)
                )
    return polygons


# dict des polygones, reutilise par la vue pour eviter de recalculer
POLYGONS = _compute_polygons()


# cle entiere stable pour un point flottant (arrondi au demi-pixel)
def _key(p):
    return (round(p[0] * 2), round(p[1] * 2))


# associe chaque (case, index_coin) a la cle du point physique correspondant
_cells_at_vertex = defaultdict(list)
for _sq, _pts in POLYGONS.items():
    for _i, _p in enumerate(_pts):
        _cells_at_vertex[_key(_p)].append((_sq, _i))


# etiquetage des aretes (n/e/s/w) par bfs.
# les labels sont abstraits (pas de vraies directions geographiques) mais doivent verifier :
#   * les aretes opposees d'une case ont des labels opposes (n<->s, e<->w)
#   * les aretes partagees entre deux cases adjacentes ont des labels opposes


# attribue les labels n/e/s/w aux 4 aretes d'une case selon sa geometrie
def _classify_edges(pts):
    center_x = sum(point[0] for point in pts) / 4
    center_y = sum(point[1] for point in pts) / 4

    edge_midpoint_offsets = []
    for i in range(4):
        mid_x = (pts[i][0] + pts[(i + 1) % 4][0]) / 2
        mid_y = (pts[i][1] + pts[(i + 1) % 4][1]) / 2
        edge_midpoint_offsets.append((mid_x - center_x, mid_y - center_y))

    dx0, dy0 = edge_midpoint_offsets[0]
    dx1, dy1 = edge_midpoint_offsets[1]
    labels = {}
    if abs(dy0) > abs(dx0):
        labels[0] = "N" if dy0 < 0 else "S"
        labels[2] = OPPOSITE_DIR[labels[0]]
        labels[1] = "E" if dx1 > 0 else "W"
        labels[3] = OPPOSITE_DIR[labels[1]]
    else:
        labels[0] = "E" if dx0 > 0 else "W"
        labels[2] = OPPOSITE_DIR[labels[0]]
        labels[1] = "N" if dy1 < 0 else "S"
        labels[3] = OPPOSITE_DIR[labels[1]]
    return labels


# re-etiquette geom pour que l'arete edge_index porte target_label,
# en preservant la structure des paires opposees (0,2) et (1,3)
def _reorient(geom, edge_index, target_label):
    target_axis = "NS" if target_label in "NS" else "EW"
    g_axis      = "NS" if geom[edge_index] in "NS" else "EW"
    if g_axis != target_axis:
        swap = {"N": "E", "S": "W", "E": "N", "W": "S"}
        labels = {i: swap[geom[i]] for i in range(4)}
    else:
        labels = dict(geom)
    if labels[edge_index] != target_label:
        flip = OPPOSITE_DIR
        for i in (edge_index, (edge_index + 2) % 4):
            labels[i] = flip[labels[i]]
    return labels


# corrige un etiquetage geometrique brut pour que les paires opposees soient coherentes
def _make_valid_seed(geom):
    labels = dict(geom)
    labels[2] = OPPOSITE_DIR[labels[0]]
    ax0 = "NS" if labels[0] in "NS" else "EW"
    ax1 = "NS" if labels[1] in "NS" else "EW"
    if ax0 == ax1:
        swap = {"N": "E", "S": "W", "E": "N", "W": "S"}
        labels[1] = swap[labels[1]]
    labels[3] = OPPOSITE_DIR[labels[1]]
    return labels


# cle d'arete invariante par sens (a, b) == (b, a)
def _edge_key(a, b):
    ka, kb = _key(a), _key(b)
    return (ka, kb) if ka < kb else (kb, ka)


_geo_labels = {sq: _classify_edges(POLYGONS[sq]) for sq in VALID_SQUARES}

_edges_of = defaultdict(list)
for _sq, _pts in POLYGONS.items():
    for _i in range(4):
        _edges_of[_edge_key(_pts[_i], _pts[(_i+1)%4])].append((_sq, _i))

# bfs pour propager des labels coherents sur toutes les cases.
# on part d'une case fixe pour que le resultat soit deterministe.
_start = "a1"
_edge_labels = {_start: _make_valid_seed(_geo_labels[_start])}
_visited  = {_start}
_frontier = [_start]

while _frontier:
    _next = []
    for _sq in _frontier:
        _pts = POLYGONS[_sq]
        for _i in range(4):
            _ek = _edge_key(_pts[_i], _pts[(_i+1)%4])
            _pair = _edges_of[_ek]
            if len(_pair) != 2:
                continue
            (sa, ia), (sb, ib) = _pair
            _nb = sb if sa == _sq else sa
            if _nb in _visited:
                continue
            _visited.add(_nb)
            _dir_sq = _edge_labels[_sq][_i]
            _nb_idx = ia if sa == _nb else ib
            _edge_labels[_nb] = _reorient(_geo_labels[_nb], _nb_idx, OPPOSITE_DIR[_dir_sq])
            _next.append(_nb)
    _frontier = _next

EDGE_NEIGHBOR = {sq: {"N": None, "E": None, "S": None, "W": None}
                 for sq in VALID_SQUARES}
for _sq in VALID_SQUARES:
    _pts = POLYGONS[_sq]
    for _i in range(4):
        _ek = _edge_key(_pts[_i], _pts[(_i+1)%4])
        _pair = _edges_of[_ek]
        if len(_pair) == 2:
            (sa, _), (sb, _) = _pair
            _nb = sb if sa == _sq else sa
            _d  = _edge_labels[_sq][_i]
            if _d:
                EDGE_NEIGHBOR[_sq][_d] = _nb

# recalcul des labels des coins depuis les labels d'aretes corriges par bfs
_CORNER_LABEL = {}
for _sq in VALID_SQUARES:
    _el = _edge_labels[_sq]
    _cl = {}
    for _vi in range(4):
        _d1 = _el[(_vi - 1) % 4]
        _d2 = _el[_vi]
        _ns = _d1 if _d1 in "NS" else _d2
        _ew = _d1 if _d1 in "EW" else _d2
        _cl[_vi] = _ns + _ew
    _CORNER_LABEL[_sq] = _cl


# vertex_class : classes d'equivalence de sommets (pour le fou).
# deux paires (sq, coin) appartiennent a la meme classe si elles partagent un point physique.
# le hub central est special : ses 6 cases forment 2 triangles alternes.

_HUB_KEY = _key((400.0, 400.0))


# angle polaire du centre de la case par rapport au centre du plateau (400, 400)
def _hub_cell_angle(sq_and_corner_index):
    sq, _ = sq_and_corner_index
    cell_points = POLYGONS[sq]
    center_x = sum(point[0] for point in cell_points) / 4
    center_y = sum(point[1] for point in cell_points) / 4
    return atan2(center_y - 400.0, center_x - 400.0)


_hub_raw    = _cells_at_vertex[_HUB_KEY]
_hub_sorted = sorted(_hub_raw, key=_hub_cell_angle)
HUB_CORNERS = [(sq, _CORNER_LABEL[sq][vi]) for (sq, vi) in _hub_sorted]

_parent = {(sq, c): (sq, c) for sq in VALID_SQUARES for c in CORNERS}


# union-find : retrouve la racine de v avec compression de chemin
def _find(v):
    while _parent[v] != v:
        _parent[v] = _parent[_parent[v]]
        v = _parent[v]
    return v


# union-find : fusionne les classes de u et v
def _union(u, v):
    ru, rv = _find(u), _find(v)
    if ru != rv:
        _parent[ru] = rv


for _k, _members in _cells_at_vertex.items():
    if _k == _HUB_KEY or len(_members) < 2:
        continue
    _labels = [(sq, _CORNER_LABEL[sq][vi]) for sq, vi in _members]
    for _p in _labels[1:]:
        _union(_labels[0], _p)

# au hub : les 6 cases forment 2 triangles alternes ; on les unit par paires
for _a, _b in [
    (HUB_CORNERS[0], HUB_CORNERS[2]),
    (HUB_CORNERS[2], HUB_CORNERS[4]),
    (HUB_CORNERS[1], HUB_CORNERS[3]),
    (HUB_CORNERS[3], HUB_CORNERS[5]),
]:
    _union(_a, _b)

_classes = defaultdict(list)
for _k in _parent:
    _classes[_find(_k)].append(_k)

VERTEX_CLASS = {}
for _root, _members in _classes.items():
    _frozen = frozenset(_members)
    for _m in _members:
        VERTEX_CLASS[_m] = _frozen


# mouvement du fou et de la tour

# un pas de fou depuis sq, entree par entry_corner ; retourne les (case_suivante, coin_entree)
def bishop_step(sq, entry_corner):
    exit_corner    = OPPOSITE_CORNER[entry_corner]
    square_color   = COLOR[sq]
    reachable = []
    for neighbor_sq, neighbor_entry_corner in VERTEX_CLASS[(sq, exit_corner)]:
        if neighbor_sq != sq and COLOR[neighbor_sq] == square_color:
            reachable.append((neighbor_sq, neighbor_entry_corner))
    return reachable


# premier pas de fou depuis sq (sans entree prealable), sortie par exit_corner
def bishop_first_step(sq, exit_corner):
    square_color = COLOR[sq]
    reachable = []
    for neighbor_sq, neighbor_entry_corner in VERTEX_CLASS[(sq, exit_corner)]:
        if neighbor_sq != sq and COLOR[neighbor_sq] == square_color:
            reachable.append((neighbor_sq, neighbor_entry_corner))
    return reachable


# rayon de la tour : itere les cases dans une direction jusqu'a un bloqueur ou un bord.
# la case du bloqueur est yieldee ; c'est a l'appelant de decider capture ou stop.
def rook_ray(sq, direction, blocked):
    current_sq = sq
    exit_dir   = direction
    while True:
        next_sq = EDGE_NEIGHBOR[current_sq][exit_dir]
        if next_sq is None:
            return
        yield next_sq
        if blocked(next_sq):
            return
        # trouver la direction d'entree dans next_sq (celle qui pointe vers current_sq)
        entry_dir = next(
            (dir_ for dir_, neighbor in EDGE_NEIGHBOR[next_sq].items() if neighbor == current_sq),
            None
        )
        if entry_dir is None:
            return
        exit_dir   = OPPOSITE_DIR[entry_dir]
        current_sq = next_sq


# rayon du fou : itere les cases en diagonale, peut se ramifier au hub central
def bishop_ray(sq, exit_corner, blocked):
    seen     = set()
    frontier = bishop_first_step(sq, exit_corner)
    while frontier:
        next_frontier = []
        for next_sq, entry_corner in frontier:
            if (next_sq, entry_corner) in seen:
                continue
            seen.add((next_sq, entry_corner))
            yield next_sq
            if not blocked(next_sq):
                next_frontier.extend(bishop_step(next_sq, entry_corner))
        frontier = next_frontier


# cibles du cavalier (precalculees)

# calcule les cases atteignables par le cavalier depuis sq (motif "tour puis fou" ou "fou puis tour")
def _knight_targets(sq):
    targets = set()

    # patron "rook puis bishop" : 1 pas de tour, puis 1 pas de fou
    for rook_direction in "NESW":
        rook_neighbor = EDGE_NEIGHBOR[sq][rook_direction]
        if rook_neighbor is None:
            continue
        for bishop_corner in CORNERS:
            for bishop_landing, _ in bishop_first_step(rook_neighbor, bishop_corner):
                if bishop_landing != sq:
                    targets.add(bishop_landing)

    # patron "bishop puis rook" : 1 pas de fou, puis 1 pas de tour
    for bishop_corner in CORNERS:
        for bishop_neighbor, _ in bishop_first_step(sq, bishop_corner):
            for rook_direction in "NESW":
                rook_landing = EDGE_NEIGHBOR[bishop_neighbor][rook_direction]
                if rook_landing is not None and rook_landing != sq:
                    targets.add(rook_landing)

    # retirer les cases adjacentes (le cavalier saute par-dessus)
    adjacent = {neighbor for neighbor in EDGE_NEIGHBOR[sq].values() if neighbor is not None} | {sq}
    return frozenset(target for target in targets if target not in adjacent)


KNIGHT_TARGETS = {sq: _knight_targets(sq) for sq in VALID_SQUARES}


# direction d'avance des pions

# direction d'avance pour un pion sur sa rangee de depart (None si pas une case de depart)
def _pawn_forward_seed(sq):
    col, rank = from_algebraic(sq)
    if rank == 1 and col < 8:
        target_rank = 2
    elif rank == 6 and (col < 4 or col >= 8):
        target_rank = 5
    elif rank == 10 and col >= 4:
        target_rank = 9
    else:
        return None
    for direction, neighbor in EDGE_NEIGHBOR[sq].items():
        if neighbor is not None and from_algebraic(neighbor)[1] == target_rank:
            return direction
    return None


# propage les directions d'avance depuis les rangees de depart vers tout le plateau
def _propagate_pawn_directions(seeds):
    result   = dict(seeds)
    frontier = list(seeds.items())
    while frontier:
        next_frontier = []
        for sq, forward_dir in frontier:
            next_sq = EDGE_NEIGHBOR[sq][forward_dir]
            if next_sq is None or next_sq in result:
                continue
            entry_dir = next(
                (direction for direction, neighbor in EDGE_NEIGHBOR[next_sq].items()
                 if neighbor == sq),
                None
            )
            if entry_dir is None:
                continue
            result[next_sq] = OPPOSITE_DIR[entry_dir]
            next_frontier.append((next_sq, result[next_sq]))
        frontier = next_frontier
    return result


# construit le dict des cases de depart vers leur direction d'avance initiale
def _build_pawn_forward_seeds():
    seeds = {}
    for sq in VALID_SQUARES:
        forward_dir = _pawn_forward_seed(sq)
        if forward_dir is not None:
            seeds[sq] = forward_dir
    return seeds


PAWN_FORWARD = _propagate_pawn_directions(_build_pawn_forward_seeds())

# coins de capture diagonale pour chaque direction d'avance
CAPTURE_CORNERS = {
    "N": ("NW", "NE"),
    "E": ("NE", "SE"),
    "S": ("SE", "SW"),
    "W": ("NW", "SW"),
}
