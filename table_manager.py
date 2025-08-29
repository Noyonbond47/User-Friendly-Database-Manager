import csv
import json
from pathlib import Path
from database_manager import DATABASES_ROOT_DIR
from typing import Union

# --- Constants for Column Types ---
PK = "PK"
FK = "FK"
DATE = "Date"
INTEGER = "Integer"
BOOLEAN = "Boolean"
TEXT = "Text"
DATA_TYPES = [PK, FK, DATE, INTEGER, BOOLEAN, TEXT]

# --- Helper Functions ---
def _get_db_path(db_name: str) -> Path:
    """Gets the path to a specific database directory."""
    return DATABASES_ROOT_DIR / db_name

def _get_table_meta_path(db_name: str, table_name: str) -> Path:
    """Gets the path to a table's metadata file."""
    return _get_db_path(db_name) / f"{table_name}.meta.json"

def _get_table_csv_path(db_name: str, table_name: str) -> Path:
    """Gets the path to a table's CSV data file."""
    return _get_db_path(db_name) / f"{table_name}.csv"

# --- Public Functions ---

def list_tables(db_name: str) -> list[str]:
    """Lists all tables in a given database by finding .meta.json files."""
    db_path = _get_db_path(db_name)
    if not db_path.is_dir():
        return []
    # The part of the filename before ".meta.json" is the table name
    return sorted([p.name.replace('.meta.json', '') for p in db_path.glob("*.meta.json")])

def create_table(db_name: str, table_name: str, columns: list[dict]) -> tuple[bool, str]:
    """
    Creates a new table with a schema (meta.json) and a data file (csv).
    `columns` is a list of dicts, e.g., [{'name': 'id', 'type': 'PK'}]
    """
    if not table_name or not table_name.strip():
        return False, "Table name cannot be empty."
    
    meta_path = _get_table_meta_path(db_name, table_name)
    csv_path = _get_table_csv_path(db_name, table_name)

    if meta_path.exists() or csv_path.exists():
        return False, f"Table '{table_name}' already exists."

    # Validate columns and ensure one PK
    pk_found = any(col.get('type') == PK for col in columns)
    if not pk_found:
        # Auto-add a primary key if none is specified for good practice
        columns.insert(0, {'name': 'id', 'type': PK})

    if sum(1 for col in columns if col.get('type') == PK) > 1:
        return False, "A table can only have one Primary Key."

    # Validate Foreign Keys
    for col in columns:
        if col.get('type') == FK:
            ref_table = col.get('references')
            if not ref_table:
                return False, f"Foreign Key column '{col.get('name')}' is missing a reference table."
            
            # Check if the referenced table actually exists
            ref_meta_path = _get_table_meta_path(db_name, ref_table)
            if not ref_meta_path.exists():
                return False, f"Cannot create Foreign Key: The referenced table '{ref_table}' does not exist."

    # Create meta file
    schema = {"columns": columns}
    try:
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=4)

        # Create CSV file with headers
        headers = [col['name'] for col in columns]
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
        return True, f"Table '{table_name}' created successfully."
    except Exception as e:
        return False, f"Failed to create table files: {e}"

def delete_table(db_name: str, table_name: str) -> tuple[bool, str]:
    """Deletes a table's .csv and .meta.json files."""
    meta_path = _get_table_meta_path(db_name, table_name)
    csv_path = _get_table_csv_path(db_name, table_name)

    if not meta_path.exists():
        return False, f"Table '{table_name}' not found."

    try:
        meta_path.unlink()
        if csv_path.exists():
            csv_path.unlink()
        return True, f"Table '{table_name}' deleted successfully."
    except Exception as e:
        return False, f"Error deleting table: {e}"

def get_table_schema(db_name: str, table_name: str) -> Union[dict, None]:
    """Reads and returns the schema for a table from its meta file."""
    meta_path = _get_table_meta_path(db_name, table_name)
    if not meta_path.exists():
        return None
    with open(meta_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_table_data(db_name: str, table_name: str) -> Union[list[dict], None]:
    """Reads a table's CSV and returns a list of dictionaries (rows)."""
    csv_path = _get_table_csv_path(db_name, table_name)
    if not csv_path.exists():
        return None
    
    data = []
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    except Exception:
        return [] # Return empty list on read error

def save_table_data(db_name: str, table_name: str, data: list[dict], headers: list[str]) -> tuple[bool, str]:
    """Overwrites the table's CSV file with new data."""
    csv_path = _get_table_csv_path(db_name, table_name)
    
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        return True, "Data saved successfully."
    except Exception as e:
        return False, f"Failed to save data: {e}"