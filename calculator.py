# coding=utf-8
"""
Functions to run an interpreter for expressions containing physical quantities.

Based on the Q class in the quantities module, this provides functions to input and interpret expressions,
calculating their values and showing the steps, and finally storing the quantities so that they can be
used for further calculations.

This is an arithmetic calculator rather than an algebra system (i.e. unknowns are not allowed and will lead to
error messages). Output is either in plain text or in HTML/MathML via LaTeX.

Call hierarchy:

    calc(oldsymbols, commands, mob):
        gather_symbols(oldsymbols):
        classify_input(a, tutor=False):

        check_name(sym, expression, output, logput, symbols):
        interpret(t, symbols, output, mob):
            scan(t):
                identifier(scanner, token):
                operator(scanner, token):
                float2(scanner, token):
                comment(scanner, token):
            make_paired_tokens(raw_tokens):
                fixoperator(operator, tokens):
            create_Python_expression(paired_tokens, symbols):
                interpret_N_U_cluster(quant, orig_paired, result):
                magic (numberstring):
            eval:
            explain_failure(a, error, output, symbols, mob):
        register_result(result0, sym, symbols, symbollist, output):
        show_work(result, sym, output, symbols, math, logput=None, error=False, addon = "", skipsteps = False):

        convert_units(input_type, command, quant, units, output, logput, symbols, mob):
        create_comment(a, logput, output, symbols):
            comments(line):
                consume_comment(charlist):
                consume_identifier(charlist):
                format_identifier(name):
                consume_formula(charlist):
        deal_with_errors(err, a, output, symbols):
        wrap_up(output, symbollist, symbols):

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import quantities
from quantities import Q, Units, QuantError, latex_name, unitquant
from re import Scanner, UNICODE, match

class CalcError(ArithmeticError): pass

def calc(oldsymbols, commands, mob):
    '''

    :param oldsymbols: quantities already defined
    :param commands: user input specifying math to define new quantities
    :param mob: device the output will be sent to (determines format)
    :return: everything needed to show the result in a browser and keep state for the next calculation
    '''
    symbols, symbollist = gather_symbols(oldsymbols)
    logput, output = [""], []
    command_list = commands.replace('\r', '').split("\n")
    try:
        for command in command_list:
            input_type, name, expression = classify_input(command, '__tutor__' in symbols)
            if input_type == Calculation:
                check_name(name, output)
                quantity = interpret(expression, symbols, output, mob)
                show_work(quantity, name, output, symbols, math=(mob != 'ipud'), logput=logput)
                register_result(quantity, name, symbols, symbollist, output)
            elif input_type == Comment:
                create_comment(command, logput, output, symbols)
            elif input_type in [ConversionUsing, ConversionIn]:
                convert_units(input_type, command, name, expression, output,logput, symbols, mob)
            #else: pass because command is empty
    except Exception as err:
        output = deal_with_errors(err, command, output, symbols)
    known, memory, oneline, output = wrap_up(output, symbollist, symbols)
    return output, logput, memory, known, mob, oneline


def gather_symbols(memory):
    '''
    Loads quantities from previous calculations by evaluating their repr()s

    :param memory: String of repr()s
    :return:(dict of symbols, ordered list of symbols)
    '''
    allsymbols = {}
    symbollist = []
    if memory:
        old = memory.replace('\r', '').split('\n')
        for a in old:
            sym = a.split("'")[1]
            allsymbols[sym] = eval(a)
            symbollist.append(sym)
    return allsymbols, symbollist


def classify_input(a, tutor=False):
    '''
    :param a: the user input string containing a calculation, unit conversion or comment
    :param tutor: if True, mirrors input and, if no name is given for result, raises exception
    :return: a tuple (type of input, symbol name, expression/units)

    Empty, Calculation, ConversionIn, ConversionUsing, Comment = range(5)

    >>> classify_input(' ')
    (0, None, None)
    >>> classify_input('K[A<=>B] = 13')
    (1, u'K[A<=>B]', u' 13')
    >>> classify_input('R using J')
    (3, u'R', u'J')
    >>> classify_input('K[A<=>B] in mM')
    (2, u'K[A<=>B]', u'mM')
    >>> classify_input('5 + 6')
    (1, u'result', u'5 + 6')
    >>> classify_input('#comment')
    (4, None, None)
    >>> classify_input('!H2O')
    (4, None, None)

    '''
    if not a or not a.strip():
        return Empty, None, None
    if tutor and not a.startswith('__'):
        output.append("<pre>\nIn: %s</pre>" % a)
    if a[0] in "!#":
        return Comment, None, None
    start = 0
    a = a.strip()
    m = match(re_identifier, a)
    if m:
        start = m.end()
    rest = a[start:].strip()
    if m and rest.startswith('='):
        return Calculation, a[:start], rest[1:]
    elif m and rest.startswith('using '):
        return ConversionUsing, a[:start], rest[len('using '):]
    elif m and rest.startswith('in '):
        return ConversionIn, a[:start], rest[len('in '):]
    else:
        if tutor:
            raise CalcError("Your tutor says: Please come up with a name for the quantity you are calculating")
        return Calculation, "result", a

Empty, Calculation, ConversionIn, ConversionUsing, Comment = range(5)



def check_name(sym, output):
    '''
    Check whether the name chosen for a quantity conforms to the rules and doesn't clash with a name already used

    :param sym: a name for a new quantity
    :param output: place to write warnings to
    :return: no return value (sym and output get changed in place)
    '''
    tokens, remainder = scanner.scan(sym)
    if len(tokens) != 1 or tokens[0][0] != "I":
        if not sym.startswith("__"):
            raise CalcError(("Please don't use %s as a name for a quantity<br><pre>%s</pre>" %
                         (sym, rules_for_symbol_name)))
    if sym in quantities.unitquant or sym in quantities.functions:
        conf = "function" if sym in quantities.functions else "unit"
        output.append(
            '<div style="color: green;">Warning: %s changed to %s_ to avoid confusion with the %s</div><br>' % (
            sym, sym, conf))
        sym = sym + "_"

rules_for_symbol_name = """Rules for names: Start with a letter, then letters or numbers or underscores.
  Examples: m0, y, s_15
