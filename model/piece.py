from abc import ABC, abstractmethod


class Piece(ABC):
    # classe de base abstraite pour toutes les pieces du jeu
    def __init__(self, color: str, position: str):
        self.color = color
        self.position = position
        self.has_moved = False
        self.value = 0

    # retourne les cases atteignables sans tenir compte de l'echec
    @abstractmethod
    def get_potential_moves(self, board) -> list:
        pass

    # retourne le symbole de la piece (P, N, B, R, Q, K)
    @abstractmethod
    def get_symbol(self) -> str:
        pass

    # cree une copie independante de la piece
    @abstractmethod
    def clone(self) -> "Piece":
        pass

    # retourne les coups legaux : potentiels filtres pour ne pas laisser son roi en echec
    def get_legal_moves(self, board) -> list:
        legal = []
        for move in self.get_potential_moves(board):
            if not board.move_leaves_king_in_check(self, move):
                legal.append(move)
        return legal

    # vrai si other est une piece de couleur differente
    def is_enemy(self, other) -> bool:
        return other is not None and other.color != self.color

    def __repr__(self):
        return f"{self.get_symbol()}({self.color}, {self.position})"
