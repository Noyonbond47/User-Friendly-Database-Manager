import sys
import os
import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as b
from ttkbootstrap.constants import *
import database_manager as dbm
import table_ui # Import the new UI module
from ui_theme import AppTheme # Import the new theme class
from custom_widgets import CustomButton # Import our new custom button

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class App(b.Window):
    def __init__(self):
        # Use a modern theme from ttkbootstrap
        super().__init__(themename="litera")

        # Create an instance of our UI theme template
        self.theme = AppTheme()

        self.title("🗃️ Database Manager")
        self.geometry("500x450")
        self.iconbitmap(resource_path("app_icon.ico")) # Set the window icon
        self.minsize(450, 400)

        # --- Main Frame ---
        main_frame = b.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # --- Create Database Section ---
        create_frame = b.LabelFrame(main_frame, text="Create New Database", padding="10")
        create_frame.pack(fill="x", pady=5)

        self.new_db_name_var = tk.StringVar()
        b.Label(create_frame, text="Name:").pack(side="left", padx=(0, 5))
        db_name_entry = b.Entry(create_frame, textvariable=self.new_db_name_var)
        db_name_entry.pack(side="left", fill="x", expand=True, padx=5)
        # --- Using our new CustomButton with the theme ---
        create_button = CustomButton(create_frame, text="Create", theme=self.theme, command=self.create_database)
        create_button.pack(side="left", pady=2)

        # --- Manage Existing Databases Section ---
        manage_frame = b.LabelFrame(main_frame, text="Manage Existing Databases", padding="10")
        manage_frame.pack(fill="both", expand=True, pady=5)

        # Listbox to show databases
        list_frame = b.Frame(manage_frame) # Frame to hold listbox and scrollbar
        list_frame.pack(pady=5, fill="both", expand=True)

        self.db_listbox = tk.Listbox(list_frame, height=10, borderwidth=0, highlightthickness=0)
        self.db_listbox.pack(side="left", fill="both", expand=True)
        self.db_listbox.bind("<<ListboxSelect>>", self.on_db_select)
        self.db_listbox.bind("<Double-1>", self.select_database) # Add double-click handler

        # Scrollbar for the listbox
        scrollbar = b.Scrollbar(list_frame, orient="vertical", command=self.db_listbox.yview, bootstyle="round")
        scrollbar.pack(side="right", fill="y")
        self.db_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons for actions
        button_frame = b.Frame(manage_frame)
        button_frame.pack(fill="x", pady=(5, 0))
        button_frame.columnconfigure((0, 1, 2), weight=1) # Make buttons expand equally

        self.select_button = b.Button(button_frame, text="Open", command=self.select_database, state="disabled", bootstyle="primary")
        self.select_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.export_sql_button = b.Button(button_frame, text="Export SQL", command=self.export_database_as_sql, state="disabled", bootstyle="info")
        self.export_sql_button.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.delete_button = b.Button(button_frame, text="Delete", command=self.delete_database, state="disabled", bootstyle="danger-outline")
        self.delete_button.grid(row=0, column=2, sticky="ew", padx=(5, 0))

        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = b.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=5)
        status_bar.pack(side="bottom", fill="x")

        # Initial population of the list
        self.refresh_database_list()

    def refresh_database_list(self):
        """Clears and repopulates the database listbox."""
        self.db_listbox.delete(0, tk.END)
        databases = dbm.list_databases()
        for db in databases:
            self.db_listbox.insert(tk.END, db)
        self.on_db_select() # Update button states

    def create_database(self):
        """Handles the create database button click."""
        db_name = self.new_db_name_var.get().strip()

        if not db_name.isidentifier():
            messagebox.showerror("Invalid Name", f"'{db_name}' is not a valid name. Please use letters, numbers, and underscores, and do not start with a number.", parent=self)
            return

        success, message = dbm.create_database(db_name)
        if success:
            messagebox.showinfo("Success", message)
            self.new_db_name_var.set("") # Clear the entry box
            # UX Improvement: Automatically select the new database
            self.refresh_database_list()
            for i, item in enumerate(self.db_listbox.get(0, tk.END)):
                if item == db_name:
                    self.db_listbox.selection_set(i)
                    self.db_listbox.see(i)
                    self.on_db_select()
                    break
        else:
            messagebox.showerror("Error", message)

    def delete_database(self):
        """Handles the delete database button click."""
        selected_indices = self.db_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select a database to delete.")
            return

        db_name = self.db_listbox.get(selected_indices[0])
        
        # Confirmation dialog
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to permanently delete the '{db_name}' database and all its contents?"
        )

        if confirm:
            success, message = dbm.delete_database(db_name)
            if success:
                messagebox.showinfo("Success", message)
                self.refresh_database_list()
            else:
                # Provide a more helpful error message, especially for permission issues.
                error_detail = (
                    f"Could not delete the database '{db_name}'.\n\n"
                    f"Details: {message}\n\n"
                    "This might be a permissions issue. Please try running the application "
                    "with administrator privileges or check the folder's permissions."
                )
                messagebox.showerror("Deletion Failed", error_detail)

    def select_database(self, event=None):
        """Handles the select database action (button click or double-click)."""
        selected_indices = self.db_listbox.curselection()
        if not selected_indices:
            return
        
        db_name = self.db_listbox.get(selected_indices[0])
        # Open the Table Manager window, passing the root window and the db_name
        table_ui.TableManagerWindow(self, db_name)
    def on_db_select(self, event=None):
        """Enables/disables buttons based on listbox selection."""
        if self.db_listbox.curselection():
            self.delete_button.config(state="normal")
            self.select_button.config(state="normal")
            self.export_sql_button.config(state="normal")
        else:
            self.delete_button.config(state="disabled")
            self.select_button.config(state="disabled")
            self.export_sql_button.config(state="disabled")

    def export_database_as_sql(self):
        """Handles exporting the selected database to a .sql file."""
        selected_indices = self.db_listbox.curselection()
        if not selected_indices:
            return

        db_name = self.db_listbox.get(selected_indices[0])

        default_export_dir = dbm.get_default_export_dir()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".sql",
            filetypes=[("SQL files", "*.sql"), ("All files", "*.*")],
            title=f"Export '{db_name}' as SQL",
            initialdir=default_export_dir,
            initialfile=f"{db_name}_dump.sql"
        )

        if not filepath:
            return # User cancelled

        success, message = dbm.dump_database_to_sql(db_name, filepath)
        if success:
            messagebox.showinfo("Export Successful", message, parent=self)
        else:
            messagebox.showerror("Export Failed", message, parent=self)

if __name__ == "__main__":
    # Ensure the root directory exists before starting the app
    dbm.initialize_root_directory()
    app = App()
    app.mainloop()
