"""
clippy_calc.py
A Clippy-like assistant that computes multivariable calculus operations using SymPy.

Requirements:
  pip install sympy numpy

Run:
  python clippy_calc.py

To build a one-file Windows exe:
  pip install pyinstaller
  pyinstaller --onefile --noconsole clippy_calc.py
"""

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import time
import sympy as sp
import math
import traceback

# -------------------------
# Small animated Clippy
# -------------------------
class ClippyCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=120, height=140, bg="white", highlightthickness=0, **kwargs)
        self.clip = None
        self.offset = 0
        self.dir = 1
        self._draw_clip()
        self.animate()

    def _draw_clip(self):
        self.delete("all")
        # draw a simple paperclip-like shape using arcs/lines
        # Outer loop
        self.create_oval(20, 20 + self.offset, 100, 100 + self.offset, outline="#666", width=4)
        # inner loop
        self.create_oval(32, 32 + self.offset, 88, 88 + self.offset, outline="#999", width=3)
        # "eye" for personality
        self.create_oval(52, 40 + self.offset, 60, 48 + self.offset, fill="#222")
        # little shadow base
        self.create_oval(30, 100 + self.offset, 90, 110 + self.offset, fill="#eee", outline="")

    def animate(self):
        # bob up and down
        self.offset += 0.6 * self.dir
        if self.offset > 6: self.dir = -1
        if self.offset < -6: self.dir = 1
        self._draw_clip()
        self.after(80, self.animate)

# -------------------------
# Calculator / worker logic
# -------------------------
class CalcEngine:
    def __init__(self):
        # default symbols commonly used
        self.symbols = {
            'x': sp.symbols('x'),
            'y': sp.symbols('y'),
            'z': sp.symbols('z'),
            't': sp.symbols('t')
        }

    def _ensure_symbols(self, var_names):
        # create symbols if not exists
        for v in var_names:
            if v not in self.symbols:
                self.symbols[v] = sp.symbols(v)
        return [self.symbols[v] for v in var_names]

    def parse_expr(self, expr_str):
        """Parse expression string into sympy expression with standard symbols available."""
        # provide a safe local dict for sympy parsing
        local_dict = dict(self.symbols)
        try:
            expr = sp.sympify(expr_str, locals=local_dict)
            return expr
        except Exception as e:
            # try to auto-detect variable names and create them then reparse
            words = {w for w in sp.sympify(0).free_symbols}  # dummy to access type
            # fallback: attempt to replace ^ with **
            try:
                expr = sp.sympify(expr_str.replace('^', '**'), locals=local_dict)
                return expr
            except Exception as e2:
                raise

    # ---- Basic ops ----
    def gradient(self, expr, vars):
        syms = self._ensure_symbols(vars)
        return [sp.simplify(sp.diff(expr, s)) for s in syms]

    def partial(self, expr, var, order=1):
        s = self._ensure_symbols([var])[0]
        return sp.simplify(sp.diff(expr, s, order))

    def hessian(self, expr, vars):
        syms = self._ensure_symbols(vars)
        H = sp.Matrix([[sp.simplify(sp.diff(expr, si, sj)) for sj in syms] for si in syms])
        return H

    def jacobian(self, funcs, vars):
        # funcs: list of expressions
        syms = self._ensure_symbols(vars)
        F = sp.Matrix(funcs)
        J = F.jacobian(syms)
        return J

    def divergence(self, vec_field, vars):
        syms = self._ensure_symbols(vars)
        assert len(vec_field) == len(syms), "Vector field length must match variable list for divergence."
        return sum(sp.diff(vec_field[i], syms[i]) for i in range(len(syms)))

    def curl(self, vec_field, vars):
        # Only defined for 3D vector fields (x,y,z)
        syms = self._ensure_symbols(vars)
        if len(vec_field) != 3 or len(syms) < 3:
            raise ValueError("Curl requires a 3-component vector field and at least x,y,z symbols.")
        x, y, z = syms[0], syms[1], syms[2]
        F = vec_field
        curl_vec = sp.Matrix([
            sp.diff(F[2], y) - sp.diff(F[1], z),
            sp.diff(F[0], z) - sp.diff(F[2], x),
            sp.diff(F[1], x) - sp.diff(F[0], y)
        ])
        return sp.simplify(curl_vec)

    def multiple_integral(self, expr, limits):
        # limits: list of tuples (var, a, b) in correct order (inner to outer)
        syms = []
        for v, a, b in limits:
            syms.extend([v])
        # ensure symbols exist
        for v, a, b in limits:
            self._ensure_symbols([v])
        it = expr
        # integrate inner to outer in given order
        for (v, a, b) in limits:
            sym = self.symbols[v]
            it = sp.integrate(it, (sym, sp.sympify(a), sp.sympify(b)))
        return sp.simplify(it)

    def line_integral(self, F_vec, param, t_var, bounds):
        # F_vec: vector field (list of expr in x,y,z or x,y)
        # param: list of parametric functions [x(t), y(t), z(t)?]
        # t_var: symbol name for parameter
        # bounds: (t0, t1)
        t = self._ensure_symbols([t_var])[0]
        param_syms = [sp.sympify(p) for p in param]
        # compute r'(t)
        rprime = [sp.diff(p, t) for p in param_syms]
        # substitute x,y,z in F with param
        subs_map = {}
        # decide how many components
        varnames = ['x', 'y', 'z']
        for i, comp in enumerate(param_syms):
            subs_map[self.symbols[varnames[i]]] = comp
        Fsub = [sp.simplify(sp.N(F.subs(subs_map))) if isinstance(F, sp.Expr) else F for F in F_vec]
        # compute dot(F(r(t)), r'(t))
        integrand = sum(sp.simplify(sp.sympify(F_vec[i]).subs(subs_map) * rprime[i]) for i in range(len(rprime)))
        return sp.integrate(integrand, (t, sp.sympify(bounds[0]), sp.sympify(bounds[1])))

