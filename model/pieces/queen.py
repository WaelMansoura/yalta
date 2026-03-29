from model.piece import Piece
from model.topology import rook_ray, bishop_ray


class Queen(Piece):
    # la reine : combine les mouvements de la tour et du fou
    def __init__(self, color, position):
        super().__init__(color, position)
        self.value = 9

    # retourne toutes les cases atteignables : lignes droites + diagonales
    def get_potential_moves(self, board) -> list:
        moves = set()

        # predicat utilise pour stopper les rayons sur une case occupee
        def square_is_occupied(sq):
            return board.get_piece(sq) is not None

        for direction in "NESW":
            for sq in rook_ray(self.position, direction, square_is_occupied):
                occupant = board.get_piece(sq)
                if occupant is None or self.is_enemy(occupant):
                    moves.add(sq)
                if occupant is not None:
                    break

        for corner in ("NE", "SE", "SW", "NW"):
            for sq in bishop_ray(self.position, corner, square_is_occupied):
                occupant = board.get_piece(sq)
                if occupant is None or self.is_enemy(occupant):
                    moves.add(sq)

        return list(moves)

    def get_symbol(self) -> str:
        return "Q"

    # cree une copie independante de la reine
    def clone(self) -> "Queen":
        cloned_queen = Queen(self.color, self.position)
        cloned_queen.has_moved = self.has_moved
        return cloned_queen
