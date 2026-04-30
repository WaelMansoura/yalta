import pygame
from model.game import Game
from model.player import HumanPlayer
from model.topology import EDGE_NEIGHBOR
from view.board_view import BoardView
from view.promotion_view import PromotionView


class GameController:
    # boucle principale : lit les evenements, fait jouer l'ia, dessine la vue

    def __init__(self, players=None):
        pygame.init()
        self.window = pygame.display.set_mode((800, 800))
        self.clock = pygame.time.Clock()

        if players is None:
            players = [HumanPlayer("white"), HumanPlayer("red"), HumanPlayer("black")]
        self.game = Game(players)
        self.view = BoardView(self.window)

        # la vue s'inscrit comme observateur du modele : game.notify() appelle view.update()
        self.game.add_observer(self.view)

        self.selected_piece = None
        self.legal_moves = []
        self.ep_moves = set()
        self.castle_moves = set()

        self._promo_view = PromotionView(self.window, self.view.sprites)

    # liste des couleurs dans l'ordre des tours, en commencant par le joueur courant
    def _player_order(self):
        all_colors = [player.color for player in self.game.players]
        current_index = self.game.current_index
        return all_colors[current_index:] + all_colors[:current_index]

    # boucle principale : 60 fps, evenements -> tick ia -> rendu
    def run(self):
        while True:
            self.clock.tick(60)
            current_player = self.game.current_player

            self._update_window_title(current_player)

            self._handle_events()
            if not self.game.needs_promotion():
                self._tick_ai()

            # le controleur est le seul a appeler view.draw() dans la boucle
            normal_highlights = set(self.legal_moves) - self.ep_moves - self.castle_moves
            self.view.draw(
                self.game.board,
                highlights        = normal_highlights,
                selected          = self.selected_piece.position if self.selected_piece else None,
                checked_kings     = self._checked_kings(),
                ep_highlights     = self.ep_moves,
                castle_highlights = self.castle_moves,
            )

            if self.game.needs_promotion():
                self._promo_view.draw(current_player.color)

            pygame.display.flip()

    # met a jour le titre de la fenetre selon l'etat courant
    def _update_window_title(self, current_player):
        if self.game.needs_promotion():
            caption = f"Yalta Chess — {current_player.color}: choose promotion"
        elif current_player.is_thinking():
            caption = f"Yalta Chess — {current_player.color}'s turn (thinking…)"
        else:
            caption = f"Yalta Chess — {current_player.color}'s turn"
        pygame.display.set_caption(caption)

    # delegue au joueur courant le soin de demarrer/surveiller son calcul
    def _tick_ai(self):
        if self.game.is_over():
            return

        current_player = self.game.current_player

        # humanplayer ne fait rien dans tick ; aiplayer gere son thread en interne
        current_player.tick(self.game.board, self._player_order())

        if not current_player.is_ready():
            # humain (jamais pret ici) ou ia encore en calcul
            return

        move = current_player.get_result()

        if move is None:
            self.game.next_turn()
            return

        src, dest = move
        piece = self.game.board.get_piece(src)
        if piece is None:
            self.game.next_turn()
            return

        self.game.apply_move(piece, dest)
        if self.game.needs_promotion():
            # l'ia promeut systematiquement en reine
            from model.pieces.queen import Queen
            self.game.confirm_promotion(Queen)
        if self.game.is_over():
            self._show_winner()

    # boucle d'evenements pygame : quitter ou clic gauche
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.game.needs_promotion():
                    self._handle_promotion_click(event.pos)
                else:
                    self._handle_click(event.pos)

    # clic sur le panneau de promotion : applique le choix
    def _handle_promotion_click(self, mouse_pos):
        piece_class = self._promo_view.piece_at(mouse_pos)
        if piece_class is None:
            return
        self.game.confirm_promotion(piece_class)
        if self.game.is_over():
            self._show_winner()

    # clic sur le plateau : selectionne une piece ou joue le coup
    def _handle_click(self, mouse_pos):
        clicked_sq = self.view.square_at(mouse_pos)
        if clicked_sq is None:
            return

        current_color = self.game.current_player.color

        if self.selected_piece is not None:
            if clicked_sq in self.legal_moves:
                self.game.apply_move(self.selected_piece, clicked_sq)
                self._deselect()
                if self.game.is_over():
                    self._show_winner()
                return

            piece_at_click = self.game.board.get_piece(clicked_sq)
            if piece_at_click and piece_at_click.color == current_color:
                self._select(piece_at_click)
            else:
                self._deselect()
            return

        piece_at_click = self.game.board.get_piece(clicked_sq)
        if piece_at_click and piece_at_click.color == current_color:
            self._select(piece_at_click)

    # selectionne une piece et calcule ses coups legaux
    def _select(self, piece):
        self.selected_piece = piece
        self.legal_moves = piece.get_legal_moves(self.game.board)
        self.ep_moves, self.castle_moves = self._classify_moves(piece)

    # deselectionne la piece courante
    def _deselect(self):
        self.selected_piece = None
        self.legal_moves = []
        self.ep_moves = set()
        self.castle_moves = set()

    # repartit les coups legaux entre prise en passant, roque et coups normaux (pour l'affichage)
    def _classify_moves(self, piece):
        ep_moves = set()
        castle_moves = set()

        if piece.get_symbol() == "P":
            en_passant = self.game.board.en_passant
            if en_passant and en_passant[0] in self.legal_moves:
                ep_moves.add(en_passant[0])

        if piece.get_symbol() == "K" and not piece.has_moved:
            for direction in "NESW":
                one_step = EDGE_NEIGHBOR[piece.position][direction]
                if one_step is None:
                    continue
                two_steps = EDGE_NEIGHBOR[one_step][direction]
                if two_steps in self.legal_moves:
                    castle_moves.add(two_steps)

        return ep_moves, castle_moves

    # cases des rois actuellement en echec (pour les surligner en rouge)
    def _checked_kings(self):
        checked = set()
        for sq, piece in self.game.board.squares.items():
            if piece is None or piece.get_symbol() != "K":
                continue
            if self.game.board.is_king_in_check(piece.color):
                checked.add(sq)
        return checked

    # affiche le gagnant pendant 4 secondes puis ferme la fenetre
    def _show_winner(self):
        font = pygame.font.SysFont("monospace", 48)
        txt = font.render(f"{self.game.winner.color} wins!", True, (255, 215, 0))
        self.window.blit(txt, (200, 370))
        pygame.display.flip()
        pygame.time.wait(4000)
        pygame.quit()
        raise SystemExit
