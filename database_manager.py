import os
import sqlite3

def get_app_data_dir():
    """
    Gets the standard application data directory for the current OS.
    Creates it if it doesn't exist. This is the robust way to store app data.
    """
    # For Windows, use the APPDATA environment variable
    app_data_path = os.getenv('APPDATA')
    if app_data_path:
        # Best practice is to create a folder for your app
        dir_path = os.path.join(app_data_path, "DatabaseManager")
    else:
        # Fallback for other OS or if APPDATA is not set
        dir_path = os.path.join(os.path.expanduser("~"), ".DatabaseManager")
    
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

APP_DATA_ROOT = get_app_data_dir()
DB_ROOT_DIR = os.path.join(APP_DATA_ROOT, "databases")

# --- Setup & Connection ---
def initialize_root_directory():
    """Ensures the root directory for databases exists."""
    os.makedirs(DB_ROOT_DIR, exist_ok=True)

def get_db_path(db_name):
    """Constructs the full path for a database file."""
    return os.path.join(DB_ROOT_DIR, f"{db_name}.db")

def get_db_connection(db_name):
    """Establishes a connection to the specified database."""
    db_path = get_db_path(db_name)
    try:
        conn = sqlite3.connect(db_path)
        # Enable foreign key support for the connection
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database {db_name}: {e}")
        return None

# --- Database Level Operations ---
def list_databases():
    """Returns a list of database names without the .db extension."""
    initialize_root_directory()
    try:
        files = [f for f in os.listdir(DB_ROOT_DIR) if f.endswith('.db')]
        return sorted([os.path.splitext(f)[0] for f in files])
    except OSError:
        return []

def get_default_export_dir():
    """
    Gets a default export directory inside the user's Documents folder.
    Creates it if it doesn't exist.
    """
    # os.path.expanduser("~") gets the user's home directory on any OS
    docs_path = os.path.join(os.path.expanduser("~"), "Documents")
    export_path = os.path.join(docs_path, "DatabaseManagerExports")
    
    os.makedirs(export_path, exist_ok=True)
    return export_path

def create_database(db_name):
    """Creates a new SQLite database file."""
    db_path = get_db_path(db_name)
    if os.path.exists(db_path):
        return False, f"Database '{db_name}' already exists."
    try:
        conn = sqlite3.connect(db_path)
        conn.close()
        return True, f"Database '{db_name}' created successfully."
    except sqlite3.Error as e:
        return False, f"Failed to create database: {e}"

def delete_database(db_name):
    """Deletes a database file."""
    db_path = get_db_path(db_name)
    if not os.path.exists(db_path):
        return False, f"Database '{db_name}' not found."
    try:
        os.remove(db_path)
        return True, f"Database '{db_name}' deleted successfully."
    except OSError as e:
        return False, str(e)

def dump_database_to_sql(db_name, output_filepath):
    """Dumps the entire database schema and data to a .sql file."""
    conn = get_db_connection(db_name)


    if not conn:
        return False, "Could not connect to the database."
    
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            for line in conn.iterdump():
                f.write('%s\n' % line)
        return True, f"Database successfully dumped to {output_filepath}"
    except (IOError, sqlite3.Error) as e:
        return False, f"Failed to dump database: {e}"
    finally:
        if conn:
            conn.close()

# --- Schema Introspection ---
def list_tables(db_name):
    """Lists all tables in a given database."""
    conn = get_db_connection(db_name)
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def get_table_columns(db_name, table_name):
    """
    Returns a list of column dictionaries for a given table, including their properties.
    Uses PRAGMA table_info.
    """
    conn = get_db_connection(db_name)
    if not conn:
        return []
    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        # Row: (cid, name, type, notnull, dflt_value, pk)
        cols = [{'name': row[1], 'type': row[2], 'notnull': row[3], 'pk': row[5]} for row in cursor.fetchall()]
        return cols
    except sqlite3.Error as e:
        print(f"Error getting columns for {table_name}: {e}")
        return []
    finally:
        conn.close()

