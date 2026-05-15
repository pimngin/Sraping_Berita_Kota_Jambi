# main.py
import tkinter as tk
from app.ui.main_window import MainWindow


def main():
    root = tk.Tk()
    root.iconbitmap("assets/favicon.ico")
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
