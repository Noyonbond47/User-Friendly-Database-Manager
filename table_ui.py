import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter import filedialog
import database_manager as dbm
import csv

class ColumnDialog(simpledialog.Dialog):
    """A dialog for adding or editing a single column's definition."""
    def __init__(self, parent, db_name, existing_column=None, all_column_names=None, add_mode=False):
        self.db_name = db_name
        self.add_mode = add_mode # True if adding a column to an existing table
        # Names of other columns, to prevent PK conflicts
        self.other_column_names = [c['name'] for c in (all_column_names or []) if c['name'] != (existing_column or {}).get('name')]
        self.all_columns = all_column_names or []
        self.column_data = existing_column or {}
        self.result = None
        title = "Edit Column" if existing_column else "Add New Column"
        super().__init__(parent, title)

    def body(self, master):
        # Column Name
        ttk.Label(master, text="Column Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.name_var = tk.StringVar(value=self.column_data.get("name", ""))
        self.name_entry = ttk.Entry(master, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=2)

        # Data Type
        ttk.Label(master, text="Data Type:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.type_var = tk.StringVar(value=self.column_data.get("type", "TEXT"))
        self.type_combo = ttk.Combobox(master, textvariable=self.type_var, state="readonly",
                                       values=["TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"])
        self.type_combo.bind("<<ComboboxSelected>>", self.update_states)
        self.type_combo.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5, pady=2)

        # Constraints
        constraints_frame = ttk.Frame(master)
        constraints_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=5)
        self.pk_var = tk.BooleanVar(value=self.column_data.get("pk", False))
        self.pk_check = ttk.Checkbutton(constraints_frame, text="Primary Key", variable=self.pk_var, command=self.update_states)
        self.pk_check.pack(side="left")

        self.autoincrement_var = tk.BooleanVar(value=self.column_data.get("autoincrement", False))
        self.not_null_var = tk.BooleanVar(value=self.column_data.get("not_null", False))
        self.unique_var = tk.BooleanVar(value=self.column_data.get("unique", False))

        self.autoincrement_check = ttk.Checkbutton(constraints_frame, text="Autoincrement", variable=self.autoincrement_var)
        self.autoincrement_check.pack(side="left", padx=5)
        self.not_null_check = ttk.Checkbutton(constraints_frame, text="Not Null", variable=self.not_null_var)
        self.not_null_check.pack(side="left", padx=5)
        self.unique_check = ttk.Checkbutton(constraints_frame, text="Unique", variable=self.unique_var)
        self.unique_check.pack(side="left", padx=5)

        # Foreign Key Section
        fk_frame = ttk.LabelFrame(master, text="Foreign Key Constraint", padding=5)
        fk_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        self.is_fk_var = tk.BooleanVar(value=bool(self.column_data.get("fk_table")))
        self.fk_check = ttk.Checkbutton(fk_frame, text="Is a Foreign Key", variable=self.is_fk_var, command=self.update_states)
        self.fk_check.grid(row=0, column=0, columnspan=2, sticky="w")

        self.fk_table_label = ttk.Label(fk_frame, text="References Table:")
        self.fk_table_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.fk_table_var = tk.StringVar(value=self.column_data.get("fk_table", ""))
        self.fk_table_combo = ttk.Combobox(fk_frame, textvariable=self.fk_table_var, state="readonly")
        self.fk_table_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.fk_table_combo['values'] = dbm.list_tables(self.db_name)
        self.fk_table_combo.bind("<<ComboboxSelected>>", self.on_fk_table_select)

        self.fk_column_label = ttk.Label(fk_frame, text="References Column:")
        self.fk_column_label.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.fk_column_var = tk.StringVar(value=self.column_data.get("fk_column", ""))
        self.fk_column_combo = ttk.Combobox(fk_frame, textvariable=self.fk_column_var, state="disabled")
        self.fk_column_combo.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.fk_column_combo.bind("<<ComboboxSelected>>", self.on_fk_column_select)

        fk_frame.columnconfigure(1, weight=1)
        self.update_states() # Set initial state of all widgets

        # If in "add column" mode, disable unsupported options
        if self.add_mode:
            self.pk_check.config(state="disabled")
            self.pk_var.set(False)
            self.fk_check.config(state="disabled")
            self.is_fk_var.set(False)
            self.update_states() # Run again to reflect disabled PK/FK

        if self.fk_table_var.get(): self.on_fk_table_select() # Populate columns if editing

        return self.name_entry

    def update_states(self, event=None):
        """Central function to manage the state of all widgets based on user selections."""
        is_fk = self.is_fk_var.get()
        is_pk = self.pk_var.get()
        is_integer = self.type_var.get() == "INTEGER"

        # --- Foreign Key has top priority ---
        if is_fk:
            # If it's a foreign key, most other attributes are inherited or irrelevant
            self.pk_var.set(False)
            self.pk_check.config(state="disabled")
            self.autoincrement_check.config(state="disabled")
            self.not_null_check.config(state="disabled")
            self.unique_check.config(state="disabled")
            self.type_combo.config(state="disabled")
            self.fk_table_combo.config(state="readonly")
            self.fk_column_combo.config(state="readonly" if self.fk_column_combo['values'] else "disabled")
            return

        # --- If not a Foreign Key, manage Primary Key and other constraints ---
        self.pk_check.config(state="normal")
        self.type_combo.config(state="readonly")
        self.fk_table_combo.config(state="disabled")
        self.fk_column_combo.config(state="disabled")

        if is_pk:
            self.not_null_var.set(True)
            self.unique_var.set(True) # A PK is implicitly unique
            self.not_null_check.config(state="disabled")
            self.unique_check.config(state="disabled")
        else:
            self.not_null_check.config(state="normal")
            self.unique_check.config(state="normal")

        # Autoincrement is only available for an INTEGER PRIMARY KEY
        if is_pk and is_integer:
            self.autoincrement_check.config(state="normal")
        else:
            self.autoincrement_var.set(False)
            self.autoincrement_check.config(state="disabled")

    def on_fk_table_select(self, event=None):
        table = self.fk_table_var.get()
        valid_cols = dbm.get_valid_fk_target_columns(self.db_name, table)
        self.fk_column_combo['values'] = valid_cols
        if valid_cols:
            self.fk_column_combo.config(state="readonly")
            self.fk_column_combo.set(valid_cols[0])
            self.on_fk_column_select() # Auto-select type
        else:
            self.fk_column_combo.set("")
            self.fk_column_combo.config(state="disabled")
            messagebox.showwarning("No Valid Columns", f"Table '{table}' has no PRIMARY KEY or UNIQUE columns to reference.", parent=self)

    def on_fk_column_select(self, event=None):
        parent_table = self.fk_table_var.get()
        parent_column = self.fk_column_var.get()

        if not parent_table or not parent_column:
            return

        # If the user hasn't typed a name for this new column, suggest one.
        if not self.name_var.get().strip():
            singular_table = parent_table[:-1] if parent_table.lower().endswith('s') else parent_table
            suggested_name = f"{singular_table}_{parent_column}"
            self.name_var.set(suggested_name)

        col_type = dbm.get_column_type(self.db_name, parent_table, parent_column)
        if col_type:
            self.type_var.set(col_type)
            self.update_states() # Re-evaluate widget states

    def apply(self):
        name = self.name_var.get().strip()
        if not name.isidentifier():
            messagebox.showerror("Invalid Name", f"'{name}' is not a valid identifier.", parent=self)
            self.result = None
            return

        if self.pk_var.get() and any(c.get('pk') for c in self.all_columns if c.get('name') != self.column_data.get('name')):
             messagebox.showerror("Invalid Constraint", "Another column is already the Primary Key. A table can only have one Primary Key.", parent=self)
             self.result = None
             return

        self.result = {
            "name": name,
            "type": self.type_var.get(),
            "pk": self.pk_var.get(),
            "autoincrement": self.autoincrement_var.get() if self.pk_var.get() else False,
            "not_null": self.not_null_var.get(),
            "unique": self.unique_var.get(),
            "fk_table": self.fk_table_var.get() if self.is_fk_var.get() else None,
            "fk_column": self.fk_column_var.get() if self.is_fk_var.get() else None,
        }

