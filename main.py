import arcade
from tetris.view.gui import LoginView
from tetris.core.constants import WINDOW_WIDTH, WINDOW_HEIGHT

def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, "Tetris retrô")
    view = LoginView()
    window.show_view(view)
    arcade.run()

if __name__ == "__main__":
    main()