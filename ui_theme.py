class AppTheme:
    """
    A centralized class to hold all UI styling information (colors, fonts, etc.).
    This acts as a reusable template for the entire application.
    """
    def __init__(self):
        # --- Color Palette ---
        self.COLOR_PRIMARY = "#007bff"
        self.COLOR_SUCCESS = "#28a745"
        self.COLOR_SUCCESS_HOVER = "#218838"
        self.COLOR_INFO = "#17a2b8"
        self.COLOR_DANGER = "#dc3545"
        self.COLOR_DANGER_OUTLINE = "#dc3545"
        self.COLOR_DISABLED = "#d3d3d3"
        self.COLOR_WHITE = "#ffffff"
        self.COLOR_LIGHT_GRAY = "#a3a3a3"

        # --- Font Palette ---
        self.FONT_PRIMARY = ("Segoe UI", 10)
        self.FONT_BOLD = ("Segoe UI", 10, "bold")

        # --- Widget-specific Styles ---
        self.button = {
            "normal_bg": self.COLOR_SUCCESS,
            "hover_bg": self.COLOR_SUCCESS_HOVER,
            "disabled_bg": self.COLOR_DISABLED,
            "normal_fg": self.COLOR_WHITE,
            "disabled_fg": self.COLOR_LIGHT_GRAY,
            "font": self.FONT_BOLD
        }