def get_full_table_definition(db_name, table_name):
    """
    Reads a table's full schema and returns it in the format used by create_table.
    Note: This is a best-effort parser and may not capture all complex constraints like multi-column UNIQUE or CHECK.
    """
    conn = get_db_connection(db_name)
    if not conn: return []
    cursor = conn.cursor()
    
    try:
        # 1. Basic info from table_info
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        cols_info = cursor.fetchall()
        defs = {row[1]: {'name': row[1], 'type': row[2], 'not_null': bool(row[3]), 'pk': bool(row[5])} for row in cols_info}
        
        # Check for autoincrement
        pk_cols = [k for k, v in defs.items() if v['pk']]
        if len(pk_cols) == 1 and defs[pk_cols[0]]['type'] == 'INTEGER':
            schema = get_table_schema(conn, table_name)
            if "AUTOINCREMENT" in schema.upper():
                defs[pk_cols[0]]['autoincrement'] = True

        # 2. Unique constraints from index_list
        cursor.execute(f"PRAGMA index_list('{table_name}')")
        for index in cursor.fetchall():
            if index[2] and index[3] == 'u': # is_unique and is a UNIQUE constraint
                cursor.execute(f"PRAGMA index_info('{index[1]}')")
                for info in cursor.fetchall():
                    if info[2] in defs: defs[info[2]]['unique'] = True
        
        # 3. Foreign keys from foreign_key_list
        cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
        for fk in cursor.fetchall():
            if fk[3] in defs:
                defs[fk[3]]['fk_table'] = fk[2]
                defs[fk[3]]['fk_column'] = fk[4]
                
        return list(defs.values())
    finally:
        conn.close()

def get_valid_fk_target_columns(db_name, table_name):
    """
    Gets a list of columns that are either primary keys or have a unique constraint.
    These are the only valid targets for a foreign key reference in SQLite.
    Returns a list of column names.
    """
    conn = get_db_connection(db_name)
    if not conn:
        return []

    target_columns = []
    cursor = conn.cursor()

    try:
        # 1. Get Primary Key columns from PRAGMA table_info
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        table_info = cursor.fetchall()
        # table_info row: (cid, name, type, notnull, dflt_value, pk)
        pk_cols = [row[1] for row in table_info if row[5] > 0]
        target_columns.extend(pk_cols)

        # 2. Get columns from UNIQUE indexes
        cursor.execute(f"PRAGMA index_list('{table_name}')")
        indexes = cursor.fetchall()
        # indexes row: (seq, name, unique, origin, partial)
        # We only care about explicit UNIQUE constraints, not implicit ones for PRIMARY KEYs
        unique_indexes = [row[1] for row in indexes if row[2] == 1 and not row[1].startswith('sqlite_autoindex_')]

        for index_name in unique_indexes:
            cursor.execute(f"PRAGMA index_info('{index_name}')")
            # index_info row: (seqno, cid, name)
            index_cols = cursor.fetchall()
            for row in index_cols:
                col_name = row[2]
                if col_name not in target_columns:
                    target_columns.append(col_name)

    except sqlite3.Error as e:
        print(f"Error getting key columns for {table_name}: {e}")
    finally:
        conn.close()

    return target_columns

def get_column_type(db_name, table_name, column_name):
    """Gets the data type of a specific column."""
    conn = get_db_connection(db_name)
    if not conn:
        return None
    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        for row in cursor.fetchall():
            if row[1] == column_name:
                return row[2] # The 'type' column
        return None
    except sqlite3.Error as e:
        print(f"Error getting column type: {e}")
        return None
    finally:
        conn.close()

