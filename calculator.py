# -*- coding: latin-1 -*-
"""
Functions to run an interpreter for expressions containing physical quantities.

Based on the Q class in the quantities module, this provides functions to input and interpret expressions,
calculating their values and showing the steps, and finally storing the quantities so that they can be
used for further calculations.

This is an arithmetic calculator rather than an algebra system (i.e. unknowns are not allowed and will lead to
error messages). Output is either in HTML or in MathML via Asciimath.
"""

from __future__ import division

import quantities
from quantities import Q, Units, QuantError, math_name


class CalcError(ArithmeticError): pass


try:
    from re import Scanner
except:
    from sre import Scanner


def identifier(scanner, token): return ["I", token.strip()]


def operator(scanner, token): return ["O", token.strip()]


def float2(scanner, token): return ["N", token.strip()]


def comment(scanner, token): return ["C", token.strip()]


scanner = Scanner([
    (r"(([a-zA-Zμ]\w*(\[[^]]+\])?)|(\[[^]]+\])|(\{[^}]+\})|\$)", identifier),
    (r"((\d*\.\d+)|(\d+\.?))([Ee][+-]?\d+)?", float2),
    (r"[ ,()/*^+-]+", operator),
    (r"[#!].*", comment)
])


def scan(t):
    """scan text for identifers(I), operators(O), numbers(N) and comments(C)"""
    tokens, remainder = scanner.scan(t + " ")
    if remainder:
        raise CalcError("got stuck on |%s|" % remainder)
    parentheses = 0
    for ttype, ttext in tokens:
        if ttype == "O":
            parentheses += ttext.count("(") - ttext.count(")")
    if parentheses:
        raise CalcError("Parentheses don't match: %s" % repr(tokens))
    tokens.append(["Z", ""])
    for i, (ttype, ttext) in enumerate(tokens):
        if ttype == "I":
            if ttext in quantities.unitquant:
                tokens[i] = ("U", ttext)
            elif ttext in quantities.functions:
                tokens[i] = ("F", ttext)
    return tokens


def fixoperator(operator, tokens):
    """
    Add implicit '*' to operator unless it follows a function call.

    e.g. 'I I' -> 'I *I', 'I)(I' -> 'I)*(I', but 'F(I' is unchanged
    """
    if tokens and tokens[-1][0] == "F":
        return operator
    for i, c in enumerate(operator):
        if c in " )":
            continue
        if c == "(":
            i = i - 1
            break
    return operator[:i + 1] + "*" + operator[i + 1:]


def make_paired_tokens(raw_tokens):
    """
    Process raw tokens into paired tokens containing item ID (N, U, I, Z), pre-operator and item text.

    This is the first step in turning the input text into a Python expression.
    Add implicit '*' operators, pick up units(I -> U) and deal with comments.
    """
    tokens = []
    tokenit = (x for x in raw_tokens)
    for ttype, ttext in tokenit:
        if ttype == "O":
            if ttext:
                operator = ttext
            else:
                operator = "*"
            for c in operator:
                if c in "+-*/^,":
                    break
            else:
                operator = fixoperator(operator, tokens)
            if hasattr(tokenit, "__next__"):
                ttype, ttext = tokenit.__next__()
            else:
                ttype, ttext = tokenit.next()
        else:
            operator = "*"
        if ttype == "C":
            tokens.append(["Z", operator, ""])
            break
        tokens.append([ttype, operator.replace("^", "**"), ttext])
    return tokens


def interpret_N_U_cluster(quant, orig_paired, result):
    paired = orig_paired[:]
    start = None
    openp = 0
    for i, (ttype, op, ttext) in enumerate(paired):
        if not (paired[i][0] == "U" or (paired[i][0] == "N" and "**" in paired[i][1])):
            break
        o = op.count("(")
        c = op.count(")")
        if o:
            openp += o
            if not start:
                start = i
        if c:
            openp -= c
            if openp < 0:
                break
            start = None
    end = start if start else i
    for j in range(end):
        quant.append(paired[j][1] + "Q('%s')" % paired[j][2])
    quantstr = "".join(quant)
    openparentheses = quantstr.count("(") - quantstr.count(")")
    try:
        if openparentheses > 0:
            for i, c in enumerate(paired[end][1]):
                if c == ")":
                    openparentheses -= 1
                if not openparentheses:
                    break
            else:
                raise CalcError("parentheses count off %s %s" % (quant, paired[end][1]))
            quantstr = quantstr + paired[end][1][:i + 1]
            paired[end][1] = paired[end][1][i + 1:]
        q = eval(quantstr)
    except QuantError:
        raise
    except:
        return quant[0], orig_paired
    q.name = ""
    q.provenance = []
    return repr(q), paired[end:]


