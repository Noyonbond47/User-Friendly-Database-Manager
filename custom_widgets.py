import tkinter as tk

class CustomButton(tk.Canvas):
    """
    A professional, custom-drawn, modern-looking button widget.
    This widget is theme-aware and reads its styling from a theme object.
    """
    def __init__(self, parent, text, theme, command=None, state=tk.NORMAL, **kwargs):
        # --- Widget Setup ---
        # To make the canvas background match the themed window, we get the theme's color.
        try:
            theme_bg = parent.winfo_toplevel().style.colors.bg
        except (AttributeError, tk.TclError):
            theme_bg = parent.cget("background") # Fallback for standard tkinter

        super().__init__(parent, width=100, height=35, bg=theme_bg, borderwidth=0, highlightthickness=0, **kwargs)
        
        self.command = command
        self.theme = theme
        self.state = state
        self._text = text
        self._hovering = False

        # --- Draw the initial button state ---
        self._draw_button()
        
        # --- Bind events for interaction ---
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw_button(self):
        """Draws the button based on its current state."""
        self.delete("all") # Clear the canvas before redrawing
        width = self.winfo_width()
        height = self.winfo_height()
        radius = height // 2

        # Determine colors from the theme object
        if self.state == tk.DISABLED:
            bg_color = self.theme.button["disabled_bg"]
            fg_color = self.theme.button["disabled_fg"]
        elif self._hovering:
            bg_color = self.theme.button["hover_bg"]
            fg_color = self.theme.button["normal_fg"]
        else:
            bg_color = self.theme.button["normal_bg"]
            fg_color = self.theme.button["normal_fg"]

        # Draw the rounded rectangle shape
        self.create_oval(0, 0, height, height, fill=bg_color, outline=bg_color)
        self.create_oval(width - height, 0, width, height, fill=bg_color, outline=bg_color)
        self.create_rectangle(radius, 0, width - radius, height, fill=bg_color, outline=bg_color)
        
        # Draw the button text
        self.create_text(width / 2, height / 2, text=self._text, fill=fg_color, font=self.theme.button["font"])

    def _on_enter(self, event):
        if self.state == tk.NORMAL:
            self._hovering = True
            self._draw_button()

    def _on_leave(self, event):
        self._hovering = False
        self._draw_button()

    def _on_click(self, event):
        if self.state == tk.NORMAL and self.command:
            self.command()

    def config(self, **kwargs):
        """Allows configuring the button's state after creation."""
        if 'state' in kwargs:
            self.state = kwargs['state']
            self._draw_button()
        super().config(**kwargs)

