#!/usr/bin/env python3
import curses
import json
import os
from typing import Any, Dict, List

import pyperclip  # Clipboard library


class TodoApp:
    def __init__(self):
        self.todos: List[Dict[str, Any]] = []
        self.current_line = 0
        self.mode = "normal"  # normal, insert, command, visual
        self.command_buffer = ""
        self.message = ""
        self.filename = os.path.expanduser("~/.todos.json")  # Store in home as hidden file
        self.visual_start = None  # Start of visual selection
        self.visual_end = None  # End of visual selection
        self.undo_stack: List[List[Dict[str, Any]]] = []  # Stack for undo
        self.redo_stack: List[List[Dict[str, Any]]] = []  # Stack for redo
        self.load_todos()

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
        self.undo_stack.append([todo.copy() for todo in self.todos])

    def push_redo(self):
        """Push the current state to the redo stack."""
        self.redo_stack.append([todo.copy() for todo in self.todos])

    def undo(self):
        """Undo the last change."""
        if self.undo_stack:
            self.push_redo()  # Save current state to redo stack
            self.todos = self.undo_stack.pop()  # Restore the last state from undo stack
            self.message = "Undo performed!"
            if self.current_line >= len(self.todos):
                self.current_line = len(self.todos) - 1
        else:
            self.message = "Nothing to undo!"

    def redo(self):
        """Redo the last undone change."""
        if self.redo_stack:
            self.push_undo()  # Save current state to undo stack
            self.todos = self.redo_stack.pop()  # Restore the last state from redo stack
            self.message = "Redo performed!"
            if self.current_line >= len(self.todos):
                self.current_line = len(self.todos) - 1
        else:
            self.message = "Nothing to redo!"

    def add_todo(self, text: str):
        """Add a new todo item"""
        self.push_undo()  # Save current state for undo
        self.redo_stack.clear()  # Clear redo stack on a new change
        self.todos.append({"text": text, "completed": False})
        self.current_line = len(self.todos) - 1

    def edit_todo(self, text: str):
        """Edit the currently selected todo"""
        if 0 <= self.current_line < len(self.todos):
            self.push_undo()  # Save current state for undo
            self.redo_stack.clear()  # Clear redo stack on a new change
            self.todos[self.current_line]["text"] = text
            self.message = "Todo edited!"

    def toggle_todo(self):
        """Toggle completion status of current todo"""
        if 0 <= self.current_line < len(self.todos):
            self.push_undo()  # Save current state for undo
            self.redo_stack.clear()  # Clear redo stack on a new change
            self.todos[self.current_line]["completed"] = not self.todos[
                self.current_line
            ]["completed"]

    def delete_todo(self):
        """Delete current todo and copy it to the clipboard."""
        if 0 <= self.current_line < len(self.todos):
            self.push_undo()  # Save current state for undo
            self.redo_stack.clear()  # Clear redo stack on a new change
            text_to_clipboard = self.todos[self.current_line]["text"]
            pyperclip.copy(text_to_clipboard)  # Copy to OS clipboard
            del self.todos[self.current_line]
            if self.current_line >= len(self.todos) and self.todos:
                self.current_line = len(self.todos) - 1
            elif not self.todos:
                self.current_line = 0
            self.message = f"Todo deleted and copied to clipboard!"

    def yank_todo(self):
        """Yank the current todo or selected range in visual mode to the clipboard."""
        if self.mode == "visual":
            # Yank the selected range
            start = min(self.visual_start, self.visual_end)
            end = max(self.visual_start, self.visual_end)
            yanked_lines = [self.todos[i]["text"] for i in range(start, end + 1)]
            pyperclip.copy("\n".join(yanked_lines))  # Copy to OS clipboard
            self.message = f"Yanked {len(yanked_lines)} todos to clipboard!"
            self.exit_visual_mode()
        else:
            # Yank the current line
            if 0 <= self.current_line < len(self.todos):
                text_to_clipboard = self.todos[self.current_line]["text"]
                pyperclip.copy(text_to_clipboard)  # Copy to OS clipboard
                self.message = "Todo yanked to clipboard!"

    def paste_todo(self):
        """Paste the content from the clipboard as new todos below the current line."""
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content.strip():
                self.push_undo()  # Save current state for undo
                self.redo_stack.clear()  # Clear redo stack on a new change
                lines = (
                    clipboard_content.splitlines()
                )  # Split clipboard content into lines
                for i, line in enumerate(lines):
                    self.todos.insert(
                        self.current_line + 1 + i, {"text": line, "completed": False}
                    )
                self.message = f"Pasted {len(lines)} todos from clipboard!"
                self.current_line += len(lines)  # Move to the last pasted line
            else:
                self.message = "Clipboard is empty!"
        except pyperclip.PyperclipException as e:
            self.message = f"Error accessing clipboard: {e}"

    def move_up(self):
        """Move cursor up (vim k)"""
        if self.current_line > 0:
            self.current_line -= 1
            if self.mode == "visual":
                self.visual_end = self.current_line

    def move_down(self):
        """Move cursor down (vim j)"""
        if self.current_line < len(self.todos) - 1:
            self.current_line += 1
            if self.mode == "visual":
                self.visual_end = self.current_line

    def move_to_top(self):
        """Move to first line (vim gg)"""
        self.current_line = 0
        if self.mode == "visual":
            self.visual_end = self.current_line

    def move_to_bottom(self):
        """Move to last line (vim G)"""
        if self.todos:
            self.current_line = len(self.todos) - 1
            if self.mode == "visual":
                self.visual_end = self.current_line

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


def draw_screen(stdscr, app):
    """Draw the main screen"""
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    # Title
    title = "VIM TODO"
    stdscr.addstr(
        0, (width - len(title)) // 2, title, curses.color_pair(4) | curses.A_BOLD
    )

    # Todo items
    start_y = 2
    for i, todo in enumerate(app.todos):
        y = start_y + i
        if y >= height - 3:  # Leave space for status line
            break

        # Checkbox
        checkbox = "[x]" if todo["completed"] else "[ ]"
        text = f"{checkbox} {todo['text']}"

        # Set colors and attributes
        if i == app.current_line:
            # Current line - highlighted
            attr = curses.color_pair(2) | curses.A_BOLD
        elif (
            app.mode == "visual"
            and app.visual_start is not None
            and min(app.visual_start, app.visual_end)
            <= i
            <= max(app.visual_start, app.visual_end)
        ):
            # Visual mode - highlighted selection
            attr = curses.color_pair(5) | curses.A_REVERSE
        elif todo["completed"]:
            # Completed items - dimmed green
            attr = curses.color_pair(3) | curses.A_DIM
        else:
            # Normal items - bright green
            attr = curses.color_pair(1)

        try:
            stdscr.addstr(y, 2, text[: width - 4], attr)
        except curses.error:
            pass

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
    help_text = "q:quit i:insert e:edit x:toggle d:delete y:yank p:paste V:visual u:undo U:redo :w:save"
    try:
        stdscr.addstr(height - 1, 0, help_text[: width - 1], curses.color_pair(5))
    except curses.error:
        pass

    stdscr.refresh()


def handle_insert_mode(stdscr, app, edit_mode=False):
    """Handle insert mode for adding or editing a todo"""
    curses.curs_set(1)  # Enable block cursor
    height, width = stdscr.getmaxyx()

    # Prepopulate input buffer with current todo text if editing
    input_text = ""
    if edit_mode and 0 <= app.current_line < len(app.todos):
        input_text = app.todos[app.current_line]["text"]

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

        if key != ord("g"):
            gg_pressed = False


if __name__ == "__main__":
    main()
