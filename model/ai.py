import os
import threading
import multiprocessing
from model.board import Board

# valeurs des pieces pour l'evaluation
PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 1000}

INF = float("inf")


# evalue le plateau du point de vue de color : ses pieces moins celles de tous les adversaires
def evaluate(board: Board, color: str) -> float:
    score = 0
    for piece in board.squares.values():
        if piece is None:
            continue
        v = PIECE_VALUES.get(piece.get_symbol(), 0)
        if piece.color == color:
            score += v
        else:
            score -= v
    return score


# generateur de tous les coups legaux d'une couleur sous forme (case_depart, case_arrivee)
def _all_moves(board: Board, color: str):
    for piece in board.get_pieces(color):
        for dest in piece.get_legal_moves(board):
            yield piece.position, dest


# retourne un nouveau plateau avec le coup applique (sans effets de bord cote game)
def _apply_on_clone(board: Board, src: str, dest: str):
    clone = board.clone()
    piece = clone.get_piece(src)
    clone.apply_move(piece, dest)
    return clone


# minimax recursif a 3 joueurs : ai_color est max, les 2 autres sont min combines
# player_order : liste des couleurs dans l'ordre des tours a partir de l'etat courant
# turn_index : index dans player_order du joueur dont c'est le tour
def minimax(board: Board, depth: int, player_order: list, turn_index: int,
            ai_color: str, alpha: float, beta: float) -> float:
    current_color = player_order[turn_index % len(player_order)]

    # limite de profondeur atteinte
    if depth == 0:
        return evaluate(board, ai_color)

    moves = list(_all_moves(board, current_color))
    if not moves:
        # aucun coup : on saute le tour de ce joueur
        next_index = (turn_index + 1) % len(player_order)
        return minimax(board, depth - 1, player_order, next_index, ai_color, alpha, beta)

    if current_color == ai_color:
        # noeud max
        best = -INF
        for src, dest in moves:
            child = _apply_on_clone(board, src, dest)
            next_index = (turn_index + 1) % len(player_order)
            val = minimax(child, depth - 1, player_order, next_index, ai_color, alpha, beta)
            best = max(best, val)
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        return best
    else:
        # noeud min (un des adversaires)
        best = INF
        for src, dest in moves:
            child = _apply_on_clone(board, src, dest)
            next_index = (turn_index + 1) % len(player_order)
            val = minimax(child, depth - 1, player_order, next_index, ai_color, alpha, beta)
            best = min(best, val)
            beta = min(beta, best)
            if alpha >= beta:
                break
        return best


# evalue UN seul coup racine : applique le coup sur un clone puis lance minimax dessus.
# fonction de haut niveau (pas imbriquee) pour que multiprocessing puisse la pickler.
def _evaluate_root_move(args):
    board, src, dest, depth, player_order, ai_color = args
    child = _apply_on_clone(board, src, dest)
    val = minimax(child, depth - 1, player_order, 1, ai_color, -INF, INF)
    return val, src, dest


# version sequentielle : retourne (src, dest) du meilleur coup (utilisee comme fallback)
def best_move(board: Board, ai_color: str, depth: int, player_order: list):
    moves = list(_all_moves(board, ai_color))
    if not moves:
        return None

    best_val = -INF
    chosen = moves[0]
    alpha = -INF
    beta = INF

    for src, dest in moves:
        child = _apply_on_clone(board, src, dest)
        val = minimax(child, depth - 1, player_order, 1, ai_color, alpha, beta)
        if val > best_val:
            best_val = val
            chosen = (src, dest)
        alpha = max(alpha, best_val)

    return chosen


# version parallele : distribue les coups racine entre plusieurs processus (root splitting).
# chaque processus evalue independamment un sous-ensemble de coups via minimax sequentiel.
# on rassemble les valeurs et on garde le coup au score maximal.
def parallel_best_move(board: Board, ai_color: str, depth: int, player_order: list,
                       num_workers: int = None):
    moves = list(_all_moves(board, ai_color))
    if not moves:
        return None

    # un seul coup : pas besoin de paralleliser, on appelle directement le sequentiel
    if len(moves) == 1:
        return moves[0]

    # par defaut : autant de processus que de coeurs cpu, plafonne au nombre de coups
    if num_workers is None:
        num_workers = max(1, os.cpu_count() or 1)
    num_workers = min(num_workers, len(moves))

    # un seul worker : evite le surcout de multiprocessing
    if num_workers <= 1:
        return best_move(board, ai_color, depth, player_order)

    # prepare les arguments pour chaque coup racine
    tasks = [(board, src, dest, depth, player_order, ai_color) for src, dest in moves]

    # pool de processus : chaque tache _evaluate_root_move tourne sur un coeur dedie.
    # imap_unordered renvoie les resultats des qu'ils arrivent (ordre non garanti).
    with multiprocessing.Pool(processes=num_workers) as pool:
        results = list(pool.imap_unordered(_evaluate_root_move, tasks))

    # selectionne le coup au score maximal
    _, best_src, best_dest = max(results, key=lambda r: r[0])
    return best_src, best_dest


class MinimaxThread(threading.Thread):
    # execute parallel_best_move dans un thread d'arriere-plan ; resultat stocke dans self.result.
    # le thread sert juste a ne pas bloquer la boucle pygame ; le vrai parallelisme cpu
    # est realise par le pool de processus interne a parallel_best_move.
    def __init__(self, board: Board, ai_color: str, depth: int, player_order: list,
                 num_workers: int = None):
        super().__init__(daemon=True)
        # on travaille sur un snapshot isole pour eviter les races avec le thread principal
        self.board = board.clone()
        self.ai_color = ai_color
        self.depth = depth
        self.player_order = player_order
        self.num_workers = num_workers
        self.result = None

    # point d'entree du thread : calcule le meilleur coup en parallele
    def run(self):
        self.result = parallel_best_move(
            self.board, self.ai_color, self.depth, self.player_order, self.num_workers
        )