def create_Python_expression(paired_tokens, symbols):
    result = []
    while True:  # consume "Z", "I", "F", "U", "N" in paired_tokens
        ttype, operator, ttext = paired_tokens.pop(0)
        if ttype in "ZIF":
            result.append(operator)
            if ttype == "Z":
                break
            if ttype == "F":
                result.append("quantities." + ttext)
            else:  # ttype == "I"
                if ttext in symbols:
                    result.append(repr(symbols[ttext]))
                else:
                    raise ValueError("unknown symbol %s encountered" % ttext)
            continue
        quant = ["Q('%s')" % ttext]
        if ttype == "N" and paired_tokens[0][0] != "U":
            result.append(operator)
            result.append(quant[0])
            continue
        quant_text, paired_tokens = interpret_N_U_cluster(quant, paired_tokens, result)
        result.append('%s%s' % (operator, quant_text))
    expression = "".join(result)[:-1]
    if expression.startswith("*"):
        return expression[1:]
    return expression


def interpret(t, symbols, output, mob):
    """Process input text into a valid Python expression and return the result of evaluating it"""
    paired = make_paired_tokens(scan(t))
    try:
        expression = create_Python_expression(paired, symbols)
        return eval(expression)
    except QuantError as err:
        explain_failure(t, err, output, mob)
        raise CalcError("")
    except SyntaxError as err:
        raise CalcError('%s<br><br><div style="color: red;">Mangled math</div><br><br>'
                        % t)
    except OverflowError as duh:
        raise CalcError('%s<br><br><div style="color: red;">Math overflow</div><br><br>'
                        % t)


rules_for_symbol_name = """Rules for names: Start with a letter, then letters or numbers or underscores.
  Examples: m0, y, s_15
Special rule #1: You can add anything in brackets, [...], or just have something in brackets
  Examples: [NaCl], [Na+], c[Na+], M[Na+]
Special rule #2: You can't use names already used for units. If you do, the program will add an underscore.
  Examples: mm, s, V are not allowed, and will be used as mm_, s_, V_"""


def load_symbols(oldsymbols):
    symbols = {}
    symbollist = []
    logput = []
    output = []
    if oldsymbols:
        oldsymbols = oldsymbols.replace('\r', '')
        old = oldsymbols.split('\n')
        for a in old:
            sym = a.split("'")[1]
            symbols[sym] = eval(a)
            symbollist.append(sym)
    return symbols, symbollist


def calc_without_assignment(a, output, symbols, mob):
    output.append('<pre>%s</pre>' % a)
    if " using " in a:
        quant, units = a.split(" using ")
        prefu = units.split()
        q = symbols[quant.strip()]
        q.prefu = prefu
        if mob == "ipud":
            output.append("%s = %s<br>" % (str(quant), q.intermediate_steps(0, math=False)))
        else:
            output.append("`%s = %s`" % (math_name(quant.strip()), q.intermediate_steps(0, math=(mob != "ipud"))))
    elif " in " in a:
        quant, units = a.split(" in ")
        tmp = interpret(units, symbols, output, mob)
        task = tmp.task(math=(mob != "ipud"))
        qq = symbols[quant.strip()] / tmp
        number3, units2 = quantities.unit_string(qq.number, qq.units, math=(mob != "ipud"))
        nstr = quantities.numberstring(number3, qq.sigfig, math=True)
        if mob == "ipud":
            output.append("%s = %s%s %s<br>" % (str(quant), nstr, units2, units))
        else:
            output.append("`%s = %s%s` %s" %
                          (math_name(quant.strip()), nstr, units2, units))
    else:
        return False
    output.append("<hr>")
    return True


