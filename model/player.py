from abc import ABC, abstractmethod
from model.ai import MinimaxThread


class Player(ABC):
    # classe de base pour un joueur (humain ou ia)
    def __init__(self, color: str):
        self.color = color
        self.is_eliminated = False

    # retourne le coup choisi par ce joueur (synchrone, surtout utile pour les tests)
    @abstractmethod
    def choose_move(self, board):
        pass

    # appele a chaque frame par le controleur quand c'est le tour de ce joueur
    # les sous-classes asynchrones (ia) lancent/surveillent leur thread ici
    def tick(self, board, player_order: list) -> None:
        _, _ = board, player_order

    # vrai si le joueur a un coup pret a etre joue
    def is_ready(self) -> bool:
        return False

    # vrai si le joueur est en train de calculer (utile pour l'affichage)
    def is_thinking(self) -> bool:
        return False

    def __repr__(self):
        return f"Player({self.color})"


class HumanPlayer(Player):
    # joueur humain : le coup vient des clics, pas de calcul ici
    def choose_move(self, board):
        return None


class AIPlayer(Player):
    # joueur ia : delegue le calcul a un thread minimax
    def __init__(self, color: str, depth: int = 2):
        super().__init__(color)
        self.depth = depth
        self._thread = None
        self._started = False

    # demarre le thread minimax au premier tick du tour
    def tick(self, board, player_order: list) -> None:
        if not self._started:
            self._thread = MinimaxThread(board, self.color, self.depth, player_order)
            self._thread.start()
            self._started = True

    # vrai tant que le thread minimax tourne
    def is_thinking(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # vrai quand le thread a fini : le controleur peut recuperer le resultat
    def is_ready(self) -> bool:
        return self._thread is not None and not self._thread.is_alive()

    # retourne (src, dest) une fois le thread termine, puis reinitialise l'etat interne
    def get_result(self):
        if self._thread is None or self._thread.is_alive():
            return None
        result = self._thread.result
        self._thread = None
        self._started = False
        return result

    # fallback synchrone (non utilise par gamecontroller, conserve pour les tests)
    def choose_move(self, board):
        from model.ai import best_move
        return best_move(board, self.color, self.depth, [self.color])
