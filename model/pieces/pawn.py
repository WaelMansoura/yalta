from model.piece import Piece
from model.topology import EDGE_NEIGHBOR, OPPOSITE_DIR, bishop_first_step, PAWN_FORWARD, CAPTURE_CORNERS


class Pawn(Piece):
    # le pion : avance d'une case (deux au depart), capture en diagonale, prise en passant
    def __init__(self, color, position, forward_dir: str = None):
        super().__init__(color, position)
        self.value = 1
        self.forward_dir = forward_dir or PAWN_FORWARD.get(position)

    # retourne les coups potentiels : avance, double avance, captures, prise en passant
    def get_potential_moves(self, board) -> list:
        moves = []
        forward_dir = self.forward_dir
        if forward_dir is None:
            return moves

        # avance d'une case (et eventuellement de deux si pas encore bouge)
        one_step = EDGE_NEIGHBOR[self.position][forward_dir]
        if one_step is not None and board.get_piece(one_step) is None:
            moves.append(one_step)
            if not self.has_moved:
                two_steps = EDGE_NEIGHBOR[one_step][forward_dir]
                if two_steps is not None and board.get_piece(two_steps) is None:
                    moves.append(two_steps)

        # captures en diagonale avant
        for capture_corner in CAPTURE_CORNERS[forward_dir]:
            for diagonal_sq, _ in bishop_first_step(self.position, capture_corner):
                if self.is_enemy(board.get_piece(diagonal_sq)):
                    moves.append(diagonal_sq)

        # prise en passant : board.en_passant est pose par Game apres une double avance adverse
        en_passant_info = board.en_passant
        if en_passant_info is not None:
            ep_target_sq, ep_pawn_sq = en_passant_info
            for direction, neighbor in EDGE_NEIGHBOR[self.position].items():
                is_sideways = direction != forward_dir and direction != OPPOSITE_DIR[forward_dir]
                if neighbor == ep_pawn_sq and is_sideways:
                    moves.append(ep_target_sq)
                    break

        return moves

    # vrai si le pion est arrive au bout (plus aucune case devant)
    def can_promote(self, board) -> bool:
        return (self.forward_dir is not None
                and EDGE_NEIGHBOR[self.position][self.forward_dir] is None)

    # recalcule la direction d'avance apres un deplacement (les sextants tournent le repere)
    def update_forward_dir(self, src: str):
        entry_dir = next(
            (direction for direction, neighbor in EDGE_NEIGHBOR[self.position].items()
             if neighbor == src),
            None
        )
        if entry_dir is not None:
            self.forward_dir = OPPOSITE_DIR[entry_dir]

    def get_symbol(self) -> str:
        return "P"

    # cree une copie independante du pion
    def clone(self) -> "Pawn":
        cloned_pawn = Pawn(self.color, self.position, self.forward_dir)
        cloned_pawn.has_moved = self.has_moved
        return cloned_pawn
