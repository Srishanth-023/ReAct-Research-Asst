import sympy
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application

def calculate_tool(expression: str) -> str:
    """
    Safely evaluate symbolic or numeric mathematical expressions using sympy.
    Never uses raw Python eval().
    """
    clean_expr = expression.strip()
    if not clean_expr:
        return "Observation Error: Empty calculation expression provided."

    try:
        # Transformations allowing safe implicit multiplication and standard algebraic parsing
        transformations = (standard_transformations + (implicit_multiplication_application,))
        parsed = parse_expr(clean_expr, transformations=transformations, evaluate=True)
        
        # Try numeric evaluation to floating point if it has no free symbols
        if not parsed.free_symbols:
            # If float/int value
            evaluated = parsed.evalf()
            # Clean formatting (strip unnecessary .0 or excess decimal digits)
            float_val = float(evaluated)
            if float_val.is_integer():
                result_str = str(int(float_val))
            else:
                result_str = f"{float_val:.6g}"
        else:
            # Symbolic simplification
            simplified = sympy.simplify(parsed)
            result_str = str(simplified)

        return f"Observation: Calculator evaluation of `{clean_expr}` = {result_str}"

    except Exception as e:
        return f"Observation Error: Could not evaluate mathematical expression `{clean_expr}` using Sympy: {e}"