class CreateTableDialog(simpledialog.Dialog):
    """Dialog to define a new table, including its name and columns."""
    def __init__(self, parent, db_name):
        self.db_name = db_name
        # Start with a default primary key column
        self.columns = [{
            "name": "ID", "type": "INTEGER",
            "pk": True, "autoincrement": True,
            "not_null": True, "unique": True,
            "fk_table": None, "fk_column": None
        }]
        self.result = None
        super().__init__(parent, "Create New Table")

    def body(self, master):
        self.geometry("600x400")
        # Table Name
        name_frame = ttk.Frame(master)
        name_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(name_frame, text="Table Name:").pack(side="left")
        self.table_name_var = tk.StringVar()
        self.table_name_entry = ttk.Entry(name_frame, textvariable=self.table_name_var)
        self.table_name_entry.pack(side="left", fill="x", expand=True, padx=5)

        # Columns
        cols_frame = ttk.LabelFrame(master, text="Columns", padding=10)
        cols_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(cols_frame, columns=("Type", "Constraints"), show="tree headings")
        self.tree.heading("#0", text="Column Name")
        self.tree.heading("Type", text="Data Type")
        self.tree.heading("Constraints", text="Constraints")
        self.tree.column("#0", width=150, stretch=tk.YES)
        self.tree.column("Type", width=100)
        self.tree.pack(side="left", fill="both", expand=True)

        btn_frame = ttk.Frame(cols_frame)
        btn_frame.pack(side="left", fill="y", padx=(10, 0))
        ttk.Button(btn_frame, text="Add...", command=self.add_column).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Edit...", command=self.edit_column).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Remove", command=self.remove_column).pack(fill="x", pady=2)

        self.refresh_tree()
        return self.table_name_entry

    def refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for i, col in enumerate(self.columns):
            display_name = col['name']
            constraints = []
            if col.get('pk'):
                constraints.append("PK")
                display_name = f"{col['name']} (PK)"
            if col.get('autoincrement'): constraints.append("AI")
            if col.get('not_null'): constraints.append("NN")
            if col.get('unique'): constraints.append("UQ")
            if col.get('fk_table'): constraints.append(f"FK->{col['fk_table']}({col['fk_column']})")
            self.tree.insert("", "end", iid=i, text=display_name, values=(col['type'], ", ".join(constraints)))

    def add_column(self):
        dialog = ColumnDialog(self, self.db_name, all_column_names=self.columns)
        if dialog.result:
            self.columns.append(dialog.result)
            self.refresh_tree()

    def edit_column(self):
        selected = self.tree.focus()
        if not selected:
            return
        col_index = int(selected)
        dialog = ColumnDialog(self, self.db_name, existing_column=self.columns[col_index], all_column_names=self.columns)
        if dialog.result:
            self.columns[col_index] = dialog.result
            self.refresh_tree()

    def remove_column(self):
        selected = self.tree.focus()
        if not selected:
            return
        if messagebox.askyesno("Confirm", "Remove selected column definition?", parent=self):
            self.columns.pop(int(selected))
            self.refresh_tree()

    def apply(self):
        table_name = self.table_name_var.get().strip()
        if not table_name.isidentifier():
            messagebox.showerror("Invalid Name", f"'{table_name}' is not a valid table name.", parent=self)
            self.result = None
            return
        if not any(c.get('pk') for c in self.columns):
            messagebox.showerror("Missing Primary Key", "A table must have at least one column designated as a Primary Key.", parent=self)
            self.result = None
            return
        self.result = (table_name, self.columns)

