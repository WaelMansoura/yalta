from model.piece import Piece
from model.topology import EDGE_NEIGHBOR, bishop_first_step, CORNERS


class King(Piece):
    # le roi : se deplace d'une case, peut roquer dans 4 directions
    def __init__(self, color, position):
        super().__init__(color, position)
        self.value = 1000

    # retourne tous les coups potentiels : un pas dans toutes directions + roques
    def get_potential_moves(self, board) -> list:
        moves = set(self._one_step_squares(board))
        for sq in self._castling_squares(board):
            moves.add(sq)
        return list(moves)

    # cases atteignables a un pas (tour + fou), sans tenir compte du roque
    def _one_step_squares(self, board) -> list:
        moves = []

        for direction in "NESW":
            neighbor = EDGE_NEIGHBOR[self.position][direction]
            if neighbor is None:
                continue
            occupant = board.get_piece(neighbor)
            square_is_free_or_enemy = occupant is None or self.is_enemy(occupant)
            if square_is_free_or_enemy:
                moves.append(neighbor)

        for corner in CORNERS:
            for diagonal_neighbor, _ in bishop_first_step(self.position, corner):
                occupant = board.get_piece(diagonal_neighbor)
                square_is_free_or_enemy = occupant is None or self.is_enemy(occupant)
                if square_is_free_or_enemy:
                    moves.append(diagonal_neighbor)

        return moves

    # cases d'arrivee possibles si le roi roque
    def _castling_squares(self, board) -> list:
        king_cannot_castle = self.has_moved or self._is_attacked(board, self.position)
        if king_cannot_castle:
            return []

        results = []
        for direction in "NESW":
            one_step = EDGE_NEIGHBOR[self.position][direction]
            if one_step is None or board.get_piece(one_step) is not None:
                continue
            two_steps = EDGE_NEIGHBOR[one_step][direction]
            if two_steps is None or board.get_piece(two_steps) is not None:
                continue
            if self._find_rook(board, direction) is None:
                continue
            path_is_attacked = (
                self._is_attacked(board, one_step)
                or self._is_attacked(board, two_steps)
            )
            if path_is_attacked:
                continue
            results.append(two_steps)
        return results

    # cherche la premiere tour alliee non deplacee dans une direction donnee
    def _find_rook(self, board, direction: str):
        current_sq = self.position
        while True:
            current_sq = EDGE_NEIGHBOR[current_sq][direction]
            if current_sq is None:
                return None
            piece = board.get_piece(current_sq)
            if piece is None:
                continue
            is_castleable_rook = (
                piece.get_symbol() == "R"
                and piece.color == self.color
                and not piece.has_moved
            )
            if is_castleable_rook:
                return current_sq
            return None

    # vrai si une piece ennemie peut atteindre sq (les rois sont traites a part pour eviter la recursion)
    def _is_attacked(self, board, sq: str) -> bool:
        for piece in board.squares.values():
            if piece is None or piece.color == self.color:
                continue

            if piece.get_symbol() == "K":
                # un roi attaque ses voisins immediats (sans recurser sur _is_attacked)
                rook_neighbors = {
                    EDGE_NEIGHBOR[piece.position][direction]
                    for direction in "NESW"
                }
                diagonal_neighbors = {
                    neighbor
                    for corner in CORNERS
                    for neighbor, _ in bishop_first_step(piece.position, corner)
                }
                king_reach = rook_neighbors | diagonal_neighbors
                if sq in king_reach:
                    return True
            elif sq in piece.get_potential_moves(board):
                return True

        return False

    # vrai si le roi est en echec et qu'aucune piece alliee ne peut le sauver
    def is_checkmate(self, board) -> bool:
        if not board.is_king_in_check(self.color):
            return False
        allied_pieces = board.get_pieces(self.color)
        for piece in allied_pieces:
            if piece.get_legal_moves(board):
                return False
        return True

    def get_symbol(self) -> str:
        return "K"

    # cree une copie independante du roi
    def clone(self) -> "King":
        cloned_king = King(self.color, self.position)
        cloned_king.has_moved = self.has_moved
        return cloned_king