# -------------------------
# GUI
# -------------------------
class ClippyApp:
    def __init__(self, root):
        self.root = root
        root.title("ClippyCalc — Multivariable Calculus Assistant")
        root.geometry("920x520")
        root.configure(bg="#f4f6f8")
        self.engine = CalcEngine()

        # left: Clippy + suggestions
        left = tk.Frame(root, width=200, bg="#f4f6f8")
        left.pack(side="left", fill="y", padx=10, pady=10)

        self.clippy = ClippyCanvas(left)
        self.clippy.pack(pady=8)

        self.speech = tk.Label(left, text="Hi! I'm ClippyCalc.\nType an expression and press an operation button.", 
                               justify="left", bg="#f4f6f8", fg="#222", wraplength=180)
        self.speech.pack(pady=6)

        # suggestions/help
        help_text = (
            "Tips:\n"
            "- Use x,y,z,t as variables (auto-created)\n"
            "- For vector fields: enter components comma-separated\n"
            "- Exponent: use ** or ^ (both supported)\n"
            "- Examples:\n  f: x**2 + y*z\n  vector: x*y, sin(y), z**2\n  param: cos(t), sin(t), t\n"
        )
        tk.Label(left, text=help_text, bg="#f4f6f8", fg="#444", justify="left", wraplength=180).pack(pady=6)

        # center: main controls
        center = tk.Frame(root, bg="#ffffff")
        center.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        top_row = tk.Frame(center, bg="#ffffff")
        top_row.pack(fill="x", padx=8, pady=6)

        tk.Label(top_row, text="Expression / Function(s):", bg="#ffffff").pack(anchor="w")
        self.expr_entry = tk.Entry(top_row, font=("Consolas", 12))
        self.expr_entry.pack(fill="x", pady=4)

        tk.Label(top_row, text="Variables (comma separated, e.g. x,y,z):", bg="#ffffff").pack(anchor="w")
        self.vars_entry = tk.Entry(top_row, font=("Consolas", 10))
        self.vars_entry.pack(fill="x", pady=4)
        self.vars_entry.insert(0, "x,y,z")

        # operation buttons
        ops = tk.Frame(center, bg="#ffffff")
        ops.pack(fill="x", pady=6)
        btn_specs = [
            ("Gradient", self.do_gradient),
            ("Divergence", self.do_divergence),
            ("Curl", self.do_curl),
            ("Jacobian", self.do_jacobian),
            ("Hessian", self.do_hessian),
            ("Partial ∂/∂", self.do_partial),
            ("Double/Triple Integral", self.do_integral),
            ("Line Integral", self.do_line_integral),
            ("Taylor Series", self.do_taylor),
            ("Limit", self.do_limit),
            ("Simplify", self.do_simplify),
        ]
        for i, (label, cmd) in enumerate(btn_specs):
            b = tk.Button(ops, text=label, command=lambda c=cmd: self._run_threaded(c), width=16)
            b.grid(row=i//3, column=i%3, padx=6, pady=6)

        # right: output
        right = tk.Frame(root, width=320, bg="#f9fafb")
        right.pack(side="right", fill="y", padx=10, pady=10)

        tk.Label(right, text="Output:", bg="#f9fafb").pack(anchor="w")
        self.output = ScrolledText(right, width=40, height=26, font=("Consolas", 11))
        self.output.pack(fill="both", expand=True, pady=6)

        # footer quick examples
        footer = tk.Frame(right, bg="#f9fafb")
        footer.pack(fill="x")
        tk.Button(footer, text="Example: gradient(x**2 + y*z)", command=self.example1).pack(side="left", padx=4)
        tk.Button(footer, text="Example: curl(x*y, y*z, z*x)", command=self.example2).pack(side="left", padx=4)
        tk.Button(footer, text="Clear", command=lambda: self.output.delete("1.0", tk.END)).pack(side="right", padx=4)

    # ----------------------
    # Utility / UI helpers
    # ----------------------
    def _write(self, text):
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)

    def _run_threaded(self, func):
        self._write("Clippy: Working... ⏳")
        threading.Thread(target=self._wrap_call, args=(func,), daemon=True).start()

    def _wrap_call(self, func):
        try:
            # remove the "Working..." line at end then call
            # simple approach: just add a divider
            res = func()
            self._write("--- Done ---")
        except Exception as e:
            self._write("Error: " + str(e))
            tb = traceback.format_exc()
            self._write(tb)

    def _get_expr_and_vars(self):
        expr_str = self.expr_entry.get().strip()
        var_str = self.vars_entry.get().strip()
        vars = [v.strip() for v in var_str.split(",") if v.strip() != ""]
        if expr_str == "":
            raise ValueError("No expression entered.")
        return expr_str, vars

    # ----------------------
    # Operations
    # ----------------------
    def do_gradient(self):
        expr_str, vars = self._get_expr_and_vars()
        expr = self.engine.parse_expr(expr_str)
        grad = self.engine.gradient(expr, vars)
        self._write(f"∇({sp.srepr(expr)}) =")
        for v, g in zip(vars, grad):
            self._write(f"  ∂/∂{v}: {sp.pretty(g)}")

    def do_divergence(self):
        expr_str, vars = self._get_expr_and_vars()
        # expect comma-separated vector components in expr_entry
        comps = [c.strip() for c in expr_str.split(",")]
        vec = [self.engine.parse_expr(c) for c in comps]
        div = self.engine.divergence(vec, vars)
        self._write(f"div = {sp.pretty(sp.simplify(div))}")

    def do_curl(self):
        expr_str, vars = self._get_expr_and_vars()
        comps = [c.strip() for c in expr_str.split(",")]
        if len(comps) != 3:
            raise ValueError("Curl expects 3 components separated by commas.")
        vec = [self.engine.parse_expr(c) for c in comps]
        curlv = self.engine.curl(vec, vars)
        self._write("curl =")
        for comp in curlv:
            self._write(f"  {sp.pretty(sp.simplify(comp))}")

    def do_jacobian(self):
        expr_str, vars = self._get_expr_and_vars()
        # functions comma separated
        funcs = [self.engine.parse_expr(c.strip()) for c in expr_str.split(",")]
        J = self.engine.jacobian(funcs, vars)
        self._write("Jacobian =")
        self._write(str(J))

    def do_hessian(self):
        expr_str, vars = self._get_expr_and_vars()
        expr = self.engine.parse_expr(expr_str)
        H = self.engine.hessian(expr, vars)
        self._write("Hessian =")
        self._write(str(H))

    def do_partial(self):
        expr_str, vars = self._get_expr_and_vars()
        # ask for variable and order
        # use a simple prompt dialog
        v = self._prompt("Variable for partial derivative (e.g. x):")
        order = self._prompt("Order (1 for first derivative):")
        try:
            order = int(order)
        except:
            order = 1
        res = self.engine.partial(self.engine.parse_expr(expr_str), v, order)
        self._write(f"∂^{order}/{v}^{order}: {sp.pretty(res)}")

    def do_integral(self):
        expr_str = self.expr_entry.get().strip()
        # prompt for limits format: var,a,b;var,a,b (inner to outer)
        limits_str = self._prompt("Enter limits as: var,a,b ; var,a,b (inner -> outer)\nExample: x,0,1 ; y,0,2")
        if not limits_str:
            raise ValueError("No limits provided.")
        limits = []
        parts = [p.strip() for p in limits_str.split(";")]
        for p in parts:
            v,a,b = [s.strip() for s in p.split(",")]
            limits.append((v, a, b))
        expr = self.engine.parse_expr(expr_str)
        res = self.engine.multiple_integral(expr, limits)
        self._write(f"Integral result: {sp.pretty(res)}")

    def do_line_integral(self):
        expr_str = self.expr_entry.get().strip()
        comps = [c.strip() for c in expr_str.split(",")]
        # prompt for param functions and bounds
        param_str = self._prompt("Parametric curve components (comma separated) e.g. cos(t), sin(t), t")
        tvar = self._prompt("Parameter name (default t):") or "t"
        bounds = self._prompt("Bounds for parameter as t0,t1 (e.g. 0,2*pi)")
        if not param_str or not bounds:
            raise ValueError("Missing param or bounds.")
        params = [p.strip() for p in param_str.split(",")]
        t0, t1 = [s.strip() for s in bounds.split(",")]
        res = self.engine.line_integral(comps, params, tvar, (t0, t1))
        self._write(f"Line integral result: {sp.pretty(sp.simplify(res))}")

    def do_taylor(self):
        expr_str, vars = self._get_expr_and_vars()
        point_str = self._prompt("Expansion point as comma list matching variables (e.g. 0,0,0)")
        order_str = self._prompt("Order (e.g. 2)")
        try:
            order = int(order_str)
        except:
            order = 2
        point = [sp.sympify(s.strip()) for s in point_str.split(",")]
        expr = self.engine.parse_expr(expr_str)
        # multivariable Taylor via series_expansion from sympy is limited; do multivariate approximation using series around point via multivariate Taylor (limited)
        # We'll provide a simple multivariate Taylor by expanding in each variable up to order (not fully general mixed terms up to total order)
        vars = [v.strip() for v in self.vars_entry.get().split(",") if v.strip()]
        syms = self.engine._ensure_symbols(vars)
        series = sp.series(expr, *[(syms[i], point[i], order) for i in range(len(point))])
        self._write("Taylor series (approx):")
        self._write(str(series))

    def do_limit(self):
        expr_str, vars = self._get_expr_and_vars()
        # prompt for var and point
        var = self._prompt("Variable for limit (e.g. x):")
        point = self._prompt("Point (use oo for infinity):")
        dir_ = self._prompt("Direction (+, -, or both). Leave blank for both:")
        if dir_ == "+":
            dirn = "+"
        elif dir_ == "-":
            dirn = "-"
        else:
            dirn = None
        res = sp.limit(self.engine.parse_expr(expr_str), self.engine._ensure_symbols([var])[0], sp.sympify(point), dirn)
        self._write(f"Limit = {sp.pretty(res)}")

    def do_simplify(self):
        expr_str = self.expr_entry.get().strip()
        res = sp.simplify(self.engine.parse_expr(expr_str))
        self._write(f"Simplified: {sp.pretty(res)}")

    # ----------------------
    # Examples / prompts
    # ----------------------
    def example1(self):
        self.expr_entry.delete(0, tk.END)
        self.expr_entry.insert(0, "x**2 + x*y + sin(z)")
        self.vars_entry.delete(0, tk.END)
        self.vars_entry.insert(0, "x,y,z")
        self._write("Loaded example: gradient of x**2 + x*y + sin(z)")

    def example2(self):
        self.expr_entry.delete(0, tk.END)
        self.expr_entry.insert(0, "x*y, y*z, z*x")
        self.vars_entry.delete(0, tk.END)
        self.vars_entry.insert(0, "x,y,z")
        self._write("Loaded example: curl of (x*y, y*z, z*x)")

    def _prompt(self, msg):
        # simple dialog-like blocking prompt using Toplevel
        res = []
        def done():
            res.append(entry.get().strip())
            top.destroy()
        top = tk.Toplevel(self.root)
        top.transient(self.root)
        top.grab_set()
        tk.Label(top, text=msg, wraplength=400).pack(padx=12, pady=8)
        entry = tk.Entry(top, width=60)
        entry.pack(padx=12, pady=8)
        entry.focus()
        btn = tk.Button(top, text="OK", command=done)
        btn.pack(pady=6)
        self.root.wait_window(top)
        return res[0] if res else None

# -------------------------
# Run
# -------------------------
def main():
    root = tk.Tk()
    app = ClippyApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
