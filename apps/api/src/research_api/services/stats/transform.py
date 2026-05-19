"""Phase 13 (MP13) — Dataset transformation ops.

Pure functions; every op takes a DataFrame and a JSON-serialisable args dict
and returns a NEW DataFrame. The input is never mutated.

Supported op types
------------------
filter         {"column": str, "op": "==|!=|<|<=|>|>=|in|not_in|notna|isna",
                "value": <scalar|list>}
mutate         {"new_column": str, "expression": str}
                Expression is a tiny algebra: a column name, ``log(col)``,
                ``log10(col)``, ``sqrt(col)``, ``abs(col)``, ``col1 + col2``,
                ``col1 - col2``, ``col1 * col2``, ``col1 / col2``, or a
                literal scalar.  No arbitrary eval.
select         {"columns": list[str]}      keep only these columns
recode         {"column": str, "mapping": {old_value: new_value}, "default":?}
drop_na        {"columns": list[str] | null}    null → all columns
log_transform  {"column": str, "new_column": str, "base": "e|10|2"}
z_score        {"column": str, "new_column": str}
group_summarise{"by": list[str], "agg": {col: "mean|sum|count|min|max|median"}}
"""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd

_COL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

OP_TYPES = (
    "filter",
    "mutate",
    "select",
    "recode",
    "drop_na",
    "log_transform",
    "z_score",
    "group_summarise",
    # MP-stats-refine: explicit row drop by original __row_index. Used by
    # the editable DataView's "Drop selected" action so deletions are
    # honoured by every downstream analysis.
    "drop_rows",
)


class TransformError(ValueError):
    """Raised when an op or its arguments are structurally invalid."""


# ── individual ops ─────────────────────────────────────────────────────


def _check_column(name: Any) -> str:
    if not isinstance(name, str) or not _COL_RE.match(name):
        raise TransformError(f"invalid column name {name!r}")
    return name


def _require_columns(df: pd.DataFrame, names: list[str]) -> None:
    missing = [n for n in names if n not in df.columns]
    if missing:
        raise TransformError(f"columns not in dataframe: {missing!r}")


def _filter(df: pd.DataFrame, args: dict[str, Any]) -> pd.DataFrame:
    col = _check_column(args.get("column"))
    op_name = args.get("op")
    value = args.get("value")
    _require_columns(df, [col])
    series = df[col]
    if op_name == "==":
        mask = series == value
    elif op_name == "!=":
        mask = series != value
    elif op_name == "<":
        mask = series < value
    elif op_name == "<=":
        mask = series <= value
    elif op_name == ">":
        mask = series > value
    elif op_name == ">=":
        mask = series >= value
    elif op_name == "in":
        if not isinstance(value, (list, tuple)):
            raise TransformError("filter 'in' requires a list value")
        mask = series.isin(value)
    elif op_name == "not_in":
        if not isinstance(value, (list, tuple)):
            raise TransformError("filter 'not_in' requires a list value")
        mask = ~series.isin(value)
    elif op_name == "notna":
        mask = series.notna()
    elif op_name == "isna":
        mask = series.isna()
    else:
        raise TransformError(f"unknown filter op: {op_name!r}")
    return df.loc[mask].reset_index(drop=True)


def _mutate(df: pd.DataFrame, args: dict[str, Any]) -> pd.DataFrame:
    new_col = _check_column(args.get("new_column"))
    expr = args.get("expression")
    if not isinstance(expr, str) or not expr.strip():
        raise TransformError("mutate requires a non-empty 'expression'")
    out = df.copy()
    out[new_col] = _evaluate_expression(out, expr.strip())
    return out


_UNARY_FNS: dict[str, Any] = {
    "log": lambda s: np.log(s),
    "log10": lambda s: np.log10(s),
    "log2": lambda s: np.log2(s),
    "sqrt": lambda s: np.sqrt(s),
    "abs": lambda s: np.abs(s),
    "exp": lambda s: np.exp(s),
}


