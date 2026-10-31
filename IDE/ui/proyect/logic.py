"""Operaciones de ficheros del panel Project (sin dependencias de Qt)."""
import os
import shutil

def rename_file(path, new_name):
    """Renombra un archivo en disco."""
    os.rename(path, os.path.join(os.path.dirname(path), new_name))

def move_file(path, folder):
    """Mueve un archivo a otra carpeta."""
    shutil.move(path, os.path.join(folder, os.path.basename(path)))

def delete_file(path):
    """Elimina un archivo de disco."""
    os.remove(path)

def list_dir(folder, hidden_entries):
    """Lista los archivos de una carpeta ignorando las entradas ocultas."""
    try:
        return sorted(n for n in os.listdir(folder) if n not in hidden_entries)
    except OSError:
        return []