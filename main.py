#!/usr/bin/env python3
import curses
import json
import os
from typing import Any, Dict, List

import pyperclip  # Clipboard library


class TodoApp:
    def __init__(self):
        self.todos: List[Dict[str, Any]] = []
        self.current_path = [0]  # Path to current todo, e.g., [main, sub, ...]
        self.mode = "normal"  # normal, insert, command, visual
        self.command_buffer = ""
        self.message = ""
        self.filename = os.path.expanduser("~/.todos.json")  # Store in home as hidden file
        self.visual_start = None  # Start of visual selection (as path)
        self.visual_end = None  # End of visual selection (as path)
        self.undo_stack: List[List[Dict[str, Any]]] = []  # Stack for undo
        self.redo_stack: List[List[Dict[str, Any]]] = []  # Stack for redo
        self.load_todos()

    def get_todo_by_path(self, path):
        """Get a todo dict by its path (e.g., [2, 1] for 2nd subtask of 3rd main todo). Returns None if not found."""
        todo = None
        todos = self.todos
        for idx in path:
            if not (0 <= idx < len(todos)):
                return None
            todo = todos[idx]
            todos = todo.get("children", [])
        return todo

    def set_todo_by_path(self, path, new_todo):
        """Set a todo dict by its path."""
        todos = self.todos
        for idx in path[:-1]:
            todos = todos[idx].setdefault("children", [])
        todos[path[-1]] = new_todo

    def ensure_children(self, path):
        """Ensure the todo at path has a 'children' list."""
        todo = self.get_todo_by_path(path)
        if todo is not None and not isinstance(todo.get("children"), list):
            todo["children"] = []

    def load_todos(self):
        """Load todos from JSON file"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, "r") as f:
                    self.todos = json.load(f)
        except Exception as e:
            self.message = f"Error loading todos: {e}"

    def save_todos(self):
        """Save todos to JSON file"""
        try:
            with open(self.filename, "w") as f:
                json.dump(self.todos, f, indent=2)
            self.message = "Saved!"
        except Exception as e:
            self.message = f"Error saving: {e}"

    def push_undo(self):
        """Push the current state to the undo stack."""
        import copy

        self.undo_stack.append(copy.deepcopy(self.todos))

    def push_redo(self):
        """Push the current state to the redo stack."""
        import copy

        self.redo_stack.append(copy.deepcopy(self.todos))

    def undo(self):
        """Undo the last change."""
        if self.undo_stack:
            self.push_redo()  # Save current state to redo stack
            self.todos = self.undo_stack.pop()
            # After undo, update current_path to a valid todo if possible
            flat_paths = self.get_flattened_paths()
            if flat_paths:
                self.current_path = flat_paths[min(len(flat_paths) - 1, 0)]
            else:
                self.current_path = [0]
            self.message = "Undo performed!"
        else:
            self.message = "Nothing to undo!"

    def redo(self):
        """Redo the last undone change."""
        if self.redo_stack:
            self.push_undo()  # Save current state to undo stack
            self.todos = self.redo_stack.pop()
            # After redo, update current_path to a valid todo if possible
            flat_paths = self.get_flattened_paths()
            if flat_paths:
                self.current_path = flat_paths[min(len(flat_paths) - 1, 0)]
            else:
                self.current_path = [0]
            self.message = "Redo performed!"
        else:
            self.message = "Nothing to redo!"

    def add_todo(self, text: str):
        """Add a new todo item"""
        self.push_undo()  # Save current state for undo
        self.redo_stack.clear()  # Clear redo stack on a new change
        self.todos.append({"text": text, "completed": False})
        self.save_todos()  # Autosave after adding
        self.current_line = len(self.todos) - 1

    def edit_todo(self, text: str):
        """Edit the currently selected todo"""
        todo = self.get_todo_by_path(self.current_path)
        if todo is not None:
            self.push_undo()  # Save current state for undo
            self.redo_stack.clear()  # Clear redo stack on a new change
            todo["text"] = text
            self.save_todos()
            self.message = "Todo edited!"

    def toggle_todo(self):
        """Toggle completion status of current todo"""
        todo = self.get_todo_by_path(self.current_path)
        if todo is not None:
            self.push_undo()  # Save current state for undo
            self.redo_stack.clear()  # Clear redo stack on a new change
            todo["completed"] = not todo["completed"]
            self.save_todos()

    def delete_todo(self):
        """Delete current todo and copy it to the clipboard."""
        flat_paths = self.get_flattened_paths()
        try:
            idx = flat_paths.index(self.current_path)
        except ValueError:
            self.message = "No todo selected."
            return
        path = flat_paths[idx]
        todo = self.get_todo_by_path(path)
        if todo is not None:
            self.push_undo()  # Save current state for undo
            self.redo_stack.clear()  # Clear redo stack on a new change
            pyperclip.copy(todo["text"])
            # Remove the todo from its parent
            if len(path) == 1:
                del self.todos[path[0]]
            else:
                parent = self.get_todo_by_path(path[:-1])
                if parent and "children" in parent:
                    del parent["children"][path[-1]]
            self.save_todos()
            # Move cursor to previous or next todo
            flat_paths = self.get_flattened_paths()
            if flat_paths:
                self.current_path = flat_paths[max(0, idx - 1)]
            else:
                self.current_path = [0]
            self.message = f"Todo deleted and copied to clipboard!"

    def yank_todo(self):
        """Yank the current todo or selected range in visual mode to the clipboard."""
        if self.mode == "visual":
            # Visual mode for nested todos is not yet implemented, so just yank the current todo for now
            todo = self.get_todo_by_path(self.current_path)
            if todo:
                pyperclip.copy(todo["text"])
                self.message = "Todo yanked to clipboard! (visual mode placeholder)"
            self.exit_visual_mode()
        else:
            # Yank the current line
            todo = self.get_todo_by_path(self.current_path)
            if todo:
                pyperclip.copy(todo["text"])
                self.message = "Todo yanked to clipboard!"

    def paste_todo(self):
        """Paste the content from the clipboard as new todos below the current todo."""
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content.strip():
                self.push_undo()  # Save current state for undo
                self.redo_stack.clear()  # Clear redo stack on a new change
                lines = clipboard_content.splitlines()
                # Insert as siblings after the current todo
                flat_paths = self.get_flattened_paths()
                try:
                    idx = flat_paths.index(self.current_path)
                except ValueError:
                    idx = -1
                path = flat_paths[idx] if idx != -1 else [0]
                if len(path) == 1:
                    insert_at = path[0] + 1
                    for i, line in enumerate(lines):
                        self.todos.insert(insert_at + i, {"text": line, "completed": False})
                else:
                    parent = self.get_todo_by_path(path[:-1])
                    if parent and "children" in parent:
                        insert_at = path[-1] + 1
                        for i, line in enumerate(lines):
                            parent["children"].insert(insert_at + i, {"text": line, "completed": False})
                self.save_todos()
                self.message = f"Pasted {len(lines)} todos from clipboard!"
                # Move to the last pasted line
                flat_paths = self.get_flattened_paths()
                if flat_paths:
                    self.current_path = flat_paths[min(len(flat_paths) - 1, idx + len(lines))]
            else:
                self.message = "Clipboard is empty!"
        except pyperclip.PyperclipException as e:
            self.message = f"Error accessing clipboard: {e}"

    def get_flattened_paths(self):
        """Return a list of all todo paths in display order (for navigation)."""
        paths = []

        def recurse(todos, prefix):
            for idx, todo in enumerate(todos):
                path = prefix + [idx]
                paths.append(path)
                if todo.get("children"):
                    recurse(todo["children"], path)

        recurse(self.todos, [])
        return paths

    def move_up(self):
        """Move cursor up (vim k) using path navigation"""
        flat_paths = self.get_flattened_paths()
        try:
            idx = flat_paths.index(self.current_path)
            if idx > 0:
                self.current_path = flat_paths[idx - 1]
        except ValueError:
            if flat_paths:
                self.current_path = flat_paths[0]

    def move_down(self):
        """Move cursor down (vim j) using path navigation"""
        flat_paths = self.get_flattened_paths()
        try:
            idx = flat_paths.index(self.current_path)
            if idx < len(flat_paths) - 1:
                self.current_path = flat_paths[idx + 1]
        except ValueError:
            if flat_paths:
                self.current_path = flat_paths[-1]

    def move_to_top(self):
        """Move to first line (vim gg) using path navigation"""
        flat_paths = self.get_flattened_paths()
        if flat_paths:
            self.current_path = flat_paths[0]

    def move_to_bottom(self):
        """Move to last line (vim G) using path navigation"""
        flat_paths = self.get_flattened_paths()
        if flat_paths:
            self.current_path = flat_paths[-1]

    def enter_visual_mode(self):
        """Enter visual mode"""
        self.mode = "visual"
        self.visual_start = self.current_line
        self.visual_end = self.current_line
        self.message = "Visual mode"

    def exit_visual_mode(self):
        """Exit visual mode"""
        self.mode = "normal"
        self.visual_start = None
        self.visual_end = None
        self.message = ""

    def add_subtask(self, text: str):
        """Add a subtask under the current todo"""
        self.push_undo()  # Save current state for undo
        self.redo_stack.clear()  # Clear redo stack on a new change
        parent = self.get_todo_by_path(self.current_path)
        if parent is not None:
            if "children" not in parent or not isinstance(parent["children"], list):
                parent["children"] = []
            parent["children"].append({"text": text, "completed": False})
            self.save_todos()  # Autosave after adding subtask
            # Move cursor to the new subtask
            self.current_path = self.current_path + [len(parent["children"]) - 1]
            self.message = "Subtask added!"
        else:
            self.message = "No parent todo selected."


def draw_screen(stdscr, app):
    """Draw the main screen with support for nested todos"""
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    # Title
    title = "VIM TODO"
    stdscr.addstr(
        0, (width - len(title)) // 2, title, curses.color_pair(4) | curses.A_BOLD
    )

    # Helper to flatten todos for display and navigation
    def render_todos(todos, path_prefix, y, indent):
        for idx, todo in enumerate(todos):
            if y >= height - 3:
                break
            path = path_prefix + [idx]
            checkbox = "[x]" if todo.get("completed") else "[ ]"
            text = f"{'  '*indent}{checkbox} {todo['text']}"

            # Highlight if this is the current path
            if path == app.current_path:
                attr = curses.color_pair(2) | curses.A_BOLD
            elif todo.get("completed"):
                attr = curses.color_pair(3) | curses.A_DIM
            else:
                attr = curses.color_pair(1)

            try:
                stdscr.addstr(y, 2, text[: width - 4], attr)
            except curses.error:
                pass
            y += 1
            # Render children recursively
            if todo.get("children"):
                y = render_todos(todo["children"], path, y, indent + 1)
        return y

    # Render all todos
    render_todos(app.todos, [], 2, 0)

    # Status line
    status_y = height - 2
    mode_text = f"-- {app.mode.upper()} --" if app.mode != "normal" else ""

    # Command buffer for command mode
    if app.mode == "command":
        command_text = f":{app.command_buffer}"
        stdscr.addstr(status_y, 0, command_text, curses.color_pair(1))
    else:
        stdscr.addstr(status_y, 0, mode_text, curses.color_pair(1))

    # Message line
    if app.message:
        try:
            stdscr.addstr(
                status_y + 1, 0, app.message[: width - 1], curses.color_pair(1)
            )
        except curses.error:
            pass

    # Help line
    help_text = (
        "q:quit  i:insert  I:subtask  e:edit  x:toggle  d:delete  y:yank  p:paste  "
        "V:visual  u:undo  U:redo  w:save  g/G:top/bottom  ESC:cancel/normal"
    )
    try:
        stdscr.addstr(height - 1, 0, help_text[: width - 1], curses.color_pair(5))
    except curses.error:
        pass

    stdscr.refresh()


def handle_insert_mode(stdscr, app, edit_mode=False, insert_subtask=False):
    """Handle insert mode for adding or editing a todo, or inserting a subtask"""
    curses.curs_set(1)  # Enable block cursor
    height, width = stdscr.getmaxyx()

    # Prepopulate input buffer with current todo text if editing
    input_text = ""
    if edit_mode:
        todo = app.get_todo_by_path(app.current_path)
        if todo:
            input_text = todo["text"]

    cursor_pos = len(input_text)

    while True:
        # Clear and redraw screen
        stdscr.clear()

        # Draw title
        title = "VIM TODO LIST"
        stdscr.addstr(
            0, (width - len(title)) // 2, title, curses.color_pair(4) | curses.A_BOLD
        )

        # Draw existing todos
        start_y = 2
        for i, todo in enumerate(app.todos):
            y = start_y + i
            if y >= height - 5:
                break
            checkbox = "[x]" if todo["completed"] else "[ ]"
            text = f"{checkbox} {todo['text']}"

            if todo["completed"]:
                attr = curses.color_pair(3) | curses.A_DIM
            else:
                attr = curses.color_pair(1)

            try:
                stdscr.addstr(y, 2, text[: width - 4], attr)
            except curses.error:
                pass

        # Show input prompt
        prompt_y = height - 3
        prompt = "Edit todo: " if edit_mode else "Enter todo: "
        stdscr.addstr(prompt_y, 0, prompt, curses.color_pair(1))
        stdscr.addstr(prompt_y, len(prompt), input_text, curses.color_pair(1))

        # Show help
        help_text = "ESC:cancel ENTER:save"
        stdscr.addstr(height - 1, 0, help_text, curses.color_pair(5))

        # Position cursor
        stdscr.move(prompt_y, len(prompt) + cursor_pos)
        stdscr.refresh()

        # Get key
        key = stdscr.getch()

        if key == 27:  # Escape
            app.message = "Cancelled"
            app.mode = "normal"
            break

        elif key == ord("\n") or key == curses.KEY_ENTER:
            if input_text.strip():
                if edit_mode:
                    app.edit_todo(input_text.strip())
                elif insert_subtask:
                    app.add_subtask(input_text.strip())
                else:
                    app.add_todo(input_text.strip())
            app.mode = "normal"
            break

        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if cursor_pos > 0:
                input_text = input_text[: cursor_pos - 1] + input_text[cursor_pos:]
                cursor_pos -= 1

        elif key == curses.KEY_LEFT:
            if cursor_pos > 0:
                cursor_pos -= 1

        elif key == curses.KEY_RIGHT:
            if cursor_pos < len(input_text):
                cursor_pos += 1

        elif 32 <= key <= 126:  # Printable characters
            input_text = input_text[:cursor_pos] + chr(key) + input_text[cursor_pos:]
            cursor_pos += 1

    curses.curs_set(0)  # Disable block cursor


def main(stdscr=None):
    """Main application loop"""
    if stdscr is None:
        curses.wrapper(main)
        return

    curses.curs_set(0)  # Hide cursor initially
    stdscr.timeout(100)  # Non-blocking input with 100ms timeout

    # Setup colors
    curses.start_color()
    curses.use_default_colors()

    # Define color pairs
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_CYAN, -1)

    stdscr.bkgd(" ", curses.color_pair(1))

    app = TodoApp()
    gg_pressed = False

    while True:
        curses.curs_set(0)  # Ensure cursor is hidden in normal mode
        draw_screen(stdscr, app)

        try:
            key = stdscr.getch()
        except KeyboardInterrupt:
            break

        if key == -1:
            continue

        app.message = ""

        if key == ord("q"):
            break

        elif key == ord("j") or key == curses.KEY_DOWN:
            app.move_down()

        elif key == ord("k") or key == curses.KEY_UP:
            app.move_up()

        elif key == ord("g"):
            if gg_pressed:
                app.move_to_top()
                gg_pressed = False
            else:
                gg_pressed = True
                continue

        elif key == ord("G"):
            app.move_to_bottom()

        elif key == ord("i"):
            app.mode = "insert"
            handle_insert_mode(stdscr, app)

        elif key == ord("e"):
            app.mode = "insert"
            handle_insert_mode(stdscr, app, edit_mode=True)

        elif key == ord("x"):
            app.toggle_todo()

        elif key == ord("d"):
            app.delete_todo()

        elif key == ord("y"):
            app.yank_todo()

        elif key == ord("p"):
            app.paste_todo()

        elif key == ord("V"):
            app.enter_visual_mode()

        elif key == ord("u"):
            app.undo()

        elif key == ord("U"):
            app.redo()

        elif key == 27:  # Escape
            app.exit_visual_mode()

        elif key == ord(":"):
            app.mode = "command"
            app.command_buffer = ""

        elif key == ord("w"):
            app.save_todos()

        elif key == ord("I"):
            # Insert a subtask under the current todo
            app.mode = "insert_subtask"
            handle_insert_mode(stdscr, app, insert_subtask=True)

        if key != ord("g"):
            gg_pressed = False


if __name__ == "__main__":
    main()
