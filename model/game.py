from model.board import Board
from model.topology import EDGE_NEIGHBOR, OPPOSITE_DIR


class Game:
    # partie de yalta : 3 joueurs, se termine au premier mat
    def __init__(self, players: list, board: Board = None):
        self.players = players
        self.board = board or Board()
        self.current_index = 0
        self.current_player = players[0]
        self.winner = None
        self.loser = None
        self._observers = []
        # case d'une promotion en attente (mise quand un pion atteint le bord)
        self.pending_promotion_sq = None
        self._promotion_mover = None

    # ajoute un observateur prevenu a chaque changement d'etat
    def add_observer(self, observer):
        self._observers.append(observer)

    # previens tous les observateurs
    def notify(self):
        for observer in self._observers:
            observer.update(self)

    # passe au joueur suivant
    def next_turn(self):
        if not self.is_over():
            self.current_index = (self.current_index + 1) % len(self.players)
            self.current_player = self.players[self.current_index]

    # vrai si une promotion est en attente du choix du joueur
    def needs_promotion(self) -> bool:
        return self.pending_promotion_sq is not None

    # applique un coup ; si une promotion est requise, on attend confirm_promotion
    def apply_move(self, piece, dest: str):
        mover = self.current_player
        src = piece.position
        was_first_move = not piece.has_moved

        needs_promo = self.board.apply_move(piece, dest)
        self.board.en_passant = self._en_passant_after(piece, src, dest, was_first_move)

        if needs_promo:
            self.pending_promotion_sq = dest
            self._promotion_mover = mover
            self.notify()
            # on attend confirm_promotion()
            return

        self._check_mate(mover)
        self.notify()
        if not self.is_over():
            self.next_turn()

    # confirme la promotion choisie (a appeler apres apply_move quand needs_promotion est vrai)
    def confirm_promotion(self, piece_class):
        sq = self.pending_promotion_sq
        mover = self._promotion_mover
        self.pending_promotion_sq = None
        self._promotion_mover = None

        self.board.apply_promotion(sq, piece_class)
        self._check_mate(mover)
        self.notify()
        if not self.is_over():
            self.next_turn()

    # retourne (case_sautee, case_pion) si le coup est une double avance de pion, sinon None
    def _en_passant_after(self, piece, src: str, dest: str, was_first_move: bool):
        is_pawn_first_move = piece.get_symbol() == "P" and was_first_move
        if not is_pawn_first_move:
            return None

        forward_dir = piece.forward_dir
        if forward_dir is None:
            return None

        skipped_sq = EDGE_NEIGHBOR[dest][OPPOSITE_DIR[forward_dir]]
        skipped_sq_is_empty = skipped_sq is not None and self.board.get_piece(skipped_sq) is None
        if not skipped_sq_is_empty:
            return None

        # confirmer que c'etait bien une double avance : la case derriere la sautee doit etre src
        square_behind_skipped = EDGE_NEIGHBOR[skipped_sq][OPPOSITE_DIR[forward_dir]]
        if square_behind_skipped != src:
            return None

        return (skipped_sq, dest)

    # verifie si l'un des autres joueurs vient d'etre mate par mover
    def _check_mate(self, mover):
        for player in self.players:
            if player is mover:
                continue

            king = None
            for piece in self.board.get_pieces(player.color):
                if piece.get_symbol() == "K":
                    king = piece
                    break

            if king is not None and king.is_checkmate(self.board):
                self.winner = mover
                self.loser = player
                return

    # vrai si la partie a un gagnant
    def is_over(self) -> bool:
        return self.winner is not None

    # retourne le gagnant ou None
    def get_winner(self):
        return self.winner

    def __repr__(self):
        return f"Game(current={self.current_player.color}, over={self.is_over()})"
