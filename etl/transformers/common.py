import numpy as np
import pandas as pd

_DECIMAL_COLS = {
    "stock_actual", "stock_minimo", "stock_maximo",
    "cantidad", "cantidad_anterior", "cantidad_posterior",
    "costo_unitario", "subtotal", "descuento", "impuesto", "total", "saldo",
}

_DATETIME_COLS = {"fecha", "created_at", "updated_at", "deleted_at"}

_DATE_COLS = {"fecha_emision", "fecha_vencimiento"}


def clean(df: pd.DataFrame, required: list[str]) -> pd.DataFrame:
    """Normaliza tipos y descarta filas con nulos en columnas NOT NULL."""
    df = df.copy()

    for col in df.columns:
        if col in _DECIMAL_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        elif col in _DATETIME_COLS:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif col in _DATE_COLS:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    # NaN → None para compatibilidad MySQL
    df = df.replace({np.nan: None})

    before = len(df)
    df = df.dropna(subset=required)
    dropped = before - len(df)
    if dropped:
        import logging
        logging.getLogger(__name__).warning(
            "Descartadas %d filas por nulos en columnas requeridas: %s",
            dropped, required,
        )

    return df
