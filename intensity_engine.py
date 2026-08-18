# -*- coding: utf-8 -*-
"""
Intensity & IDF Calculation Engine for Aeternum Aquae
Extensible framework for computing intensities, return periods, and IDF curves.
Uses a secure AST-based mathematical evaluator for formula processing.
"""

import math
import re
import ast
import operator

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_FUNCTIONS = {
    'log10': math.log10,
    'log': math.log10,
    'ln': math.log,
    'exp': math.exp,
    'sqrt': math.sqrt,
    'abs': abs,
}

def _eval_ast_node(node, variables):
    if isinstance(node, ast.Expression):
        return _eval_ast_node(node.body, variables)
    elif isinstance(node, ast.Constant):
        return float(node.value)
    elif isinstance(node, ast.Name):
        var_name = node.id.lower()
        if var_name in variables:
            return float(variables[var_name])
        raise ValueError(f"Variable no permitida o desconocida: {node.id}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in _OPERATORS:
            left = _eval_ast_node(node.left, variables)
            right = _eval_ast_node(node.right, variables)
            return _OPERATORS[op_type](left, right)
        raise ValueError(f"Operador binario no soportado: {op_type}")
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in _OPERATORS:
            operand = _eval_ast_node(node.operand, variables)
            return _OPERATORS[op_type](operand)
        raise ValueError(f"Operador unario no soportado: {op_type}")
    elif isinstance(node, ast.Call):
        func_name = node.func.id.lower() if isinstance(node.func, ast.Name) else ""
        if func_name in _FUNCTIONS:
            args = [_eval_ast_node(arg, variables) for arg in node.args]
            return _FUNCTIONS[func_name](*args)
        raise ValueError(f"Función no soportada: {func_name}")
    else:
        raise TypeError(f"Nodo AST no soportado: {type(node)}")

class IntensityEngine:
    """
    Computes precipitation intensities using Chen equation and station-specific formulas.
    """

    @staticmethod
    def calculate_chen_intensity(chen_a, chen_b, chen_c, x, duration_min, tr_years):
        """
        Calculates intensity i (mm/hr) using Chen formula:
        i = (a * R_tr) / ((d + b)^c)
        where R_tr = log10(10^(2 - x) * tr^(x - 1))
        """
        try:
            if any(v is None for v in (chen_a, chen_b, chen_c, duration_min, tr_years)):
                return None
            
            d = float(duration_min)
            tr = float(tr_years)
            a = float(chen_a)
            b = float(chen_b)
            c = float(chen_c)
            
            if d <= 0 or tr <= 0:
                return None

            if x is not None:
                x_val = float(x)
                term_log = math.log10((10.0 ** (2.0 - x_val)) * (tr ** (x_val - 1.0)))
                i = (a * term_log) / ((d + b) ** c)
            else:
                i = a / ((d + b) ** c)
            return round(float(i), 4)
        except Exception:
            return None

    @staticmethod
    def evaluate_formula(formula_str, duration_min, tr_years):
        """
        Safely evaluates station-specific intensity formula string using AST parser.
        Example: "(36.7333 * 40.6336 * LOG10(10^(2 - 1.3623) * tr^(1.3623 - 1))) / ((d + 11.5014)^0.8636)"
        """
        if not formula_str:
            return None
        try:
            d = float(duration_min)
            tr = float(tr_years)
            
            # Reemplazar ^ por ** para sintaxis de potencia en Python
            expr = formula_str.replace('^', '**')
            
            # Parsear en AST seguro (sin ejecución eval)
            tree = ast.parse(expr, mode='eval')
            variables = {'d': d, 'tr': tr}
            result = _eval_ast_node(tree, variables)
            return round(float(result), 4)
        except Exception:
            return None

    @classmethod
    def compute_custom_intensities(cls, station_props, durations_min, tr_years_list):
        """
        Computes intensities for combinations of durations and return periods.
        Returns a dictionary of column_name -> calculated_intensity.
        """
        results = {}
        chen_a = station_props.get('chen_a')
        chen_b = station_props.get('chen_b')
        chen_c = station_props.get('chen_c')
        x_val = station_props.get('x')
        formula_i = station_props.get('formula_i')

        for tr in tr_years_list:
            for d in durations_min:
                col_name = f"i_TR{int(tr) if tr.is_integer() else tr}_{int(d) if d.is_integer() else d}m"
                val = None
                if formula_i:
                    val = cls.evaluate_formula(formula_i, d, tr)
                if val is None and chen_a is not None and chen_b is not None and chen_c is not None:
                    val = cls.calculate_chen_intensity(chen_a, chen_b, chen_c, x_val, d, tr)
                
                results[col_name] = val
        return results