class RowDataDialog(simpledialog.Dialog):
    """Dialog to add or edit a row in a table."""
    def __init__(self, parent, db_name, table_name, initial_data=None):
        self.db_name = db_name
        self.table_name = table_name
        self.initial_data = initial_data or {}
        self.widgets = {}
        self.result = None
        title = f"Edit Row in '{table_name}'" if initial_data else f"Add Row to '{table_name}'"
        super().__init__(parent, title)

    def body(self, master):
        self.columns = dbm.get_table_columns(self.db_name, self.table_name)
        self.fk_info = dbm.get_foreign_key_info(self.db_name, self.table_name)
        self.pk_names = dbm.get_primary_key_columns(self.db_name, self.table_name)
        
        # Check for autoincrement PK for "add" mode
        is_autoincrement_add_mode = (
            not self.initial_data and
            len(self.pk_names) == 1 and
            next((c['type'] for c in self.columns if c['name'] == self.pk_names[0]), None) == 'INTEGER'
        )

        for i, col in enumerate(self.columns):
            col_name = col['name']
            
            # In "add" mode, don't show an input for an autoincrement PK
            if is_autoincrement_add_mode and col_name in self.pk_names:
                ttk.Label(master, text=f"{col_name}:").grid(row=i, column=0, sticky="w", padx=5, pady=2)
                ttk.Label(master, text="(Autogenerated)").grid(row=i, column=1, sticky="w", padx=5, pady=2)
                continue

            ttk.Label(master, text=f"{col_name}:").grid(row=i, column=0, sticky="w", padx=5, pady=2)
            
            # If it's a foreign key, use a Combobox
            if col_name in self.fk_info:
                fk = self.fk_info[col_name]
                parent_values = dbm.get_parent_table_values(self.db_name, fk['table'], fk['to'])
                combo = ttk.Combobox(master, state="readonly", values=parent_values)
                if self.initial_data.get(col_name) in parent_values:
                    combo.set(self.initial_data.get(col_name))
                combo.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
                self.widgets[col_name] = combo
            else: # Otherwise, use a standard Entry
                entry = ttk.Entry(master)
                entry.insert(0, self.initial_data.get(col_name, ""))
                entry.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
                self.widgets[col_name] = entry

            # In "edit" mode, disable primary key fields
            if self.initial_data and col_name in self.pk_names:
                self.widgets[col_name].config(state="disabled")

        master.columnconfigure(1, weight=1)
        # Focus first editable widget
        if self.widgets:
            return self.widgets.get(next(iter(self.widgets.keys())), None)

    def apply(self):
        data = {}
        for col_name, widget in self.widgets.items():
            value = widget.get()
            # For non-text types, an empty string should be NULL.
            # This is a simplification; a more robust solution would check column type.
            if value == '':
                data[col_name] = None
            else:
                data[col_name] = value
        
        self.result = data

