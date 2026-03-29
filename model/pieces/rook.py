from model.piece import Piece
from model.topology import rook_ray


class Rook(Piece):
    # la tour : se deplace en ligne droite N/E/S/W
    def __init__(self, color, position):
        super().__init__(color, position)
        self.value = 5

    # retourne toutes les cases atteignables le long des 4 directions
    def get_potential_moves(self, board) -> list:
        moves = []
        for direction in "NESW":
            for sq in rook_ray(self.position, direction, lambda s: board.get_piece(s) is not None):
                occupant = board.get_piece(sq)
                if occupant is None:
                    moves.append(sq)
                elif self.is_enemy(occupant):
                    moves.append(sq)
                    break
                else:
                    break
        return moves

    def get_symbol(self) -> str:
        return "R"

    # cree une copie independante de la tour
    def clone(self) -> "Rook":
        cloned_rook = Rook(self.color, self.position)
        cloned_rook.has_moved = self.has_moved
        return cloned_rook
