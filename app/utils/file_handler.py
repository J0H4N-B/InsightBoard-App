"""
app/utils/file_handler.py — Manejo seguro de archivos CSV
==========================================================
Centraliza validación, guardado y análisis del CSV.

Para escalar:
  - Agrega nuevos tipos de análisis en analyze_dataframe()
  - El límite de filas y peso se configura en .env
"""
import os
import uuid
import pandas as pd
from flask import current_app
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage


class FileValidationError(Exception):
    pass


def allowed_file(filename: str) -> bool:
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"csv"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_uploaded_file(file: FileStorage) -> str:
    """Guarda el CSV de forma segura. Retorna la ruta absoluta."""
    if not file or file.filename == "":
        raise FileValidationError("No se recibió ningún archivo.")
    if not allowed_file(file.filename):
        raise FileValidationError("Solo se aceptan archivos .csv")

    safe     = secure_filename(file.filename)
    unique   = f"{uuid.uuid4().hex}_{safe}"
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], unique)
    file.save(filepath)
    return filepath


def read_csv_safe(filepath: str, max_rows: int = 50_000) -> pd.DataFrame:
    """
    Lee el CSV con validaciones de seguridad:
    - Límite de filas
    - Manejo de encodings (utf-8, latin-1)
    - Limpieza de nombres de columna
    """
    if not os.path.exists(filepath):
        raise FileValidationError("Archivo no encontrado.")

    df = None
    for enc in ("utf-8", "latin-1", "utf-8-sig"):
        try:
            df = pd.read_csv(filepath, nrows=max_rows, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise FileValidationError(f"Error al leer el CSV: {e}")

    if df is None:
        raise FileValidationError("No se pudo decodificar el CSV.")
    if df.empty:
        raise FileValidationError("El CSV está vacío.")
    if len(df.columns) < 2:
        raise FileValidationError("El CSV debe tener al menos 2 columnas.")

    df.columns = (
        df.columns.str.strip().str.lower()
        .str.replace(" ", "_").str.replace(r"[^\w]", "", regex=True)
    )
    return df


def analyze_dataframe(df: pd.DataFrame) -> dict:
    """
    Extrae metadata del DataFrame para poblar los controles del frontend:
    - Columnas numéricas y categóricas
    - Valores únicos de columnas categóricas (para filtros)
    - Estadísticas básicas de columnas numéricas

    Para agregar nuevas métricas de análisis, extiende este dict.
    """
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()

    # Valores únicos para columnas categóricas (máx 200 por columna)
    cat_values = {}
    for col in cat_cols:
        vals = df[col].dropna().unique().tolist()
        cat_values[col] = sorted([str(v) for v in vals])[:200]

    # Estadísticas rápidas por columna numérica
    num_stats = {}
    for col in num_cols:
        s = df[col].dropna()
        num_stats[col] = {
            "min":    round(float(s.min()), 2),
            "max":    round(float(s.max()), 2),
            "mean":   round(float(s.mean()), 2),
            "median": round(float(s.median()), 2),
            "sum":    round(float(s.sum()), 2),
        }

    return {
        "num_cols":   num_cols,
        "cat_cols":   cat_cols,
        "cat_values": cat_values,
        "num_stats":  num_stats,
        "total_rows": len(df),
        "total_cols": len(df.columns),
        "all_cols":   df.columns.tolist(),
    }


def cleanup_old_uploads(upload_folder: str, max_files: int = 50) -> None:
    """Elimina uploads más antiguos si se supera max_files."""
    try:
        files = sorted(
            [os.path.join(upload_folder, f) for f in os.listdir(upload_folder)
             if os.path.isfile(os.path.join(upload_folder, f))],
            key=os.path.getctime,
        )
        while len(files) > max_files:
            os.remove(files.pop(0))
    except Exception:
        pass
