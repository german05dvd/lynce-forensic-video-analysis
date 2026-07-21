import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.gui import ForensicsGUI
import tkinter as tk

def main():
    root = tk.Tk()
    # Intenta forzar un estilo moderno si está disponible
    try:
        import sv_ttk
        sv_ttk.set_theme("dark")
    except ImportError:
        pass
    app = ForensicsGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()