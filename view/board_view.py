import pygame
from model.topology import POLYGONS, SEXTANTS, COLOR_FLIP_SEXTANTS, to_algebraic


class BoardView:
    # affichage du plateau et des pieces, gere le hit-testing au clic

    DARK             = (54,  39,  32)
    LIGHT            = (229, 210, 170)
    SELECTED         = (200, 200, 50)
    HIGHLIGHT        = (100, 200, 100)
    HIGHLIGHT_EP     = (220, 100, 180)
    HIGHLIGHT_CASTLE = (100, 160, 220)
    CHECK_COLOR      = (220, 50,  50)

    PIECE_NAMES  = {"king": "K", "queen": "Q", "rook": "R",
                    "bishop": "B", "knight": "N", "pawn": "P"}
    PIECE_COLORS = ("white", "black", "red")

    def __init__(self, window):
        self.window = window
        self.sprites = self._load_sprites()
        self.polygons, self._sq_colors = self._build_polygons()
        self._labels = self._prerender_labels()
        # polygones shapely pour le hit-test, construits paresseusement au premier clic
        self._shapely = None
        # derniere snapshot recue via update(), lue par le controleur
        self._pending_game = None

    # charge les sprites des pieces depuis assets/pieces/ (les manquants sont ignores)
    def _load_sprites(self):
        sprites = {}
        for color in self.PIECE_COLORS:
            for name, symbol in self.PIECE_NAMES.items():
                try:
                    img = pygame.image.load(f"assets/pieces/{color}-{name}.png")
                    sprites[(color, symbol)] = pygame.transform.scale(img, (42, 42))
                except FileNotFoundError:
                    pass
        return sprites

    # convertit les polygones de la topologie en listes pygame et calcule la couleur des cases
    def _build_polygons(self):
        polys = {}
        colors = {}
        for i, ((x1, x2), (y1, y2)) in enumerate(SEXTANTS):
            for x in range(x1, x2):
                for y in range(y1, y2):
                    sq = to_algebraic(x, y)
                    pts = [list(p) for p in POLYGONS[sq]]
                    parity = (x + y + i) % 2
                    if i in COLOR_FLIP_SEXTANTS:
                        parity = 1 - parity
                    polys[sq] = {
                        "points": pts,
                        "center": (
                            sum(p[0] for p in pts) / 4,
                            sum(p[1] for p in pts) / 4,
                        ),
                    }
                    colors[sq] = self.DARK if parity == 0 else self.LIGHT
        return polys, colors

    # pre-rend les libelles algebriques de chaque case (gagne du temps a chaque frame)
    def _prerender_labels(self):
        font = pygame.font.SysFont("monospace", 16)
        return {sq: font.render(sq, True, (255, 0, 0)) for sq in self.polygons}

    # construit (paresseusement) les polygones shapely pour le hit-test
    def _get_shapely(self):
        if self._shapely is None:
            from shapely.geometry import Polygon
            self._shapely = {sq: Polygon(data["points"])
                             for sq, data in self.polygons.items()}
        return self._shapely

    # retourne la case algebrique sous mouse_pos, ou None hors plateau
    def square_at(self, mouse_pos) -> str | None:
        from shapely.geometry import Point
        pt = Point(mouse_pos)
        for sq, poly in self._get_shapely().items():
            if poly.contains(pt):
                return sq
        return None

    # dessine le plateau, les surlignages et les pieces
    def draw(self, board, highlights=None, selected=None, checked_kings=None,
             ep_highlights=None, castle_highlights=None):
        self.window.fill((0, 0, 0))
        highlights = highlights or set()
        ep_highlights = ep_highlights or set()
        castle_highlights = castle_highlights or set()
        checked_kings = checked_kings or set()

        for sq, data in self.polygons.items():
            # priorite des surlignages : echec > roque > prise en passant > coup normal > selection
            if sq in checked_kings:
                color = self.CHECK_COLOR
            elif sq in castle_highlights:
                color = self.HIGHLIGHT_CASTLE
            elif sq in ep_highlights:
                color = self.HIGHLIGHT_EP
            elif sq in highlights:
                color = self.HIGHLIGHT
            elif sq == selected:
                color = self.SELECTED
            else:
                color = self._sq_colors[sq]

            pygame.draw.polygon(self.window, color, data["points"])

            cx, cy = data["center"]
            self.window.blit(self._labels[sq], (cx - 10, cy - 5))

            piece = board.get_piece(sq)
            if piece is not None:
                sprite = self.sprites.get((piece.color, piece.get_symbol()))
                if sprite is not None:
                    self.window.blit(sprite, (cx - 21, cy - 21))

    # appele par game.notify() ; on memorise l'etat mais le rendu reste a la charge du controleur
    def update(self, game):
        self._pending_game = game