def get_table_schema(conn, table_name):
    """Gets the CREATE statement for a table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    result = cursor.fetchone()
    return result[0] if result else None

def get_primary_key_columns(db_name, table_name):
    """Returns a list of the primary key column names for a table."""
    cols = get_table_columns(db_name, table_name)
    return [c['name'] for c in cols if c['pk']]

def get_foreign_key_info(db_name, table_name):
    """
    Gets foreign key relationships for a table.
    Returns a dict: {'column_name': {'table': 'parent_table', 'to': 'parent_column'}}
    """
    conn = get_db_connection(db_name)
    if not conn:
        return {}
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
        fk_info = {}
        # Row: (id, seq, table, from, to, on_update, on_delete, match)
        for row in cursor.fetchall():
            fk_info[row[3]] = {'table': row[2], 'to': row[4]}
        return fk_info
    except sqlite3.Error as e:
        print(f"Error getting FK info for {table_name}: {e}")
        return {}
    finally:
        conn.close()

# --- Private Helpers ---
def _generate_create_table_sql(table_name, columns_defs):
    """Generates the 'CREATE TABLE' SQL string from a list of column definitions."""
    col_strings = []
    pk_cols = []
    fk_defs = []

    for col in columns_defs:
        parts = [f'"{col["name"]}"', col["type"]]
        # Handle single-column Primary Key defined inline
        if col.get('pk') and len([c for c in columns_defs if c.get('pk')]) == 1:
            parts.append("PRIMARY KEY")
            if col.get('autoincrement'):
                parts.append("AUTOINCREMENT")
        elif col.get('pk'):
            pk_cols.append(col["name"]) # For composite PK

        if col.get('not_null'): parts.append("NOT NULL")
        if col.get('unique'): parts.append("UNIQUE")
        col_strings.append(" ".join(parts))

        if col.get('fk_table') and col.get('fk_column'):
            fk_defs.append(f'FOREIGN KEY ("{col["name"]}") REFERENCES "{col["fk_table"]}"("{col["fk_column"]}")')

    if pk_cols: # Add composite primary key if necessary
        pk_cols_str = ", ".join([f'"{c}"' for c in pk_cols])
        col_strings.append(f'PRIMARY KEY ({pk_cols_str})')

    col_strings.extend(fk_defs)
    return f'CREATE TABLE "{table_name}" (\n  ' + ",\n  ".join(col_strings) + "\n);"

# --- Schema Modification ---
def create_table(db_name, table_name, columns_defs):
    """
    Creates a new table.
    - columns_defs: A list of dictionaries, where each dict defines a column.
      e.g., {'name': 'id', 'type': 'INTEGER', 'pk': True, 'autoincrement': True, ...}
    """
    conn = get_db_connection(db_name)
    if not conn:
        return False, "Could not connect to the database."

    sql = _generate_create_table_sql(table_name, columns_defs)
    try:
        conn.execute(sql)
        conn.commit()
        return True, f"Table '{table_name}' created successfully."
    except sqlite3.Error as e:
        return False, f"Failed to create table: {e}"
    finally:
        conn.close()

def add_foreign_key(db_name, table_name, column_name, target_table, target_column):
    """
    Adds a foreign key to an existing table.
    Since SQLite has limited ALTER TABLE support, this is done by recreating the table.
    """
    conn = get_db_connection(db_name)
    if not conn:
        return False, "Could not connect to the database."
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA foreign_keys=OFF;")
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Get original schema and column names
        original_schema = get_table_schema(conn, table_name)
        if not original_schema:
            raise sqlite3.Error(f"Table '{table_name}' not found.")
            
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        columns_info = cursor.fetchall()
        column_names = [info[1] for info in columns_info]
        column_names_str = ", ".join(f'"{col}"' for col in column_names)

        # 2. Create the new schema with the foreign key
        closing_paren_index = original_schema.rfind(')')
        new_schema = (
            original_schema[:closing_paren_index] +
            f",\n  FOREIGN KEY (\"{column_name}\") REFERENCES \"{target_table}\"(\"{target_column}\")" +
            original_schema[closing_paren_index:]
        )
        
        # 3. Rename old table
        temp_table_name = f"{table_name}_old_{os.urandom(4).hex()}"
        cursor.execute(f'ALTER TABLE "{table_name}" RENAME TO "{temp_table_name}";')

        # 4. Create the new table
        cursor.execute(new_schema)

        # 5. Copy data
        cursor.execute(f'INSERT INTO "{table_name}" ({column_names_str}) SELECT {column_names_str} FROM "{temp_table_name}";')

        # 6. Drop old table
        cursor.execute(f'DROP TABLE "{temp_table_name}";')

        cursor.execute("COMMIT;")
        return True, "Foreign key added successfully."

    except sqlite3.Error as e:
        cursor.execute("ROLLBACK;")
        return False, f"Failed to add foreign key: {e}"
    finally:
        cursor.execute("PRAGMA foreign_keys=ON;")
        conn.close()

def delete_table(db_name, table_name):
    """Deletes a table from the database."""
    conn = get_db_connection(db_name)
    if not conn:
        return False, "Could not connect to the database."

    try:
        cursor = conn.cursor()
        # Table names cannot be parameterized in SQLite, so we use a formatted string.
        # This is safe here because the table_name comes from our UI list, not direct user input.
        cursor.execute(f'DROP TABLE "{table_name}"')
        conn.commit()
        return True, f"Table '{table_name}' deleted successfully."
    except sqlite3.Error as e:
        return False, f"Failed to delete table: {e}"
    finally:
        conn.close()

def add_column(db_name, table_name, column_def):
    """Adds a new column to a table using ALTER TABLE."""
    conn = get_db_connection(db_name)
    if not conn:
        return False, "Could not connect to the database."

    # Build the column definition string
    col_parts = [f'"{column_def["name"]}"', column_def["type"]]
    if column_def.get('not_null'):
        col_parts.append("NOT NULL")
    if column_def.get('unique'):
        col_parts.append("UNIQUE")
    # Note: If a column is NOT NULL, SQLite requires a DEFAULT value if the table
    # already contains data. The UI doesn't currently ask for a default,
    # so SQLite will raise an error, which is informative for the user.
    
    col_def_str = " ".join(col_parts)
    sql = f'ALTER TABLE "{table_name}" ADD COLUMN {col_def_str}'

    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        return True, "Column added successfully."
    except sqlite3.Error as e:
        return False, f"Failed to add column: {e}"
    finally:
        conn.close()

def remove_column(db_name, table_name, column_to_remove):
    """
    Removes a column from a table by recreating the table.
    This is a complex operation due to SQLite's limitations.
    """
    # Pre-flight checks before opening a transaction
    pk_cols = get_primary_key_columns(db_name, table_name)
    if column_to_remove in pk_cols:
        return False, "Cannot remove a column that is part of the primary key."

    conn = get_db_connection(db_name)
    if not conn: return False, "Could not connect to the database."
    cursor = conn.cursor()

    try:
        # Check if column is referenced by another table's FK
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for row in cursor.fetchall():
            other_table = row[0]
            if other_table == table_name: continue
            cursor.execute(f"PRAGMA foreign_key_list('{other_table}')")
            for fk in cursor.fetchall():
                if fk[2] == table_name and fk[4] == column_to_remove:
                    return False, f"Cannot remove column '{column_to_remove}' because it is referenced by a foreign key in table '{other_table}'."

        # Get full definition and filter out the column
        full_defs = get_full_table_definition(db_name, table_name)
        new_defs = [d for d in full_defs if d['name'] != column_to_remove]
        
        if len(new_defs) == len(full_defs): raise sqlite3.Error(f"Column '{column_to_remove}' not found.")
        if not new_defs: return False, "Cannot remove the last column from a table."
        
        remaining_col_names = [d['name'] for d in new_defs]
        remaining_col_names_str = ", ".join(f'"{col}"' for col in remaining_col_names)
        
        cursor.execute("PRAGMA foreign_keys=OFF;")
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Rename old table
        temp_table_name = f"{table_name}_old_{os.urandom(4).hex()}"
        cursor.execute(f'ALTER TABLE "{table_name}" RENAME TO "{temp_table_name}";')
        
        # 2. Create new table (re-implementing create_table logic for the transaction)
        create_sql = _generate_create_table_sql(table_name, new_defs)
        cursor.execute(create_sql)
        
        # 3. Copy data & 4. Drop old table
        cursor.execute(f'INSERT INTO "{table_name}" ({remaining_col_names_str}) SELECT {remaining_col_names_str} FROM "{temp_table_name}";')
        cursor.execute(f'DROP TABLE "{temp_table_name}";')
        cursor.execute("COMMIT;")
        return True, "Column removed successfully."
    except sqlite3.Error as e:
        cursor.execute("ROLLBACK;")
        return False, f"Failed to remove column: {e}"
    finally:
        if conn: cursor.execute("PRAGMA foreign_keys=ON;"); conn.close()

# --- Data Manipulation ---
def get_table_data(db_name, table_name):
    """Fetches all data and headers for a given table."""
    conn = get_db_connection(db_name)
    if not conn:
        return [], []
    try:
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM "{table_name}"')
        headers = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return headers, rows
    except sqlite3.Error as e:
        print(f"Error fetching data for {table_name}: {e}")
        return [], []
    finally:
        conn.close()

def get_parent_table_values(db_name, table_name, column_name):
    """Fetches all distinct values from a parent table's column for FK selection."""
    conn = get_db_connection(db_name)
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        # Use DISTINCT to avoid duplicate values in the dropdown
        cursor.execute(f'SELECT DISTINCT "{column_name}" FROM "{table_name}" ORDER BY "{column_name}"')
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching parent values: {e}")
        return []
    finally:
        conn.close()

