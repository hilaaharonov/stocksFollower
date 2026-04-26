"""Script execution service.

User scripts are Python snippets that receive a ``context`` dict with stock data
and can append alert messages to ``context['alerts']``.

Example script:
    # Alert when close price drops more than 5% from open
    if context['close'] is not None and context['open'] is not None:
        change_pct = (context['close'] - context['open']) / context['open'] * 100
        if change_pct < -5:
            context['alerts'].append(f"Price dropped {change_pct:.2f}% today!")
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Allowed built-ins for sandboxed script execution
_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,

    "range": range,
    "round": round,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "zip": zip,
}


def run_script(code: str, stock_data: dict) -> list[str]:
    """Execute a user script and return generated alert messages.

    Args:
        code: Python script source code.
        stock_data: Dict with keys like symbol, close, open, high, low, volume,
                    and optionally 'history' (list of recent OHLCV dicts).

    Returns:
        List of alert message strings produced by the script.
    """
    context = {
        **stock_data,
        "alerts": [],
    }
    safe_globals = {"__builtins__": _SAFE_BUILTINS, "context": context}
    try:
        exec(code, safe_globals)  # noqa: S102
    except Exception as exc:
        logger.error("Script execution error: %s", exc)
        context["alerts"].append("Script execution failed. Check the server logs for details.")
    return list(context.get("alerts", []))


def validate_script(code: str) -> Optional[str]:
    """Validate that a script can be compiled without errors.

    Returns an error message string if invalid, else None.
    """
    try:
        compile(code, "<script>", "exec")
        return None
    except SyntaxError as exc:
        return f"Syntax error at line {exc.lineno}: {exc.msg}"