def _evaluate_expression(df: pd.DataFrame, expr: str) -> Any:
    """Tiny algebra: column, fn(column), col +-*/ col, or literal scalar.

    Deliberately *not* a general eval — only the patterns the UI generates.
    """
    # Literal scalar?
    try:
        v = float(expr)
        if not math.isfinite(v):
            raise ValueError("non-finite literal")
        return v
    except ValueError:
        pass

    # Unary function: fn(arg)
    m = re.fullmatch(r"([A-Za-z_]+)\(([A-Za-z_][A-Za-z0-9_]*)\)", expr)
    if m is not None:
        fn_name, arg = m.group(1), m.group(2)
        if fn_name not in _UNARY_FNS:
            raise TransformError(f"unknown function {fn_name!r}")
        _require_columns(df, [arg])
        return _UNARY_FNS[fn_name](df[arg].astype(float))

    # Binary: col1 OP col2  OR  col OP literal  OR  literal OP col
    m = re.fullmatch(
        r"([A-Za-z_][A-Za-z0-9_]*|-?\d+(?:\.\d+)?)\s*([+\-*/])\s*"
        r"([A-Za-z_][A-Za-z0-9_]*|-?\d+(?:\.\d+)?)",
        expr,
    )
    if m is not None:
        lhs_tok, op_tok, rhs_tok = m.group(1), m.group(2), m.group(3)
        lhs = _resolve_token(df, lhs_tok)
        rhs = _resolve_token(df, rhs_tok)
        if op_tok == "+":
            return lhs + rhs
        if op_tok == "-":
            return lhs - rhs
        if op_tok == "*":
            return lhs * rhs
        if op_tok == "/":
            return lhs / rhs

    # Bare column reference
    if _COL_RE.match(expr):
        _require_columns(df, [expr])
        return df[expr]

    raise TransformError(f"unparseable expression: {expr!r}")


def _resolve_token(df: pd.DataFrame, token: str) -> Any:
    if _COL_RE.match(token):
        _require_columns(df, [token])
        return df[token].astype(float)
    return float(token)


def _select(df: pd.DataFrame, args: dict[str, Any]) -> pd.DataFrame:
    cols = args.get("columns")
    if not isinstance(cols, list) or not cols:
        raise TransformError("select requires non-empty 'columns'")
    names = [_check_column(c) for c in cols]
    _require_columns(df, names)
    return df.loc[:, names].copy()


def _recode(df: pd.DataFrame, args: dict[str, Any]) -> pd.DataFrame:
    col = _check_column(args.get("column"))
    mapping = args.get("mapping")
    if not isinstance(mapping, dict):
        raise TransformError("recode requires a 'mapping' dict")
    _require_columns(df, [col])
    out = df.copy()
    if "default" in args:
        default = args["default"]
        out[col] = out[col].map(lambda v: mapping.get(v, default)).where(
            ~out[col].isna(), other=None
        )
    else:
        # Preserve unmapped values (and NaN) as-is.
        out[col] = out[col].map(lambda v: mapping[v] if v in mapping else v)
    return out


def _drop_na(df: pd.DataFrame, args: dict[str, Any]) -> pd.DataFrame:
    cols = args.get("columns")
    if cols is None:
        return df.dropna().reset_index(drop=True)
    if not isinstance(cols, list):
        raise TransformError("drop_na 'columns' must be a list or null")
    names = [_check_column(c) for c in cols]
    _require_columns(df, names)
    return df.dropna(subset=names).reset_index(drop=True)


def _log_transform(df: pd.DataFrame, args: dict[str, Any]) -> pd.DataFrame:
    col = _check_column(args.get("column"))
    new_col = _check_column(args.get("new_column"))
    base = args.get("base", "e")
    _require_columns(df, [col])
    s = df[col].astype(float)
    if base == "e":
        out_vals = np.log(s)
    elif base == "10":
        out_vals = np.log10(s)
    elif base == "2":
        out_vals = np.log2(s)
    else:
        raise TransformError(f"log_transform base must be 'e', '10', or '2'; got {base!r}")
    out = df.copy()
    out[new_col] = out_vals
    return out


