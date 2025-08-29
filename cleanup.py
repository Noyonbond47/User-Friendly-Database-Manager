import os
import shutil

def clean_project():
    """
    Removes Python cache files and folders (__pycache__) from the project directory.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    print(f"Starting cleanup in: {project_root}\n")

    for root, dirs, files in os.walk(project_root):
        # Remove __pycache__ directories
        if "__pycache__" in dirs:
            pycache_folder = os.path.join(root, "__pycache__")
            print(f"Removing folder: {pycache_folder}")
            try:
                shutil.rmtree(pycache_folder)
            except OSError as e:
                print(f"  Error removing {pycache_folder}: {e}")

    print("\nCleanup complete.")

if __name__ == "__main__":
    clean_project()

