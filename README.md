# VIM TODO LIST (Curses)

A terminal-based, Vim-inspired todo list manager written in Python using the `curses` library. Features include:

- Fast keyboard navigation (Vim-style: j/k/g/G, etc.)
- Add, edit, delete, and toggle todos
- Visual mode for multi-line selection and yanking
- Yank/copy and paste todos using the system clipboard
- Undo/redo support
- Persistent storage in `todos.json`
- Colorful, modern TUI

## Usage

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   # or, if using pyproject.toml:
   pip install .
   ```
   (Requires Python 3.7+, `pyperclip`, and `curses`)

2. **(Recommended) Install as a CLI tool:**
   ```sh
   pip install .
   ```
   This will install the `vimtodo` command globally.

3. **Run the app:**
   ```sh
   vimtodo
   ```
   Or, if not installed as a CLI tool:
   ```sh
   python main.py
   ```

## Keybindings

| Key         | Action                                 |
|-------------|----------------------------------------|
| q           | Quit                                   |
| i           | Insert new todo                        |
| I           | Insert subtask under current todo      |
| e           | Edit selected todo                     |
| x           | Toggle completion                      |
| d           | Delete todo (copies to clipboard)      |
| y           | Yank (copy) todo to clipboard          |
| p           | Paste todos from clipboard             |
| V           | Enter visual mode                      |
| u           | Undo                                   |
| U           | Redo                                   |
| w           | Save todos                             |
| j/k         | Move down/up                           |
| g/G         | Move to top/bottom                     |
| ESC         | Cancel/exit to normal mode             |

## File Storage

Todos are now saved in `~/.todos.json` (a hidden file in your home directory).

## Requirements
- Python 3.7+
- `pyperclip` (for clipboard support)
- `curses` (standard on Unix/macOS)

## Notes
- Clipboard support requires `pyperclip` and may need `xclip`/`xsel` on Linux.
- Designed for macOS/Linux terminals. Windows support may require additional setup.

## License
MIT
