import pygame
from model.pieces.queen  import Queen
from model.pieces.rook   import Rook
from model.pieces.bishop import Bishop
from model.pieces.knight import Knight

# les 4 choix de promotion possibles : (classe, nom_fichier_sprite, symbole)
CHOICES = [
    (Queen,  "queen",  "Q"),
    (Rook,   "rook",   "R"),
    (Bishop, "bishop", "B"),
    (Knight, "knight", "N"),
]

_PANEL_W = 220
_PANEL_H = 80
_CELL_W  = _PANEL_W // 4


class PromotionView:
    # panneau d'overlay pour choisir la piece de promotion

    def __init__(self, window, sprites: dict):
        self.window = window
        self.sprites = sprites
        # rectangle pygame du panneau, mis a jour dans draw()
        self._rect = None

    # dessine le panneau centre sur la fenetre, avec un sprite et un libelle par choix
    def draw(self, color: str):
        ww, wh = self.window.get_size()
        x = (ww - _PANEL_W) // 2
        y = (wh - _PANEL_H) // 2

        panel = pygame.Rect(x, y, _PANEL_W, _PANEL_H)
        self._rect = panel

        pygame.draw.rect(self.window, (40, 40, 40), panel)
        pygame.draw.rect(self.window, (200, 200, 200), panel, 2)

        font = pygame.font.SysFont("monospace", 13)

        for i, (cls, name, symbol) in enumerate(CHOICES):
            cell_x = x + i * _CELL_W
            cell_rect = pygame.Rect(cell_x, y, _CELL_W, _PANEL_H)
            pygame.draw.rect(self.window, (60, 60, 60), cell_rect)
            pygame.draw.rect(self.window, (120, 120, 120), cell_rect, 1)

            sprite = self.sprites.get((color, symbol))
            if sprite is not None:
                sw, sh = sprite.get_size()
                self.window.blit(sprite, (cell_x + (_CELL_W - sw) // 2, y + 4))

            label = font.render(name[0].upper() + name[1:], True, (220, 220, 220))
            lw = label.get_width()
            self.window.blit(label, (cell_x + (_CELL_W - lw) // 2, y + _PANEL_H - 18))

    # retourne la classe de piece cliquee, ou None si en dehors du panneau
    def piece_at(self, mouse_pos):
        if self._rect is None or not self._rect.collidepoint(mouse_pos):
            return None
        rx = mouse_pos[0] - self._rect.x
        i = rx // _CELL_W
        if 0 <= i < len(CHOICES):
            return CHOICES[i][0]
        return None
