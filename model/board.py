from model.topology import VALID_SQUARES, to_algebraic, EDGE_NEIGHBOR
from model.pieces.knight import Knight
from model.pieces.bishop import Bishop
from model.pieces.rook   import Rook
from model.pieces.queen  import Queen
from model.pieces.pawn   import Pawn
from model.pieces.king   import King


class Board:
    VALID_SQUARES = VALID_SQUARES

    # ordre des pieces sur la premiere rangee de chaque joueur
    BACK_RANKS = {
        "white": [Rook, Knight, Bishop, Queen, King,  Bishop, Knight, Rook],
        "red":   [Rook, Knight, Bishop, King,  Queen, Bishop, Knight, Rook],
        "black": [Queen, Bishop, Knight, Rook, King,  Bishop, Knight, Rook],
    }

    def __init__(self):
        self.squares = {sq: None for sq in VALID_SQUARES}
        # cible de prise en passant : (case_sautee, case_du_pion) apres une double avance
        self.en_passant = None
        self._setup()

    # vrai si sq est une case valide du plateau
    def is_valid(self, sq: str) -> bool:
        return sq in VALID_SQUARES

    # retourne la piece sur sq (ou None)
    def get_piece(self, sq: str):
        return self.squares.get(sq)

    # retourne toutes les pieces d'une couleur
    def get_pieces(self, color: str) -> list:
        pieces = []
        for piece in self.squares.values():
            if piece is not None and piece.color == color:
                pieces.append(piece)
        return pieces

    # applique un coup : deplace la piece, gere prise en passant et roque, signale si promotion
    def apply_move(self, piece, dest: str):
        src = piece.position

        # prise en passant : on retire le pion adverse saute
        if piece.get_symbol() == "P" and self.en_passant and dest == self.en_passant[0]:
            self.squares[self.en_passant[1]] = None

        # roque : si c'est le roi qui bouge de 2 cases, on bouge aussi la tour
        if piece.get_symbol() == "K":
            self._apply_castle(piece, dest)

        self.squares[src] = None
        self.squares[dest] = piece
        piece.position = dest
        piece.has_moved = True

        if isinstance(piece, Pawn):
            piece.update_forward_dir(src)
            if piece.can_promote(self):
                self.en_passant = None
                # l'appelant doit gerer le choix de la piece de promotion
                return True

        # reset ; game reposera la cible si necessaire
        self.en_passant = None
        return False

    # deplace la tour quand le roi roque (avance de 2 cases dans une direction)
    def _apply_castle(self, king, dest: str):
        src = king.position
        for direction in "NESW":
            one_step = EDGE_NEIGHBOR[src][direction]
            if one_step is None:
                continue
            two_steps = EDGE_NEIGHBOR[one_step][direction]
            if two_steps != dest:
                continue
            rook_sq = self._allied_rook_toward(src, direction, king.color)
            if rook_sq is None:
                continue
            rook = self.squares[rook_sq]
            rook_dest = EDGE_NEIGHBOR[dest][self._opposite(direction)]
            rook_destination_is_blocked = (
                rook_dest is None
                or self.squares[rook_dest] not in (None, rook)
            )
            if rook_destination_is_blocked:
                continue
            self.squares[rook_sq] = None
            self.squares[rook_dest] = rook
            rook.position = rook_dest
            rook.has_moved = True
            return

    # cherche la premiere tour alliee non deplacee dans une direction (None sinon)
    def _allied_rook_toward(self, src: str, direction: str, color: str):
        current_sq = src
        while True:
            current_sq = EDGE_NEIGHBOR[current_sq][direction]
            if current_sq is None:
                return None
            piece = self.squares[current_sq]
            if piece is None:
                continue
            is_castleable_rook = (
                piece.get_symbol() == "R"
                and piece.color == color
                and not piece.has_moved
            )
            if is_castleable_rook:
                return current_sq
            return None

    # retourne la direction opposee (N<->S, E<->W)
    def _opposite(self, direction: str) -> str:
        return {"N": "S", "S": "N", "E": "W", "W": "E"}[direction]

    # remplace le pion sur sq par la piece de promotion choisie
    def apply_promotion(self, sq: str, piece_class):
        pawn = self.squares[sq]
        promoted = piece_class(pawn.color, sq)
        promoted.has_moved = True
        self.squares[sq] = promoted

    # vrai si le roi de la couleur donnee est attaque
    def is_king_in_check(self, color: str) -> bool:
        # localiser le roi
        king_sq = None
        for sq, piece in self.squares.items():
            if piece is not None and piece.color == color and piece.get_symbol() == "K":
                king_sq = sq
                break

        if king_sq is None:
            return False

        # une piece ennemie peut-elle l'atteindre ?
        for piece in self.squares.values():
            if piece is None or piece.color == color:
                continue
            if king_sq in piece.get_potential_moves(self):
                return True
        return False

    # vrai si jouer ce coup laisserait son propre roi en echec (test sur un clone)
    def move_leaves_king_in_check(self, piece, dest: str) -> bool:
        copy = self.clone()
        copy.apply_move(copy.get_piece(piece.position), dest)
        return copy.is_king_in_check(piece.color)

    # cree une copie independante du plateau (pieces clonees)
    def clone(self) -> "Board":
        cloned_board = Board.__new__(Board)
        cloned_board.squares = {}
        for sq, piece in self.squares.items():
            if piece is not None:
                cloned_board.squares[sq] = piece.clone()
            else:
                cloned_board.squares[sq] = None
        cloned_board.en_passant = self.en_passant
        return cloned_board

    # place les pieces de depart pour les 3 joueurs
    def _setup(self):
        white_back  = [to_algebraic(x, 0) for x in range(8)]
        white_pawns = [to_algebraic(x, 1) for x in range(8)]
        red_back    = [to_algebraic(x, 7) for x in list(range(4)) + list(range(8, 12))]
        red_pawns   = [to_algebraic(x, 6) for x in list(range(4)) + list(range(8, 12))]
        black_back  = [to_algebraic(x, 11) for x in range(4, 12)]
        black_pawns = [to_algebraic(x, 10) for x in range(4, 12)]

        for color, back_rank_squares, pawn_squares in [
            ("white", white_back,  white_pawns),
            ("red",   red_back,    red_pawns),
            ("black", black_back,  black_pawns),
        ]:
            for sq, piece_class in zip(back_rank_squares, self.BACK_RANKS[color]):
                self.squares[sq] = piece_class(color, sq)
            for sq in pawn_squares:
                self.squares[sq] = Pawn(color, sq)