class TableManagerWindow(tk.Toplevel):
    def __init__(self, parent, db_name):
        super().__init__(parent)
        self.db_name = db_name
        self.title(f"Table Manager - {db_name}")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()

        paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, padx=10, pady=10)

        # Left Pane: Table List
        left_frame = ttk.LabelFrame(paned_window, text="Tables", padding=5)
        self.table_list = tk.Listbox(left_frame)
        self.table_list.pack(fill="both", expand=True)
        self.table_list.bind("<<ListboxSelect>>", self.on_table_select)
        paned_window.add(left_frame, weight=1)

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="Create Table...", command=self.create_table).pack(side="left", fill="x", expand=True, padx=(0,2))
        self.delete_btn = ttk.Button(btn_frame, text="Delete Table", state="disabled", command=self.delete_table)
        self.delete_btn.pack(side="left", fill="x", expand=True, padx=(2,0))

        # Right Pane: Notebook with Structure and Data tabs
        notebook = ttk.Notebook(paned_window)
        paned_window.add(notebook, weight=3)

        # -- Structure Tab --
        structure_tab = ttk.Frame(notebook, padding=5)
        notebook.add(structure_tab, text="Structure")
        
        self.details_tree = ttk.Treeview(structure_tab, columns=("Name", "Type", "NotNull", "PK", "Unique", "ForeignKey"), show="headings")
        self.details_tree.heading("Name", text="Column Name")
        self.details_tree.heading("Type", text="Type")
        self.details_tree.heading("NotNull", text="Not Null")
        self.details_tree.heading("PK", text="Primary Key")
        self.details_tree.heading("Unique", text="Unique")
        self.details_tree.heading("ForeignKey", text="Foreign Key")

        self.details_tree.column("Name", width=150, stretch=tk.YES)
        self.details_tree.column("Type", width=100, stretch=tk.YES)
        self.details_tree.column("NotNull", width=60, anchor="center")
        self.details_tree.column("PK", width=80, anchor="center")
        self.details_tree.column("Unique", width=60, anchor="center")
        self.details_tree.column("ForeignKey", width=150, stretch=tk.YES)
        self.details_tree.pack(fill="both", expand=True)

                
        structure_btn_frame = ttk.Frame(structure_tab)
        structure_btn_frame.pack(fill="x", pady=(5, 0))
        self.add_column_btn = ttk.Button(structure_btn_frame, text="Add Column...", command=self.add_column_to_table, state="disabled")
        self.add_column_btn.pack(side="left", padx=(0, 5))
        
        self.remove_column_btn = ttk.Button(structure_btn_frame, text="Remove Selected Column", command=self.remove_column_from_table, state="disabled")
        self.remove_column_btn.pack(side="left")

        # -- Data Tab --
        data_tab = ttk.Frame(notebook, padding=5)
        notebook.add(data_tab, text="Data")

        data_btn_frame = ttk.Frame(data_tab)
        data_btn_frame.pack(fill="x", pady=(0, 5))
        self.add_row_btn = ttk.Button(data_btn_frame, text="Add Row...", command=self.add_row, state="disabled")
        self.add_row_btn.pack(side="left", padx=(0, 5))
        self.delete_row_btn = ttk.Button(data_btn_frame, text="Delete Selected Row", command=self.delete_row, state="disabled")
        self.delete_row_btn.pack(side="left", padx=(0, 5))
        self.export_csv_btn = ttk.Button(data_btn_frame, text="Export to CSV...", command=self.export_to_csv, state="disabled")
        self.export_csv_btn.pack(side="left")

        self.data_tree = ttk.Treeview(data_tab, show="headings")
        # Bind double-click to edit row
        self.data_tree.bind("<Double-1>", self.edit_row)
        
        data_v_scroll = ttk.Scrollbar(data_tab, orient="vertical", command=self.data_tree.yview)
        data_h_scroll = ttk.Scrollbar(data_tab, orient="horizontal", command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=data_v_scroll.set, xscrollcommand=data_h_scroll.set)
        
        data_v_scroll.pack(side="right", fill="y")
        data_h_scroll.pack(side="bottom", fill="x")
        self.data_tree.pack(fill="both", expand=True)

        self.refresh_table_list()

    def refresh_table_list(self):
        self.table_list.delete(0, tk.END)
        for table in dbm.list_tables(self.db_name):
            self.table_list.insert(tk.END, table)
        self.on_table_select()

    def on_table_select(self, event=None):
        # Clear both views
        for i in self.details_tree.get_children(): self.details_tree.delete(i)
        for i in self.data_tree.get_children(): self.data_tree.delete(i)
        self.data_tree.unbind("<B1>") # Clear old header sort bindings
        self.data_tree["columns"] = []

        selection = self.table_list.curselection()
        data_tree_selection = self.data_tree.selection()

        if not selection:
            self.delete_btn.config(state="disabled")
            self.add_row_btn.config(state="disabled")
            self.add_column_btn.config(state="disabled")
            self.remove_column_btn.config(state="disabled")
            self.export_csv_btn.config(state="disabled")
            self.delete_row_btn.config(state="disabled")
            return

        self.delete_btn.config(state="normal")
        self.add_row_btn.config(state="normal")
        self.add_column_btn.config(state="normal")
        self.export_csv_btn.config(state="normal")
        self.on_structure_select() # Set initial state for remove button
        self.delete_row_btn.config(state="normal" if data_tree_selection else "disabled")
        table_name = self.table_list.get(selection[0])
        
        # --- Populate Structure Tab ---
        columns = dbm.get_full_table_definition(self.db_name, table_name)
        for col in columns:
            pk_val = '✔' if col.get('pk') else ''
            not_null_val = '✔' if col.get('not_null') else ''
            # A PK is implicitly unique, so show the checkmark for both.
            unique_val = '✔' if col.get('unique') or col.get('pk') else ''
            
            fk_val = ''
            if col.get('fk_table'):
                fk_val = f"-> {col['fk_table']}({col['fk_column']})"
                
            values = (
                col['name'], col['type'], not_null_val, pk_val, unique_val, fk_val
            )
            # The 'text' property is kept for compatibility with the 'remove column' logic
            self.details_tree.insert("", "end", values=values, text=col['name'])

        # --- Populate Data Tab ---
        headers, rows = dbm.get_table_data(self.db_name, table_name)
        self.data_tree["columns"] = headers
        for header in headers:
            self.data_tree.heading(header, text=header)
            self.data_tree.column(header, width=100, stretch=tk.YES)
        
        for row in rows:
            self.data_tree.insert("", "end", values=row)
        
        # Update delete button state based on data tree selection
        self.data_tree.bind("<<TreeviewSelect>>", lambda e: self.delete_row_btn.config(state="normal"))
        self.details_tree.bind("<<TreeviewSelect>>", self.on_structure_select)
        
    def on_structure_select(self, event=None):
        """Enables/disables the remove column button based on selection."""
        state = "normal" if self.details_tree.selection() else "disabled"
        self.remove_column_btn.config(state=state)

    def create_table(self):
        dialog = CreateTableDialog(self, self.db_name)
        if dialog.result:
            table_name, columns = dialog.result
            success, message = dbm.create_table(self.db_name, table_name, columns)
            if success:
                messagebox.showinfo("Success", message, parent=self)
                self.refresh_table_list()
            else:
                messagebox.showerror("Error", message, parent=self)

    def add_column_to_table(self):
        selection = self.table_list.curselection()
        if not selection: return
        table_name = self.table_list.get(selection[0])

        existing_cols_info = dbm.get_table_columns(self.db_name, table_name)
        
        # Open the dialog in "add mode"
        dialog = ColumnDialog(self, self.db_name, all_column_names=existing_cols_info, add_mode=True)
        if dialog.result:
            new_column_def = dialog.result
            
            success, message = dbm.add_column(self.db_name, table_name, new_column_def)
            if success:
                messagebox.showinfo("Success", message, parent=self)
                self.on_table_select() # Refresh view
            else:
                messagebox.showerror("Error", message, parent=self)

    def remove_column_from_table(self):
        table_selection = self.table_list.curselection()
        col_selection = self.details_tree.selection()
        if not table_selection or not col_selection:
            return
        
        table_name = self.table_list.get(table_selection[0])
        item = self.details_tree.item(col_selection[0])
        column_to_remove = item['text']
        
        confirm = messagebox.askyesno(
            "Confirm Column Deletion",
            f"Are you sure you want to permanently delete the column '{column_to_remove}' from table '{table_name}'?\n\nThis action requires recreating the table and cannot be undone.",
            parent=self
        )
        
        if confirm:
            success, message = dbm.remove_column(self.db_name, table_name, column_to_remove)
            if success:
                messagebox.showinfo("Success", message, parent=self)
                self.on_table_select()
            else:
                messagebox.showerror("Error", message, parent=self)

    def add_row(self):
        selection = self.table_list.curselection()
        if not selection: return
        table_name = self.table_list.get(selection[0])
        
        dialog = RowDataDialog(self, self.db_name, table_name)
        if dialog.result:
            success, message = dbm.insert_row(self.db_name, table_name, dialog.result)
            if success:
                # Refresh the data view to show the new row
                self.on_table_select()
                # Go to the last row
                last_item = self.data_tree.get_children()[-1]
                self.data_tree.selection_set(last_item)
                self.data_tree.focus(last_item)
                self.data_tree.see(last_item)
            else:
                messagebox.showerror("Error", message, parent=self)

    def edit_row(self, event=None):
        """Handles double-click on a row to edit it."""
        selection = self.data_tree.selection()
        if not selection: return
        item_id = selection[0]
        
        table_name = self.table_list.get(self.table_list.curselection()[0])
        headers = self.data_tree['columns']
        row_values = self.data_tree.item(item_id, 'values')
        initial_data = dict(zip(headers, row_values))

        pk_names = dbm.get_primary_key_columns(self.db_name, table_name)
        pk_dict = {pk: initial_data[pk] for pk in pk_names}

        dialog = RowDataDialog(self, self.db_name, table_name, initial_data=initial_data)
        if dialog.result:
            # Don't include PKs in the data to be updated
            update_data = {k: v for k, v in dialog.result.items() if k not in pk_names}
            success, message = dbm.update_row(self.db_name, table_name, pk_dict, update_data)
            if success:
                self.on_table_select()
                # Re-select the edited row
                self.data_tree.selection_set(item_id)
                self.data_tree.focus(item_id)
            else:
                messagebox.showerror("Update Failed", message, parent=self)

    def delete_row(self):
        """Deletes the selected row from the data view."""
        selection = self.data_tree.selection()
        if not selection: return

        table_name = self.table_list.get(self.table_list.curselection()[0])
        pk_names = dbm.get_primary_key_columns(self.db_name, table_name)
        if not pk_names:
            messagebox.showerror("Error", f"Cannot delete row: Table '{table_name}' has no primary key.", parent=self)
            return

        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the selected row?", parent=self)
        if not confirm: return

        headers = self.data_tree['columns']
        row_values = self.data_tree.item(selection[0], 'values')
        pk_dict = {pk: row_values[headers.index(pk)] for pk in pk_names}

        success, message = dbm.delete_row(self.db_name, table_name, pk_dict)
        if success:
            self.on_table_select()
        else:
            messagebox.showerror("Deletion Failed", message, parent=self)

    def delete_table(self):
        selection = self.table_list.curselection()
        if not selection:
            return

        table_name = self.table_list.get(selection[0])

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to permanently delete the table '{table_name}'?\n\nThis action cannot be undone.",
            parent=self
        )

        if confirm:
            success, message = dbm.delete_table(self.db_name, table_name)
            if success:
                messagebox.showinfo("Success", message, parent=self)
                self.refresh_table_list()
            else:
                messagebox.showerror("Error", message, parent=self)

    def export_to_csv(self):
        """Handles exporting the current table's data to a CSV file."""
        selection = self.table_list.curselection()
        if not selection:
            return
        
        table_name = self.table_list.get(selection[0])
        
        default_export_dir = dbm.get_default_export_dir()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title=f"Export '{table_name}' to CSV",
            initialdir=default_export_dir,
            initialfile=f"{table_name}_export.csv"
        )
        
        if not filepath:
            return # User cancelled the dialog
            
        try:
            headers, rows = dbm.get_table_data(self.db_name, table_name)
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            messagebox.showinfo("Success", f"Data from '{table_name}' successfully exported to:\n{filepath}", parent=self)
        except (IOError, Exception) as e:
            messagebox.showerror("Export Failed", f"An error occurred while exporting the file:\n{e}", parent=self)