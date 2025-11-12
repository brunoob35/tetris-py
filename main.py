import arcade
from tetris.gui import MainMenuView
from tetris.constants import WINDOW_WIDTH, WINDOW_HEIGHT

def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, "Tetris (Arcade) - v1")
    window.show_view(MainMenuView())
    arcade.run()

if __name__ == "__main__":
    main()
