from model.piece import Piece
from model.topology import bishop_ray


class Bishop(Piece):
    # le fou : se deplace en diagonale, peut traverser le hub central
    def __init__(self, color, position):
        super().__init__(color, position)
        self.value = 3

    # retourne toutes les cases atteignables le long des 4 coins
    def get_potential_moves(self, board) -> list:
        moves = set()
        for corner in ("NE", "SE", "SW", "NW"):
            for sq in bishop_ray(self.position, corner,
                                 lambda s: board.get_piece(s) is not None):
                occupant = board.get_piece(sq)
                if occupant is None or self.is_enemy(occupant):
                    moves.add(sq)
        return list(moves)

    def get_symbol(self) -> str:
        return "B"

    # cree une copie independante du fou
    def clone(self) -> "Bishop":
        cloned_bishop = Bishop(self.color, self.position)
        cloned_bishop.has_moved = self.has_moved
        return cloned_bishop
