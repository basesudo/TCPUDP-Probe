import tkinter as tk
from gui import TCPToolGUI


def main():
    """主函数"""
    root = tk.Tk()
    app = TCPToolGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