Special rule #1: You can add anything in brackets, [...], or just have something in brackets
  Examples: [NaCl], [Na+], c[Na+], M[Na+]
Special rule #2: You can't use names already used for units or functions. If you do, the program will add an underscore.
  Examples: mm, s, V, and log are not allowed, and will be used as mm_, s_, V_, and log_"""


def interpret(t, symbols, output, mob=False):
    '''
    Process input mathematical express into a valid Python expression and return the result of evaluating it. This is
    a four step process. First, the string is broken into tokens by scan(), then grouped into pairs of operators and
    values by make_paired_tokens(), then turned into a valid Python expression by create_Python_expression, and finally
    evaluated with eval() to yield a quantity Q().

    :param t: the expression as string
    :param symbols: dict of known quantities
    :param output: list of output strings, to be appended to
    :param mob: device the output will be displayed on
    :return: a quantity Q()

    >>> str(interpret('3 mol/L', dict(), []))
    '3 mol/L'
    >>> str(interpret('30 s + 1 min', dict(), []))
    '(3 / 2) min'

    There are implicit parentheses around a number and the units following it.
    >>> str(interpret('4 mol/L / 2 mol/L', dict(), []))
    '2'

    Multiple fraction slashes in units are confusing, better to use parentheses to group explicitly
    >>> str(interpret('3.5 J/mol/K', dict(), []))
    '3.5 J/(K mol)'
    >>> str(interpret('3.5 J/mol K', dict(), []))
    '3.5 K J/mol'
    >>> str(interpret('3.5 J/(mol K)', dict(), []))
    '3.5 J/(K mol)'

    Non base units are retained
    >>> str(interpret('5.6 mmol', dict(), []))
    '5.6 mmol'

    Math with symbols is allowed as long symbols are defined
    >>> str(interpret('2a', dict(a=Q(2.5, units=Units(), uncert=0.1, name='a')), []))
    '5.0'

    ?>>> interpret('2a', dict(), [])
    calculator.CalcError: unknown symbol a encountered

    Here are the actual results:
    >>> interpret('3 mol/L', dict(), [])
    Q(3000.0, '', Units(m=-3,mol=1), 0.0, set([u'L', u'mol']))
    >>> interpret('30 s + 1 min', dict(), [])
    Q(90.0, '%s + %s', Units(s=1), 0.0, set([u's', u'min']), (Q(30.0, '', Units(s=1), 0.0, set([u's'])), Q(60.0, '', Units(s=1), 0.0, set([u'min']))))
    >>> interpret('4 mol/L / 2 mol/L', dict(), [])
    Q(2.0, '%s / %s', Units(), 0.0, set([u'L', u'mol']), (Q(4000.0, '', Units(m=-3,mol=1), 0.0, set([u'L', u'mol'])), Q(2000.0, '', Units(m=-3,mol=1), 0.0, set([u'L', u'mol']))))
    >>> interpret('3.5 J/mol/K', dict(), [])
    Q(3.5, '', Units(kg=1,m=2,s=-2,mol=-1,K=-1), 0.1, set([u'K', u'J', u'mol']))
    >>> interpret('3.5 J/mol K', dict(), [])
    Q(3.5, '', Units(kg=1,m=2,s=-2,mol=-1,K=1), 0.1, set([u'K', u'J', u'mol']))
    >>> interpret('3.5 J/(mol K)', dict(), [])
    Q(3.5, '', Units(kg=1,m=2,s=-2,mol=-1,K=-1), 0.1, set([u'K', u'J', u'mol']))
    >>> interpret('5.6 mmol', dict(), [])
    Q(0.0056, '', Units(mol=1), 0.00010000000000000002, set([u'mmol']))
    >>> interpret('2a', dict(a=Q(2.5, units=Units(), uncert=0.1, name='a')), [])
    Q(5.0, '%s * %s', Units(), 0.2, set([]), (Q(2.0, units=Units(), uncert=0.0), Q(2.5, 'a', Units(), 0.1)))
    '''
    paired = make_paired_tokens(scan(t))
    try:
        expression = create_Python_expression(paired, symbols)
        return eval(expression)
    except QuantError as err:
        explain_failure(t, err, output, symbols, mob)
        raise CalcError("")
    except SyntaxError as err:
        raise CalcError('%s<br><br><div style="color: red;">Mangled math: %s</div><br><br>' % (t, err))
    except OverflowError as duh:
        raise CalcError('%s<br><br><div style="color: red;">Math overflow: %s</div><br><br>' % (t, duh))


def scan(t):
    '''
    Scan text for identifers('I'), operators('O'), numbers('N') and comments('C') using the regular expression scanner.

    :param t: string of the expression to be parsed
    :return: list of tuples containing tokens ('X', text)

    >>> scan('3 mol/L')
    [(u'N', u'3'), (u'O', u''), (u'U', u'mol'), (u'O', u'/'), (u'U', u'L'), (u'O', u''), (u'Z', u'')]

    >>> scan('30 s + 1 min')
    [(u'N', u'30'), (u'O', u''), (u'U', u's'), (u'O', u'+'), (u'N', u'1'), (u'O', u''), (u'U', u'min'), (u'O', u''), (u'Z', u'')]

    >>> scan('2a')
    [(u'N', u'2'), (u'I', u'a'), (u'O', u''), (u'Z', u'')]

    >>> scan('4 7 #comment')
    [(u'N', u'4'), (u'O', u''), (u'N', u'7'), (u'O', u''), (u'C', u'#comment'), (u'Z', u'')]
    '''

    tokens, remainder = scanner.scan(t + " ")
    if remainder:
        raise CalcError("got stuck on |%s|" % remainder)
    parentheses = 0
    for ttype, ttext in tokens:
        if ttype == "O":
            parentheses += ttext.count("(") - ttext.count(")")
    if parentheses:
        raise CalcError("Parentheses don't match: %s" % repr(tokens))
    tokens.append(("Z", ""))
    for i, (ttype, ttext) in enumerate(tokens):
        if ttype == "I":
            if ttext.endswith("Ohm"):
                ttext = ttext.replace("Ohm","Ω")
            if ttext in quantities.unitquant:
                if ttext.startswith("u"):
                    ttext = "μ" + ttext[1:]
                tokens[i] = "U", ttext
            elif ttext in quantities.functions:
                tokens[i] = "F", ttext
    return tokens


def identifier(scanner, token): return "I", token.strip()
def operator(scanner, token): return "O", token.strip()
def float2(scanner, token): return "N", token.strip()
def comment(scanner, token): return "C", token.strip()

re_identifier = r"[^\[ ,()/*\^+\-=]+(\[[^]]+\])?[^\[ ,()/*\^+\-=]*|\[[^]]+\][^\[ ,()/*\^+\-=]*"

scanner = Scanner([
    (r"[#!].*", comment),
    (r"[ ,()/*^+-]+", operator),
    (r"((\d*\.\d+)|(\d+\.?))(\(\d\d?\))?([Ee][+-]?\d+)?", float2),
    (re_identifier, identifier),
], UNICODE)

"""
operator: one or more of the following: | ,()/*^+-|
float2: any floating point representation with uncertainty, e.g. 3.5(1)E-34
identifier: has to start with non-operator non-digit, may have something in brackets, may have something added
identifier: anything in brackets followed by anything
"""

def make_paired_tokens(raw_tokens):
    '''

    :param raw_tokens: A list of tokens (item ID, str) from scan()
    :return: a list of paired tokens (item ID, pre-operator, item text)

    Folds operator and identifier/number tokens into paired tokens containing item ID (N, U, I, Z), pre-operator and item text.

    This is the second step in turning the input text into a Python expression.
    It also adds implicit '*' operators and removes comments. There might be artifact '*' at the beginning and at the end.

    User input '3 mol/L' turns into '* 3 * mol / L *'
    >>> make_paired_tokens([('N', '3'), ('O', ''), ('U', 'mol'), ('O', '/'), ('U', 'L'), ('O', ''), ('Z', '')])
    [[u'N', u'*', u'3'], [u'U', u'*', u'mol'], [u'U', u'/', u'L'], [u'Z', u'*', u'']]

    User input '30 s + 1 min' turns into '* 30 * s + 1 * min *'
    >>> make_paired_tokens([('N', '30'), ('O', ''), ('U', 's'), ('O', '+'), ('N', '1'), ('O', ''), ('U', 'min'), ('O', ''), ('Z', '')])
    [[u'N', u'*', u'30'], [u'U', u'*', u's'], [u'N', u'+', u'1'], [u'U', u'*', u'min'], [u'Z', u'*', u'']]

    User input '2a' turns into '* 2 * a *'
    >>> make_paired_tokens([('N', '2'), ('I', 'a'), ('O', ''), ('Z', '')])
    [[u'N', u'*', u'2'], [u'I', u'*', u'a'], [u'Z', u'*', u'']]

    User input '4 7' turns into '* 4 * 7 *'
    >>> make_paired_tokens([('N', '4'), ('O', ''), ('N', '7'), ('O', ''), ('C', '#comment'), ('Z', '')])
    [[u'N', u'*', u'4'], [u'N', u'*', u'7'], [u'Z', u'*', u'']]

    '''
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
            if hasattr(tokenit, "__next__"):    # python 2.7 vs 3.1
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


def fixoperator(operator, tokens):
    """
    Change implicit multiplication to explicit '*' in operator unless it follows a function call.

    e.g. 'I I' -> 'I *I', 'I)(I' -> 'I)*(I', but 'F(I' is unchanged
    """
    if tokens and tokens[-1][0] == "F":
        return operator
    for i, c in enumerate(operator):
        if c == "(":
            i = i - 1
            break
    return operator[:i + 1] + "*" + operator[i + 1:]


def create_Python_expression(paired_tokens, symbols):
    '''

    :param paired_tokens: parsed and processed list of tokens from make_paired_tokens
    :param symbols: known quantities
    :return: a string containing a valid python expression yielding a quantity Q() as result

    User input '3 mol/L'
    >>>create_Python_expression([['N', '*', '3'], ['U', '*', 'mol'], ['U', '/', 'L'], ['Z', '*', '']], {})
    Q(3000.0, '', Units(m=-3,mol=1), 0.0, set(['L', 'mol']))

    User input '30 s + 1 min)
    >>>create_Python_expression([['N', '*', '30'], ['U', '*', 's'], ['N', '+', '1'], ['U', '*', 'min'], ['Z', '*', '']], {})
    Q(30.0, '', Units(s=1), 0.0, set(['s']))+Q(60.0, '', Units(s=1), 0.0, set(['min']))

    User input '4 7'
    >>>create_Python_expression([['N', '*', '4'], ['N', '*', '7'], ['Z', '*', '']], {})
    Q('4')*Q('7')

    User input '2a'
    >>>create_Python_expression([['N', '*', '2'], ['I', '*', 'a'], ['Z', '*', '']], {})
    calculator.CalcError: unknown symbol a encountered

    User input '2a'
    >>>create_Python_expression([['N', '*', '2'], ['I', '*', 'a'], ['Z', '*', '']], dict(a=Q('5')))
    Q('2')*Q(5.0, units=Units(), uncert=0.0)

    User input 'log(7)'
    >>>create_Python_expression([['F', '*', 'log'], ['N', '(', '7'], ['Z', ')*', '']], {})
    quantities.log(Q('7'))
    '''

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
                    result.append(symbols[ttext].__repr__())
                else:
                    raise CalcError("unknown symbol %s encountered" % ttext)
            continue
        # ttype in "UN", i.e. either unit or number
        quant = ["Q('%s')" % ttext]
        if ttype == "N" and "." in ttext:
            if magic(ttext if "(" not in ttext else ttext.split("(")[0]) and not "__showuncert__" in symbols:
                raise CalcError("If you always use powerful tools, your basic skills might get rusty. Do this calculation using a method other than PQCalc, please")
        if ttype == "N" and paired_tokens[0][0] != "U":
            result.append(operator)
            result.append(quant[0])
            continue
        quant_text, paired_tokens = interpret_N_U_cluster(quant, paired_tokens)
        result.append('%s%s' % (operator, quant_text))
    expression = "".join(result)[:-1]
    if expression.startswith("*"):
        return expression[1:]
    return expression


def interpret_N_U_cluster(quant, orig_paired):
    '''
    Find quantity introduced on the fly and evaluate as Q(). This is done to avoid cluttering the output with
    trivial calculations such as 2 * mol / L = 2 mol/L. This step also has consequences for order of operation, as
    quantities with units are treated as a single entity (with implied parentheses around them).

    Has to figure out where quantity ends, e.g. 8.314 J/(K mol) * 273 K or 5 mol/L / 2 mol/L
                                                ***************   +++++    *******   +++++++

    Complications arise with exponents in the units, e.g. 5 m ** 2 / J
    or parentheses, e.g. 8.314 J/(K mol) vs 8.314 J /(K 2 kg)

    :param quant: a list containing the first quantity in the cluster, e.g. "Q('2')" or "Q('kg')
    :param orig_paired: the paired list containing items on the right of the first quantity in the cluster
    :return: repr() of the quantity, and the paired tokens that have not been used

    user input: '3 mol / L'
    >>>interpret_N_U_cluster(["Q('3')"],[['U', '*', 'mol'], ['U', '/', 'L'], ['Z', '*', '']])
    ("Q(3000.0, '', Units(m=-3,mol=1), 0.0, set(['L', 'mol']))", [['Z', '*', '']])

    user input: '30 s + 1 min'
    >>>interpret_N_U_cluster(["Q('30')"],[['U', '*', 's'], ['N', '+', '1'], ['U', '*', 'min'], ['Z', '*', '']])
    ("Q(30.0, '', Units(s=1), 0.0, set(['s']))", [['N', '+', '1'], ['U', '*', 'min'], ['Z', '*', '']])
    '''

    paired = orig_paired[:]
    notyetclosed = None
    openp = 0
    for i, (ttype, op, ttext) in enumerate(paired):
        o = op.count("(")
        c = op.count(")")
        if o:
            openp += o
            if not notyetclosed:
                notyetclosed = i  # start of new parentheses that might not close
        if c:
            openp -= c
            if openp < 0:
                break
            notyetclosed = None
        if not (paired[i][0] == "U" or (paired[i][0] == "N" and "**" in paired[i][1])):
            break # we're done if we encounter anything but a unit (with the exception of an exponent on a unit)
    end = notyetclosed if notyetclosed else i  # take up to open parenthesis that wasn't closed, or to end of N-U cluster
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
    except QuantError as err:
        outp = []
        explain_failure(quantstr, err, outp, symbols, "")
        raise CalcError("<br>".join(outp[1:]))
    q.name = ""
    q.provenance = []
    return repr(q), paired[end:]

endings = {"9351", "1736", "2271", "0261", "3589", "4259", "5257", "8637", "6264", "7126"}

def magic (numberstring):
    if "e" in numberstring:
        numberstring = numberstring.split("e")[0]
    if "E" in numberstring:
        numberstring = numberstring.split("E")[0]
    if len(numberstring) < 5:
        return False
    dig = [int(i) for i in numberstring.replace(".", "")]
    quer = sum(int(n) for n in dig[:-4])
    four = "%04d" % int("".join(str((d + quer)%10) for d in dig[-4:]))
    return four in endings


def explain_failure(a, error, output, symbols, mob):
    output.append(a)
    problem = error.args[0]
    output.append('<br><br><div style="color: red;">Calculation failed: %s</div><br><br>' % problem[0])
    if problem[1]:
        show_work(problem[1], "problem", output, symbols, math=(mob != "ipud"), error=True)
    output.append("<hr>")


def register_result(result0, sym, symbols, symbollist, output):
    result0.provenance = []
    result0.name = sym[:]
    symbols[sym] = result0
    if sym.startswith("__"):
        if not result0.number:
            del symbols[sym]
            if sym in symbollist:
                symbollist.remove(sym)
        elif sym not in symbollist:
            symbollist.append(sym)
    elif sym in symbollist:
        output.append('<div style="color: green;">Warning: Updated value of %s</div><br>' % (format_identifier(sym)))
    else:
        symbollist.append(sym)
    if "__checkunits__" in symbols:
        if len(sym) == 1 or sym[1] in "_0123456789[" or sym[0] == "[":
            if sym[0] in typicalunits and result0.units != typicalunits[sym[0]][0]:
                output.append('<div style="color: green;">Warning: %s looks like a %s, but units are strange</div><br>' % (format_identifier(sym), typicalunits[sym[0]][1]))


typicalunits = dict(
    c=(Units(m=-3,mol=1),"concentration"),
    V=(Units(m=3),"volume"),
    m=(Units(kg=1),"mass"),
    P=(Units(kg=1,m=-1,s=-2),"pressure"),
    T=(Units(K=1),"absolute temperature"),
    t=(Units(s=1),"time"),
    n=(Units(mol=1),"chemical amount"))

typicalunits["["] = typicalunits["c"]


def show_work(result, sym, output, symbols, math, logput=None, error=False, addon = "", skipsteps = False):
    if sym.startswith("__"):
        return
    if math:
        if logput:
            logput.append ('''<span style="cursor:pointer" onclick="insertAtCaret('commands','%s ', 0)">''' % sym)
        output.append ('''<span style="cursor:pointer" onclick="insertAtCaret('commands','%s ', 0)">''' % sym)
        writer = quantities.latex_writer
    else:
        writer = quantities.ascii_writer
    subs = {"%s / %s":"\\dfrac{%s}{%s}",
            "%s * %s": "%s \\cdot %s",
            "%s ^ %s": "{%s}^{%s}",
            "exp(%s)": "e^{%s}",
            "log(%s)":"\\mathrm{log}(%s)",
            "ln(%s)":"\\mathrm{ln}(%s)",
            "sqrt(%s)":"\\sqrt{%s}",
            "quadn(%s":"\\mathrm{quadn}(%s",
            "quadp(%s":"\\mathrm{quadp}(%s",
            "average(%s":"\\mathrm{average(%s",
            "minimum(%s":"\\mathrm{minimum(%s",
            "alldigits(%s)":"\\mathrm{alldigits}(%s)",
            } if math else None
    d = result.setdepth()
    if math:
        template1 = "\(%s = %s%s\)<br><br>"
        template2 = "\(\\ \\ \\ =%s%s\)<br><br>"
    else:
        template1 = "%s = %s%s" if d <= 0 else "%s = \n   = %s%s"
        template2 = "   = %s%s"
    flaugs=dict(uncert=("__showuncert__" in symbols), hideunits=("__hideunits__" in symbols), hidenumbers=("__hidenumbers__" in symbols))
    task = result.steps(-1, writer, subs, flaugs)  # task
    if flaugs.get('hidenumbers'):
        task = result.steps(-1, quantities.latex_writer, subs)
    name = latex_name(sym) if math else str(sym)
    output.append(template1 % (name, task, addon))
    if logput:
        logput.append(template1 % (name, task, addon))
    if not skipsteps:
        for dd in range(1, d + 1):
            if dd == 1:
                first = result.steps(dd, writer, subs, flaugs)
                if flaugs.get('hidenumbers'):
                    first = result.steps(dd, quantities.latex_writer, subs, dict(hidenumbers=True))
                if first != task:
                    output.append(template2 % (first, addon))
            else:
                output.append(template2 % (result.steps(dd, writer, subs, flaugs), addon))  # intermediate steps
    result_str = result.steps(0, writer, subs, flaugs)  # result
    if result_str != task and not error and not (flaugs.get('hidenumbers') and d == 0):
        #print (result, task, math)
        if logput:
            logput.append(template2 % (result_str, addon))
        output.append(template2 % (result_str, addon))
    if math:
        if logput:
            logput.append ('</span>')
        output.append ('</span>')


def comments(line):
    charlist = [c for c in line]
    interpretation = []
    while charlist:
        if charlist[0] == "[":
            interpretation.append(consume_formula(charlist))
            continue
        if charlist[0] == "_":
            interp = consume_identifier(charlist)
            if interp:
                interpretation.append(interp)
                continue
        interpretation.append(consume_comment(charlist))
    return "".join(interpretation)

def convert_units(input_type, command, quant, units, output, logput, symbols, mob):
    if "__tutor__" in symbols:
        output.append('<pre>In: %s</pre>' % command)
    if input_type == ConversionUsing:
        prefu = units.split()
        for p in prefu:
            if p not in unitquant:
                raise CalcError ("PQCalc does not recognize the unit '%s', so 'using' does not work. Try 'in' instead." % p)
        try:
            q = symbols[quant.strip()] + Q(0.0)
        except KeyError:
            raise CalcError ("The quantity '%s' is not defined yet. Check for typos." % quant.strip())
        q.name = ""
        q.provenance = None
        outp = []
        show_work(q, quant, outp, symbols, mob != "ipud")
        output.extend(outp[:-1])
        symbols[quant.strip()].prefu = set(prefu)
        q = symbols[quant.strip()] + Q(0.0)
        show_work(q, quant, outp, symbols, mob != "ipud")
        output.extend(outp[-2:])
        logput = output[1:]
    else:
        tmp = interpret(units, symbols, output, mob)
        try:
            qq = symbols[quant.strip()] / tmp
        except KeyError:
            raise CalcError ("The quantity '%s' is not defined yet. Check for typos." % quant.strip())
        addon = ("\mathrm{\ %s}" % quantities.latex_name(units)) if mob != "ipud" else units
        show_work(qq, quant, output, symbols, math=(mob != "ipud"), addon=addon)


def create_comment(a, logput, output, symbols):
    if "__tutor__" in symbols:
        output.append("<pre>\nIn: %s</pre>" % a)
    if a.startswith("!"):
        output.append('<span style="color: blue;font-size: 14pt;">\\(\\ce{\\ %s}\\)<br><br></span>' % a[1:])
        logput.append('<span style="color: blue;font-size: 14pt;">\\(\\ce{\\ %s}\\)<br><br></span>' % a[1:])
    else:
        formatted = comments(a[1:])
        output.append('<div style="color: blue; font-size: 11pt;">%s</div><br>' % formatted)
        logput.append('<div style="color: blue; font-size: 11pt;">%s</div><br>' % formatted)

def consume_comment(charlist):
    cl2 = []
    while charlist and not charlist[0] in "[_":
        c = charlist.pop(0)
        if c == " ":
            cl2.append("&nbsp;")
        else:
            cl2.append(c)
    return "".join(cl2)

def consume_identifier(charlist):
    cl2 = []
    charlist.pop(0)
    while charlist:
        if charlist[0] == " ":
            charlist.pop(0)
            break
        cl2.append(charlist.pop(0))
    return "\\(%s\\)" % latex_name("".join(cl2))

def format_identifier(name):
    return consume_identifier(["_"]+[c for c in name])

def consume_formula(charlist):
    cl2 = []
    charlist.pop(0)
    while charlist:
        c = charlist.pop(0)
        if c == "]":
            break
        cl2.append(c)
    return "\\(\\ce{%s}\\)" % "".join(cl2)

def deal_with_errors(err, a, output, symbols):
    if type(err) is QuantError:
        output.append(err.args[0][0])
    elif type(err) is OverflowError:
        output.append("Overflow error, sorry: %s" % a)
    elif type(err) is CalcError:
        if "__tutor__" not in symbols:
            output.append("<pre>\n%s</pre>" % a)
        output.append(err.args[0])
        if err.args[0].startswith("If you always"):
            output = [err.args[0]]
    else:
        raise err
    return output

def wrap_up(output, symbollist, symbols):
    if output and not output[-1].endswith("<hr>"):
        output = ["<hr>"] + output
    memory = [symbols[s].__repr__() for s in symbollist]
    known = [s + " = " + symbols[s].__str__() for s in symbollist]
    oneline = ("__oneline__" in symbols)
    if "__latex__" in symbols:
        output = ["<pre>"] + output + ["</pre>"]
    return known, memory, oneline, output


task = '''for i in range(10): calc("","dd = exp(45.34) / log(6.9654) \\n yy = 87 mg/uL", False)'''

if __name__ == "__main__":
    import cProfile
    cProfile.run(task)
    mob = "ipud"
    symbols = {}
    symbollist = []
    command = raw_input("pqcalc>>>")
    while True:
        output = []
        logput = []
        try:
            input_type, name, expression = classify_input(command, symbols)
            if input_type == Calculation:
                check_name(name, output)
                quantity = interpret(expression, symbols, output, mob)
                show_work(quantity, name, output, symbols, math=(mob != 'ipud'), logput=logput)
                register_result(quantity, name, symbols, symbollist, output)
            elif input_type == Comment:
                create_comment(command, logput, output, symbols)
            elif input_type in [ConversionUsing, ConversionIn]:
                convert_units(command, name, expression, output,logput, symbols, mob)
            #else: pass because command is empty
        except Exception as err:
            output = deal_with_errors(err, command, output, symbols)
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
