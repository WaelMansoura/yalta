from controller.game_controller import GameController
from model.player import HumanPlayer, AIPlayer

# configuration des joueurs.
# remplace humanplayer par aiplayer(color, depth=n) pour rendre un joueur ia.

players = [
    # HumanPlayer("white"),
    # HumanPlayer("red"),
    # HumanPlayer("black"),
    AIPlayer("red",   depth=2),
    AIPlayer("black", depth=5),
    AIPlayer("white", depth=2),
]


if __name__ == "__main__":
    controller = GameController(players)
    controller.run()
