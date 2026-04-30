"""
app/blueprints/dashboard.py — Datos para los gráficos
=======================================================
Endpoints:
    GET /api/dashboard/kpis       → métricas agregadas globales
    GET /api/dashboard/bar        → datos para gráfico de barras
    GET /api/dashboard/line       → datos para gráfico de líneas
    GET /api/dashboard/scatter    → datos para gráfico de dispersión
    GET /api/dashboard/pie        → datos para gráfico de torta
    GET /api/dashboard/filtros    → valores únicos para los filtros

Todos los endpoints aceptan filtros dinámicos como query params.
Para agregar un nuevo tipo de gráfico, crea un endpoint nuevo aquí
y regístralo — el frontend lo detectará automáticamente.
"""
import pandas as pd
from flask import Blueprint, request, jsonify, session
from app.utils.file_handler import read_csv_safe, analyze_dataframe, FileValidationError

dashboard_bp = Blueprint("dashboard", __name__)


# ── Helpers ────────────────────────────────────────────────────

def _get_df() -> pd.DataFrame:
    """Carga el DataFrame desde la sesión. Lanza ValueError si no hay CSV."""
    path = session.get("csv_path")
    if not path:
        raise ValueError("No hay ningún CSV cargado.")
    return read_csv_safe(path)


def _apply_filters(df: pd.DataFrame, params) -> pd.DataFrame:
    """
    Aplica filtros categóricos recibidos como query params.
    Valida cada columna contra el DataFrame real (seguridad).
    Acepta múltiples valores: ?marca=A&marca=B
    """
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    for col in cat_cols:
        vals = params.getlist(col)
        if vals and col in df.columns:
            df = df[df[col].isin(vals)]
    return df


def _validate_col(df: pd.DataFrame, col: str, dtype: str = "any") -> str | None:
    """
    Valida que una columna exista en el DataFrame y sea del tipo correcto.
    Retorna None si no es válida (evita inyección de parámetros).
    """
    if col not in df.columns:
        return None
    if dtype == "numeric":
        return col if col in df.select_dtypes(include="number").columns else None
    if dtype == "categorical":
        return col if col in df.select_dtypes(include="object").columns else None
    return col


def _safe_records(data: list, max_points: int = 2000) -> list:
    """Limita la cantidad de registros para no saturar el frontend."""
    return data[:max_points]


# ── Endpoints ──────────────────────────────────────────────────