def insert_row(db_name, table_name, data_dict):
    """Inserts a new row of data into a table."""
    conn = get_db_connection(db_name)
    if not conn:
        return False, "Could not connect to the database."

    columns = ', '.join(f'"{k}"' for k in data_dict.keys())
    placeholders = ', '.join(['?'] * len(data_dict))
    sql = f"INSERT INTO \"{table_name}\" ({columns}) VALUES ({placeholders})"
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql, list(data_dict.values()))
        conn.commit()
        return True, "Row added successfully."
    except sqlite3.Error as e:
        return False, f"Failed to add row: {e}"
    finally:
        conn.close()

def update_row(db_name, table_name, pk_dict, new_data_dict):
    """Updates a row identified by its primary key."""
    conn = get_db_connection(db_name)
    if not conn:
        return False, "Could not connect to the database."

    set_clause = ", ".join([f'"{k}" = ?' for k in new_data_dict.keys()])
    where_clause = " AND ".join([f'"{k}" = ?' for k in pk_dict.keys()])
    sql = f'UPDATE "{table_name}" SET {set_clause} WHERE {where_clause}'
    
    values = list(new_data_dict.values()) + list(pk_dict.values())

    try:
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Row not found. It may have been deleted by another user."
        return True, "Row updated successfully."
    except sqlite3.Error as e:
        return False, f"Failed to update row: {e}"
    finally:
        conn.close()

def delete_row(db_name, table_name, pk_dict):
    """Deletes a row identified by its primary key values."""
    conn = get_db_connection(db_name)
    if not conn:
        return False, "Could not connect to the database."
    
    where_clause = " AND ".join([f'"{k}" = ?' for k in pk_dict.keys()])
    sql = f'DELETE FROM "{table_name}" WHERE {where_clause}'

    try:
        cursor = conn.cursor()
        cursor.execute(sql, list(pk_dict.values()))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Row not found. It may have been deleted by another user."
        return True, "Row deleted successfully."
    except sqlite3.Error as e:
        return False, f"Failed to delete row: {e}"
    finally:
        conn.close()