def figure_out_name(a, output, logput):
    if "=" in a:
        sym, expression = a.split("=", 1)
        sym = sym.strip()
        expression = expression.strip()
        tokens, remainder = scanner.scan(sym)
        if len(tokens) != 1 or tokens[0][0] != "I":
            raise CalcError(("Please don't use %s as a name for a quantity<br><pre>%s<pre>" %
                             (sym, rules_for_symbol_name)))
        if sym in quantities.unitquant or sym in quantities.functions:
            conf = "function" if sym in quantities.functions else "unit"
            output.append(
                '<div style="color: green;">Warning: %s changed to %s_ to avoid confusion with the %s</div>' % (
                sym, sym, conf))
            sym = sym + "_"
        output.append("<pre>\n%s = %s</pre>" % (sym, expression))
        logput.append("\n%s = %s" % (sym, expression))
    else:
        sym = "result"
        expression = a
        output.append("<pre>\n%s = %s</pre>" % (sym, a))
    return sym, expression


def show_work(result0, sym, expression, output, logput, math=True):
    start = result0.task(math=math)
    if str(result0) != expression.strip():
        logput.append("  = %s" % str(result0))
    d = result0.setdepth()
    if math:
        template1 = "`%s = %s`<br><br>"
        template2 = "`\\ \\ \\ =%s`<br><br>"
    else:
        template1 = "%s = %s<br>" if d <= 0 else "%s = <br>&nbsp;&nbsp;&nbsp;= %s<br>"
        template2 = "&nbsp;&nbsp;&nbsp;= %s<br>"
    name = math_name(sym) if math else str(sym)
    output.append(template1 % (name, start))
    for dd in range(1, d + 2):
        interm = result0.intermediate_steps(dd, math=math)
        if interm != start:
            output.append(template2 % interm)
    result0.provenance = []


def register_result(result0, sym, symbols, symbollist, output):
    result0.name = sym[:]
    if sym in symbols:
        output.append('<div style="color: green;">Warning: Updated value of %s</div><br>' % sym)
    else:
        symbollist.append(sym)
    symbols[sym] = result0


def explain_failure(a, error, output, mob):
    output.append(a)
    duh = error.args[0]
    output.append('<br><br><div style="color: red;">Calculation failed: %s</div><br><br>' % duh[0])
    if not duh[1]:
        output.append('<hr>')
        return
    d = duh[1].setdepth()
    start = duh[1].task(math=(mob != "ipud"))
    output.append("`text{problem} = %s`<br><br>" % start)
    for dd in range(1, d + 1):
        inter = duh[1].intermediate_steps(dd, math=(mob != "ipud"))
        if inter != start:
            output.append("`\\ \\ \\ = %s`<br><br>" % inter)
    output.append("<hr>")
    return


def calc(oldsymbols, commands, mob):
    symbols, symbollist = load_symbols(oldsymbols)
    logput = []
    output = []
    commands = commands.replace('\r', '')
    commands = commands.split("\n")
    for a in commands:
        if not a or not a.strip():
            continue
        if a.startswith("!") or a.startswith("#"):
            output.append('<div style="color: blue;"><pre>%s</pre><hr></div>' % a[1:])
            continue
        try:
            if not "=" in a:
                if calc_without_assignment(a, output, symbols, mob):
                    continue
            sym, expression = figure_out_name(a, output, logput)
            result0 = interpret(expression, symbols, output, mob)
            show_work(result0, sym, expression, output, logput, math=(mob != 'ipud'))
            register_result(result0, sym, symbols, symbollist, output)
        except QuantError as err:
            output.append(err.args[0][0])
        except CalcError as err:
            output.append(err.args[0])
        except ValueError as err:
            output.append(err.args[0])
        output.append("<hr>")
    memory = [symbols[s].__repr__() for s in symbollist]
    known = [s + " = " + symbols[s].__str__() for s in symbollist]
    # return ["fake output"], logput, memory, known, mob
    return output, logput, memory, known, mob


if __name__ == "__main__":
    mob = "ipud"
    symbols = {}
    symbollist = []
    command = raw_input("pqcalc>>>")
    while "=" in command:
        output = []
        logput = []
        try:
            sym, expression = figure_out_name(command, output, logput)
            result0 = interpret(expression, symbols, output, mob)
            show_work(result0, sym, expression, output, logput, mob)
            register_result(result0, sym, symbols, symbollist, output)
        except CalcError as err:
            output.append(err.args[0])
        for line in output:
            print (line)
        command = raw_input("pqcalc>>>")    
        

"""
Test input that should fail gracefully:

sadf = 56 * (67 )()

asdf = 5 + t + &#@

gg = sin(45)

vv = 10^10^10

omg = 1 / 10^-1000
"""