@dashboard_bp.route("/filtros", methods=["GET"])
def get_filtros():
    """Retorna valores únicos de cada columna categórica para los filtros."""
    try:
        df       = _get_df()
        analysis = analyze_dataframe(df)
        return jsonify({
            "filtros":    analysis["cat_values"],
            "num_cols":   analysis["num_cols"],
            "cat_cols":   analysis["cat_cols"],
            "total_rows": analysis["total_rows"],
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except FileValidationError as e:
        return jsonify({"error": str(e)}), 422


@dashboard_bp.route("/kpis", methods=["GET"])
def get_kpis():
    """
    Métricas agregadas: suma, promedio y máximo de columnas numéricas.
    Respeta los filtros activos.
    """
    try:
        df      = _get_df()
        df      = _apply_filters(df, request.args)
        num_cols = df.select_dtypes(include="number").columns.tolist()

        kpis = {}
        for col in num_cols[:6]:  # máx 6 KPIs
            s = df[col].dropna()
            kpis[col] = {
                "suma":     round(float(s.sum()), 2),
                "promedio": round(float(s.mean()), 2),
                "maximo":   round(float(s.max()), 2),
                "minimo":   round(float(s.min()), 2),
            }

        return jsonify({"kpis": kpis, "registros": len(df)})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/bar", methods=["GET"])
def get_bar():
    """
    Gráfico de barras: agrupa por columna categórica y suma/promedia una numérica.

    Query params:
        x        — columna categórica (eje X)
        y        — columna numérica (eje Y)
        agg      — agregación: sum | mean | count  (default: sum)
        top      — limitar a los N primeros (default: 20)
        [filtros dinámicos]
    """
    try:
        df = _get_df()
        df = _apply_filters(df, request.args)

        num_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(include="object").columns.tolist()

        x_col = _validate_col(df, request.args.get("x", cat_cols[0] if cat_cols else ""), "categorical")
        y_col = _validate_col(df, request.args.get("y", num_cols[0] if num_cols else ""), "numeric")
        agg   = request.args.get("agg", "sum")
        top   = min(int(request.args.get("top", 20)), 100)

        if not x_col or not y_col:
            return jsonify({"error": "Columnas inválidas para el gráfico de barras."}), 422

        if agg not in ("sum", "mean", "count"):
            agg = "sum"

        if agg == "count":
            grouped = df.groupby(x_col).size().reset_index(name=y_col)
        else:
            grouped = df.groupby(x_col)[y_col].agg(agg).reset_index()

        grouped = grouped.nlargest(top, y_col)

        return jsonify({
            "labels": grouped[x_col].astype(str).tolist(),
            "values": grouped[y_col].round(2).tolist(),
            "x_col":  x_col,
            "y_col":  y_col,
            "agg":    agg,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/line", methods=["GET"])
def get_line():
    """
    Gráfico de líneas: evolución de una métrica a lo largo de una columna ordenada.

    Query params:
        x        — columna para el eje X (fecha, mes, periodo, etc.)
        y        — columna numérica
        group_by — columna categórica para múltiples líneas (opcional)
        agg      — sum | mean  (default: sum)
        [filtros dinámicos]
    """
    try:
        df = _get_df()
        df = _apply_filters(df, request.args)

        num_cols = df.select_dtypes(include="number").columns.tolist()
        all_cols = df.columns.tolist()

        x_col    = _validate_col(df, request.args.get("x", all_cols[0]), "any")
        y_col    = _validate_col(df, request.args.get("y", num_cols[0] if num_cols else ""), "numeric")
        group_by = _validate_col(df, request.args.get("group_by", ""), "categorical")
        agg      = request.args.get("agg", "sum")

        if agg not in ("sum", "mean"):
            agg = "sum"
        if not x_col or not y_col:
            return jsonify({"error": "Columnas inválidas para el gráfico de líneas."}), 422

        datasets = []
        if group_by:
            for grp, sub in df.groupby(group_by):
                agged = sub.groupby(x_col)[y_col].agg(agg).reset_index()
                datasets.append({
                    "label":  str(grp),
                    "x":      agged[x_col].astype(str).tolist(),
                    "y":      agged[y_col].round(2).tolist(),
                })
        else:
            agged = df.groupby(x_col)[y_col].agg(agg).reset_index()
            datasets.append({
                "label": y_col,
                "x":     agged[x_col].astype(str).tolist(),
                "y":     agged[y_col].round(2).tolist(),
            })

        return jsonify({"datasets": datasets, "x_col": x_col, "y_col": y_col})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/scatter", methods=["GET"])
def get_scatter():
    """
    Gráfico de dispersión: correlación entre dos métricas numéricas.

    Query params:
        x        — columna numérica eje X
        y        — columna numérica eje Y
        color_by — columna categórica para agrupar colores (opcional)
        [filtros dinámicos]
    """
    try:
        df = _get_df()
        df = _apply_filters(df, request.args)

        num_cols = df.select_dtypes(include="number").columns.tolist()
        if len(num_cols) < 2:
            return jsonify({"error": "Se necesitan al menos 2 columnas numéricas."}), 422

        x_col    = _validate_col(df, request.args.get("x", num_cols[0]), "numeric")
        y_col    = _validate_col(df, request.args.get("y", num_cols[1]), "numeric")
        color_by = _validate_col(df, request.args.get("color_by", ""), "categorical")

        if not x_col or not y_col:
            return jsonify({"error": "Columnas inválidas."}), 422

        traces = []
        if color_by:
            for grp, sub in df.groupby(color_by):
                clean = sub[[x_col, y_col]].dropna()
                traces.append({
                    "name": str(grp),
                    "x":    clean[x_col].round(4).tolist(),
                    "y":    clean[y_col].round(4).tolist(),
                })
        else:
            clean = df[[x_col, y_col]].dropna()
            traces.append({
                "name": f"{x_col} vs {y_col}",
                "x":    _safe_records(clean[x_col].round(4).tolist()),
                "y":    _safe_records(clean[y_col].round(4).tolist()),
            })

        return jsonify({"traces": traces, "x_col": x_col, "y_col": y_col})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/pie", methods=["GET"])
def get_pie():
    """
    Gráfico de torta/donut: distribución de una métrica por categoría.

    Query params:
        label    — columna categórica
        value    — columna numérica
        top      — mostrar top N categorías (default: 8)
        [filtros dinámicos]
    """
    try:
        df = _get_df()
        df = _apply_filters(df, request.args)

        cat_cols = df.select_dtypes(include="object").columns.tolist()
        num_cols = df.select_dtypes(include="number").columns.tolist()

        label_col = _validate_col(df, request.args.get("label", cat_cols[0] if cat_cols else ""), "categorical")
        value_col = _validate_col(df, request.args.get("value", num_cols[0] if num_cols else ""), "numeric")
        top       = min(int(request.args.get("top", 8)), 20)

        if not label_col or not value_col:
            return jsonify({"error": "Columnas inválidas para el gráfico de torta."}), 422

        grouped = df.groupby(label_col)[value_col].sum().nlargest(top).reset_index()

        return jsonify({
            "labels": grouped[label_col].astype(str).tolist(),
            "values": grouped[value_col].round(2).tolist(),
            "label_col": label_col,
            "value_col": value_col,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