def _z_score(df: pd.DataFrame, args: dict[str, Any]) -> pd.DataFrame:
    col = _check_column(args.get("column"))
    new_col = _check_column(args.get("new_column"))
    _require_columns(df, [col])
    s = df[col].astype(float)
    mean = s.mean()
    std = s.std(ddof=1)
    if not math.isfinite(std) or std == 0:
        raise TransformError(f"z_score: column {col!r} has zero variance")
    out = df.copy()
    out[new_col] = (s - mean) / std
    return out


_VALID_AGGS = {"mean", "sum", "count", "min", "max", "median"}


def _group_summarise(df: pd.DataFrame, args: dict[str, Any]) -> pd.DataFrame:
    by = args.get("by")
    agg = args.get("agg")
    if not isinstance(by, list) or not by:
        raise TransformError("group_summarise requires non-empty 'by'")
    if not isinstance(agg, dict) or not agg:
        raise TransformError("group_summarise requires non-empty 'agg'")
    by_names = [_check_column(c) for c in by]
    _require_columns(df, by_names)
    agg_clean: dict[str, str] = {}
    for col, fn in agg.items():
        cname = _check_column(col)
        if fn not in _VALID_AGGS:
            raise TransformError(
                f"group_summarise: unknown aggregator {fn!r} for column {cname!r}"
            )
        _require_columns(df, [cname])
        agg_clean[cname] = fn
    grouped = df.groupby(by_names, dropna=False).agg(agg_clean).reset_index()
    return grouped


def _drop_rows(df: pd.DataFrame, args: dict[str, Any]) -> pd.DataFrame:
    """MP-stats-refine — Drop rows by their ORIGINAL positional index.

    The FE editable grid emits row ids of the form ``r-{index}`` where the
    index is the row's position in the unmutated dataset. We accept either
    integer indices or the ``r-<int>`` string form.
    """
    raw = args.get("indices") or args.get("drop_row_ids") or []
    if not isinstance(raw, list):
        raise TransformError("drop_rows requires a list of indices")
    indices: set[int] = set()
    for item in raw:
        if isinstance(item, int):
            indices.add(item)
            continue
        if isinstance(item, str):
            if item.startswith("r-"):
                try:
                    indices.add(int(item[2:]))
                    continue
                except ValueError:
                    pass
            try:
                indices.add(int(item))
                continue
            except ValueError:
                pass
        raise TransformError(f"drop_rows: invalid index {item!r}")
    if not indices:
        return df.reset_index(drop=True)
    # ``df.index`` is the post-prior-ops index. We compare against the
    # positional index — i.e. row number in the current frame, NOT the
    # original CSV — because earlier transformations may have reordered.
    keep_mask = [i for i in range(len(df)) if i not in indices]
    return df.iloc[keep_mask].reset_index(drop=True)


_DISPATCH = {
    "filter": _filter,
    "mutate": _mutate,
    "select": _select,
    "recode": _recode,
    "drop_na": _drop_na,
    "log_transform": _log_transform,
    "z_score": _z_score,
    "group_summarise": _group_summarise,
    "drop_rows": _drop_rows,
}


def apply_op(
    df: pd.DataFrame, op_type: str, op_args: dict[str, Any]
) -> pd.DataFrame:
    """Apply a single op. Returns a new DataFrame; original untouched."""
    if op_type not in _DISPATCH:
        raise TransformError(f"unknown op_type: {op_type!r}")
    if not isinstance(op_args, dict):
        raise TransformError("op_args must be a dict")
    return _DISPATCH[op_type](df, op_args)


def apply_transformations(
    df: pd.DataFrame, transformations: list[dict[str, Any]]
) -> pd.DataFrame:
    """Apply a list of ops in position order.

    Each op is a dict with keys 'op_type' and 'op_args' (extras like 'label'
    are ignored). The list is NOT mutated; ops are applied in the order they
    appear (callers are expected to pre-sort by position).
    """
    out = df
    for op in transformations:
        out = apply_op(out, op["op_type"], op.get("op_args") or {})
    return out
