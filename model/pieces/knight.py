from model.piece import Piece
from model.topology import KNIGHT_TARGETS


class Knight(Piece):
    # le cavalier : saute vers des cases precalculees
    def __init__(self, color, position):
        super().__init__(color, position)
        self.value = 3

    # retourne les cases atteignables : cases precalculees libres ou ennemies
    def get_potential_moves(self, board) -> list:
        moves = []
        for sq in KNIGHT_TARGETS[self.position]:
            occupant = board.get_piece(sq)
            if occupant is None or self.is_enemy(occupant):
                moves.append(sq)
        return moves

    def get_symbol(self) -> str:
        return "N"

    # cree une copie independante du cavalier
    def clone(self) -> "Knight":
        cloned_knight = Knight(self.color, self.position)
        cloned_knight.has_moved = self.has_moved
        return cloned_knight
