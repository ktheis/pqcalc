# coding=utf-8
"""
Functions to run an interpreter for expressions containing physical quantities.

Based on the Q class in the quantities module, this provides functions to input and interpret expressions,
calculating their values and showing the steps, and finally storing the quantities so that they can be
used for further calculations.

This is an arithmetic calculator rather than an algebra system (i.e. unknowns are not allowed and will lead to
error messages). Output is either in plain text or in HTML/MathML via LaTeX.

Call hierarchy:

    calc(memory, commands, mob):
        class State(OrderedDict):
        classify_input(a, state):

        check_name(sym, state):
        interpret(t, state):
            scan(t):
                identifier(scanner, token):
                operator(scanner, token):
                float2(scanner, token):
                comment(scanner, token):
            make_paired_tokens(raw_tokens):
                fixoperator(operator, tokens):
            create_Python_expression(paired_tokens, state):
                interpret_N_U_cluster(quant, orig_paired):
                magic(numberstring):
            eval(expression)
        register_result(result0, sym, state):
        show_work(result, sym, flags, error=False, addon="", skipsteps=False):

        comments(line):
        convert_units(input_type, command, quant, units, state):
        create_comment(a, state):
            consume_comment(charlist):
            consume_identifier(charlist):
            format_identifier(name):
            consume_formula(charlist):
        change_flag(flags, name, expression):
        deal_with_errors(err, a, state):


"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import quantities
from quantities import Q, Units, QuantError, latex_name, unitquant
from re import Scanner, UNICODE, match
from form import exdict
from fractions import Fraction

class CalcError(ArithmeticError): pass


def calc(memory, commands, mob):
    '''

    :param memory: quantities already defined, given as repr()s line by line in a string
    :param commands: string of user input specifying math operations to define new quantities
    :param mob: device the output will be sent to (determines format)
    :return: everything needed to show the result in a browser and keep state for the next calculation
    '''
    state = State(memory, mob)
    command_list = commands.replace('\r', '').split("\n")
    try:
        for command in command_list:
            #print ("%s" % command)
            input_type, name, expression = classify_input(command, state)
            if input_type == Calculation:
                name = check_name(name, state)
                quantity = interpret(expression, state)
                state.printwork(show_work(quantity, name, state.flags))
                register_result(quantity, name, state)
            elif input_type == Comment:
                create_comment(command, state)
            elif input_type in [ConversionUsing, ConversionIn]:
                convert_units(input_type, command, name, expression, state)
            elif input_type == Flags:
                change_flag(state.flags, name, expression)
                # else: pass because command is empty
            state.log_input(command)
    except (CalcError, OverflowError, QuantError) as err:
        deal_with_errors(err, command, state)
    return state.export()
    # return output, logput, memory, known, mob, oneline, linespace


from collections import OrderedDict


class State(OrderedDict):
    def __init__(self, memory=None, mob=None):
        """
        Loads quantities from previous calculations by evaluating their repr()s

        :param memory: String of repr()s
        :stores OrderedDict of symbols, output, logput
        """
        OrderedDict.__init__(self)
        self.flags = set()
        self.output = []
        self.logput = []
        self.good_input = []
        self.mob = mob
        if mob == 'ipud':
            self.flags.add('plain math')
        if memory:
            old = memory.replace('\r', '').split('\n')
            for a in old:
                if a.startswith('__'):
                    self.flags.add(a)
                else:
                    sym = a.split("'")[1]
                    self[sym] = eval(a)

    def printit(self, str):
        self.output.append(str)

    def logit(self, str):
        self.logput.append(str)

    def printnlog(self, str):
        self.printit(str)
        self.logput.append(str)

    def printwork(self, outlog):
        self.output.extend(outlog[0])
        self.logput.extend(outlog[1])

    def log_input(self, inp):
        self.good_input.append(inp)

    def export(self):
        if self.output and not self.output[-1].endswith("<hr>"):
            self.output = ["<hr>"] + self.output
        memory = [self[s].__repr__() for s in self]
        flags = [f for f in self.flags]
        memory.extend(flags)
        known = [s + " = " + self[s].__str__() for s in self]
        oneline = ("__oneline__" in self.flags)
        if "__latex__" in self.flags:
            self.output = ["<pre>"] + self.output + ["</pre>"]
        input_log = '\n'.join(self.good_input)
        linespace = '40%' if '__scrunch__' in self.flags else '100%'
        return self.output, self.logput, memory, known, oneline, input_log, linespace


def classify_input(a, state):
    '''
    :param a: the user input string containing a calculation, unit conversion or comment
    :param state: contains known quantities as ordered dict, along with flags and output
    :return: a tuple (type of input, symbol name, expression/units)

    Empty, Calculation, ConversionIn, ConversionUsing, Comment, Flags = range(6)

    >>> classify_input(' ', State())
    (0, None, None)
    >>> classify_input('K[A<=>B] = 13', State())
    (1, u'K[A<=>B]', u' 13')
    >>> classify_input('R using J', State())
    (3, u'R', u'J')
    >>> classify_input('K[A<=>B] in mM', State())
    (2, u'K[A<=>B]', u'mM')
    >>> classify_input('5 + 6', State())
    (1, u'result', u'5 + 6')
    >>> classify_input('#comment', State())
    (4, None, None)
    >>> classify_input('!H2O', State())
    (4, None, None)

    '''
    if not a or not a.strip():
        return Empty, None, None
    if '__tutor__' in state.flags and not a.startswith('__'):
        state.printit("<pre><b>>>>> %s</b></pre>" % a)
    elif not a.startswith('__'):
        state.printit("<br>")
    state.logit("<br>")

    if a[0] in "!#@":
        return Comment, None, None
    a = a.strip()
    if a.startswith('__'):
        name, onoff = a.split('=', 1)
        return Flags, name.strip(), onoff
    start = 0
    m = match(re_identifier, a)
    if m:
        start = m.end()
    rest = a[start:].strip()
    if m and rest.startswith('='):
        return Calculation, a[:start], rest[1:]
    elif m and rest.startswith('using'):
        return ConversionUsing, a[:start], rest[len('using'):].strip()
    elif m and rest.startswith('in'):
        return ConversionIn, a[:start], rest[len('in'):].strip()
    else:
        if '__tutor__' in state.flags:
            raise CalcError("Your tutor says: Please come up with a name for the quantity you are calculating")
        return Calculation, "result", a


Empty, Calculation, ConversionIn, ConversionUsing, Comment, Flags = range(6)


def check_name(sym, state):
    '''
    Check whether the name chosen for a quantity conforms to the rules and doesn't clash with a name already used

    :param sym: a name for a new quantity
    :param state: contains known quantities as ordered dict, along with flags and output
    :return: no return value (sym and output get changed in place)
    '''
    tokens, remainder = scanner.scan(sym)
    if len(tokens) != 1 or tokens[0][0] != "I":
        raise CalcError(("Please don't use %s as a name for a quantity<br><pre>%s</pre>" %
                         (sym, rules_for_symbol_name)))
    if sym in quantities.unitquant or sym in quantities.functions:
        conf = "function" if sym in quantities.functions else "unit"
        state.printit(
            '<div style="color: green;">Warning: %s changed to %s_ to avoid confusion with the %s</div><br>' % (
                sym, sym, conf))
        sym = sym + "_"
    return sym


rules_for_symbol_name = """Rules for names: Start with a letter, then letters or numbers or underscores.
  Examples: m0, y, s_15
Special rule #1: You can add anything in brackets, [...], or just have something in brackets
  Examples: [NaCl], [Na+], c[Na+], M[Na+]
Special rule #2: You can't use names already used for units or functions. If you do, the program will add an underscore.
  Examples: mm, s, V, and log are not allowed, and will be used as mm_, s_, V_, and log_"""


def interpret(t, state):
    '''
    Process input mathematical expression into a valid Python expression and return the result of evaluating it. This is
    a four step process. First, the string is broken into tokens by scan(), then grouped into pairs of operators and
    values by make_paired_tokens(), then turned into a valid Python expression by create_Python_expression, and finally
    evaluated with eval() to yield a quantity Q().

    :param t: the expression as string
    :param state: contains known quantities as ordered dict, along with flags and output
    :return: a quantity Q()

    >>> str(interpret('3 mol/L', State()))
    '3 mol/L'
    >>> str(interpret('30 s + 1 min', State()))
    '(3 / 2) min'

    There are implicit parentheses around a number and the units following it.
    >>> str(interpret('4 mol/L / 2 mol/L', State()))
    '2'

    Multiple fraction slashes in units are confusing, better to use parentheses to group explicitly
    >>> str(interpret('3.5 J/mol/K', State()))
    '3.5 J/(K mol)'
    >>> str(interpret('3.5 J/mol K', State()))
    '3.5 K J/mol'
    >>> str(interpret('3.5 J/(mol K)', State()))
    '3.5 J/(K mol)'

    Non base units are retained
    >>> str(interpret('5.6 mmol', State()))
    '5.6 mmol'

    Math with symbols is allowed as long symbols are defined
    >>> str(interpret('2a', State("Q(2.5, units=Units(), uncert=0.1, name='a')")))
    '5.0'

    ?>>> interpret('2a', State())
    calculator.CalcError: unknown symbol a encountered

    Here are the actual results:
    >>> interpret('3 mol/L', State())
    Q(3000.0, '', Units(m=-3,mol=1), 0.0, set([u'L', u'mol']))
    >>> interpret('30 s + 1 min', State())
    Q(90.0, '%s + %s', Units(s=1), 0.0, set([u's', u'min']), (Q(30.0, '', Units(s=1), 0.0, set([u's'])), Q(60.0, '', Units(s=1), 0.0, set([u'min']))))
    >>> interpret('4 mol/L / 2 mol/L', State())
    Q(2.0, '%s / %s', Units(), 0.0, set([u'L', u'mol']), (Q(4000.0, '', Units(m=-3,mol=1), 0.0, set([u'L', u'mol'])), Q(2000.0, '', Units(m=-3,mol=1), 0.0, set([u'L', u'mol']))))
    >>> interpret('3.5 J/mol/K', State())
    Q(3.5, '', Units(kg=1,m=2,s=-2,mol=-1,K=-1), 0.1, set([u'K', u'J', u'mol']))
    >>> interpret('3.5 J/mol K', State())
    Q(3.5, '', Units(kg=1,m=2,s=-2,mol=-1,K=1), 0.1, set([u'K', u'J', u'mol']))
    >>> interpret('3.5 J/(mol K)', State())
    Q(3.5, '', Units(kg=1,m=2,s=-2,mol=-1,K=-1), 0.1, set([u'K', u'J', u'mol']))
    >>> interpret('5.6 mmol', State())
    Q(0.0056, '', Units(mol=1), 0.00010000000000000002, set([u'mmol']))
    >>> interpret('2a', State("Q(2.5, units=Units(), uncert=0.1, name='a')"))
    Q(5.0, '%s * %s', Units(), 0.2, set([]), (Q(2.0, units=Units(), uncert=0.0), Q(2.5, 'a', Units(), 0.1)))
    '''

    paired = make_paired_tokens(scan(t))
    try:
        expression = create_Python_expression(paired, state)
        q = eval(expression)
################ EVAL EVAl EVAL #######################
        if type(q) != Q:
            print(expression)
            print(q)
            raise CalcError('<div style="color: red;">misused comma? %s</div><br>' % expression)
        return q
    except SyntaxError as err:
        raise CalcError('<br>%s<br><br><div style="color: red;">Mangled math: %s</div><br>' % (t, err))
    except OverflowError as duh:
        raise CalcError('<br>%s<br><br><div style="color: red;">Math overflow: %s</div><br>' % (t, duh))
    except AttributeError as duh:
        raise CalcError('<br>%s<br><br><div style="color: red;">Comma again?: %s</div><br>' % (t, duh))


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
    flatop = (c for ttyp, ttex in tokens if ttyp == 'O' for c in ttex)
    paren = 0
    for c in flatop:
        if c == '(':
            paren += 1
        elif c == ')':
            if not paren:
                raise CalcError("Closing parenthesis ')' is missing a matching opening one '(' to the left of it")
            paren -= 1
    if paren:
        raise CalcError("Parentheses don't match: need %d more ')'" % paren)
    tokens.append(("Z", ""))
    for i, (ttype, ttext) in enumerate(tokens):
        if ttype == "I":
            if ttext.endswith("Ohm"):
                ttext = ttext.replace("Ohm", "Ω")
            if ttext in quantities.unitquant:
                if ttext.startswith("u"):
                    ttext = "μ" + ttext[1:]
                tokens[i] = "U", ttext
            elif ttext in quantities.functions:
                tokens[i] = "F", ttext
    infunc = []
    paren = 0
    for i, (ttype, ttext) in enumerate(tokens):
        if ttype == 'F':
            infunc.append(paren)
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
            if hasattr(tokenit, "__next__"):  # python 2.7 vs 3.1
                ttype, ttext = tokenit.__next__()
            else:
                ttype, ttext = tokenit.next()
        else:
            operator = "*"
        if ttype == "C":
            tokens.append(["Z", operator, ""])
            break
        tokens.append([ttype, operator.replace("^", "**"), ttext])
    return fixfractions(tokens)

def fixfractions(tokens):
    newtokens = []
    while tokens:
        # ['N','...(','integer'],['N','/','integer'],['...',')','...]
        if (len(tokens) > 2 and tokens[0][0] == 'N' and tokens[1][0] == 'N' and tokens[0][1].endswith('(') and tokens[2][1].startswith(')') and tokens[1][1] == '/' and
            '.' not in tokens[0][2] and '.' not in tokens[1][2] and int(tokens[1][2]) != 0):
                fractoken = ['N', tokens[0][1], '%s / %s' % (tokens[0][2], tokens[1][2])]
                newtokens.append(fractoken)
                tokens.pop(0)
                tokens.pop(0)
        else:
            newtokens.append(tokens.pop(0))
    return newtokens


def fixoperator(operator, tokens):
    """
    Change implicit multiplication to explicit '*' in operator unless it follows a function call.

    >>> fixoperator(' ', ['I'])
    u' *'
    >>> fixoperator(' )  (   ', ['I'])
    u' )  *(   '
    >>> fixoperator(') ', ['I'])
    u') *'
    >>> fixoperator('(', ['I'])
    u'*('
    >>> fixoperator('(', ['F'])
    u'('

    no '*' inserted prior to function call
    """

    if tokens and tokens[-1][0] == "F":
        return operator
    for i, c in enumerate(operator):
        if c == "(":
            i = i - 1
            break
    return operator[:i + 1] + "*" + operator[i + 1:]


def create_Python_expression(paired_tokens, state):
    '''

    :param paired_tokens: parsed and processed list of tokens from make_paired_tokens
    :param state: contains known quantities as ordered dict, along with flags and output
    :return: a string containing a valid python expression yielding a quantity Q() as result

    User input '3 mol/L'
    >>> create_Python_expression([['N', '*', '3'], ['U', '*', 'mol'], ['U', '/', 'L'], ['Z', '*', '']], {})
    u"Q(3000.0, '', Units(m=-3,mol=1), 0.0, set(['L', 'mol']))"

    User input '30 s + 1 min)
    >>> create_Python_expression([['N', '*', '30'], ['U', '*', 's'], ['N', '+', '1'], ['U', '*', 'min'], ['Z', '*', '']], {})
    u"Q(30.0, '', Units(s=1), 0.0, set(['s']))+Q(60.0, '', Units(s=1), 0.0, set(['min']))"

    User input '4 7'
    >>> create_Python_expression([['N', '*', '4'], ['N', '*', '7'], ['Z', '*', '']], {})
    u"Q('4')*Q('7')"

    User input '2a'
    >>> create_Python_expression([['N', '*', '2'], ['I', '*', 'a'], ['Z', '*', '']], {})
    calculator.CalcError: unknown symbol a encountered

    User input '2a'
    >>> create_Python_expression([['N', '*', '2'], ['I', '*', 'a'], ['Z', '*', '']], State("Q(number=5.0, name='a')"))
    u"Q('2')*Q(5.0, 'a', Units(), 0.0)"

    User input 'log(7)'
    >>> create_Python_expression([['F', '*', 'log'], ['N', '(', '7'], ['Z', ')*', '']], {})
    u"quantities.log(Q('7'))"

    '''

    result = []
    complaint = '__tutor__' in state.flags and any(x[0]=='I' for x in paired_tokens) and any(x[0]=='U' for x in paired_tokens)
    while True:  # consume "Z", "I", "F", "U", "N" in paired_tokens
        ttype, operator, ttext = paired_tokens.pop(0)
        if ttype in "ZIF":
            result.append(operator)
            if ttype == "Z":
                break
            if ttype == "F":
                result.append("quantities." + ttext)
            else:  # ttype == "I"
                if ttext in state:
                    result.append(state[ttext].__repr__())
                else:
                    raise CalcError("unknown symbol |%s| encountered" % ttext)
            continue
        # ttype in "UN", i.e. either unit or number
        quant = ["Q('%s')" % ttext]
        if ttype == "N" and "." in ttext:
            if magic(ttext if "(" not in ttext else ttext.split("(")[0]) and not "__showuncert__" in state.flags:
                raise CalcError(
                    "If you always use powerful tools, your basic skills might get rusty. Do this calculation using a method other than PQCalc, please")
        if ttype == "N" and paired_tokens[0][0] != "U":
            result.append(operator)
            result.append(quant[0])
            continue
        quant_text, paired_tokens = interpret_N_U_cluster(quant, paired_tokens, complaint)
        result.append('%s%s' % (operator, quant_text))
    expression = "".join(result)[:-1]
    if expression.startswith("*"):
        return expression[1:]
    return expression


def interpret_N_U_cluster(quant, orig_paired, complaint):
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
    complaint = complaint and any('U' in x for x in orig_paired)
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
            break  # we're done if we encounter anything but a unit (with the exception of an exponent on a unit)
    end = notyetclosed if notyetclosed else i  # take up to open parenthesis that wasn't closed, or to end of N-U cluster
    for j in range(end):
        quant.append(paired[j][1] + "Q('%s')" % paired[j][2])
    quantstr = "".join(quant)
    openparentheses = quantstr.count("(") - quantstr.count(")")
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
    try:
        q = eval(quantstr)
    except SyntaxError:
        raise CalcError('<br>%s<br><br><div style="color: red;">Mangled math</div><br>' % quantstr)
    except OverflowError as duh:
        raise CalcError('<br>%s<br><br><div style="color: red;">Math overflow: %s</div><br>' % (quantstr, duh))
    except AttributeError as duh:
        raise CalcError('<br>%s<br><br><div style="color: red;">Bad comma?: %s</div><br>' % (quantstr, duh))
    if complaint:
        raise CalcError('<br>%s<br><br><div style="color: red;">Please give all quantities a name before using them in a calculation</div><br>' % q)

    q.name = ""
    q.provenance = []
    return repr(q), paired[end:]


endings = {"9351", "1736", "2271", "0261", "3589", "4259", "5257", "8637", "6264", "7126"}


def magic(numberstring):
    if "e" in numberstring:
        numberstring = numberstring.split("e")[0]
    if "E" in numberstring:
        numberstring = numberstring.split("E")[0]
    if len(numberstring) < 5:
        return False
    dig = [int(i) for i in numberstring.replace(".", "")]
    quer = sum(int(n) for n in dig[:-4])
    four = "%04d" % int("".join(str((d + quer) % 10) for d in dig[-4:]))
    return four in endings


def register_result(result0, sym, state):
    """
    Enters the quantity that was just calculated into the database

    :param result0: quantity Q()
    :param sym: name of the quantity
    :param state: contains known quantities as ordered dict, along with flags and output
    """
    result0.provenance = []
    result0.name = sym[:]
    if sym in state:
        state.printit('<div style="color: green;">Warning: Updated value of %s</div><br>' % (format_identifier(sym)))
    state[sym] = result0
    if '__fracunits__' not in state.flags:
        for u in result0.units:
            if u.denominator != 1:#oddly, ints have and floats don't
                state.printit('<div style="color: green;">Warning: Units have non-integer exponents %s</div><br>' % u)
    if "__checkunits__" in state.flags:
        if len(sym) == 1 or sym[1] in "_0123456789[" or sym[0] == "[":
            if sym[0] in typicalunits and result0.units != typicalunits[sym[0]][0]:
                state.printit(
                    '<div style="color: green;">Warning: %s looks like a %s, but units are strange</div><br>' % (
                        format_identifier(sym), typicalunits[sym[0]][1]))


typicalunits = dict(
    c=(Units(m=-3, mol=1), "concentration"),
    V=(Units(m=3), "volume"),
    m=(Units(kg=1), "mass"),
    P=(Units(kg=1, m=-1, s=-2), "pressure"),
    T=(Units(K=1), "absolute temperature"),
    t=(Units(s=1), "time"),
    n=(Units(mol=1), "chemical amount"))

typicalunits["["] = typicalunits["c"]


def show_work(result, sym, flags, error=False, addon="", skipsteps=False):
    """
    Shows the steps in getting from formula to calculated value. This function is called not only by calc(),
    but also by convert_units() and deal_with_errors() to show steps in calculations.

    :param result: value and provenance of the quantity Q()
    :param sym: name of the quantity
    :param flags: Switches that determine how much detail is shown
    :param error: True if used to show an error in a step of a calculation
    :param addon: Used when called from convert_units(ConversionIn)
    :param skipsteps: True when intermediate steps are to be skipped
    :return: tuple containing detailed output, brief output
    """
    output = []
    logput = []
    math = not 'plain math' in flags
    if math:
        writer = quantities.latex_writer
        if not "__latex__" in flags:
            logput.append('''<span style="cursor:pointer" onclick="insertAtCaret('commands','%s ', 0)">''' % sym)
            output.append('''<span style="cursor:pointer" onclick="insertAtCaret('commands','%s ', 0)">''' % sym)
    else:
        writer = quantities.ascii_writer
    subs = {"%s / %s": "\\dfrac{%s}{%s}",
            "%s * %s": "%s \\cdot %s",
            "%s ^ %s": "{%s}^{%s}",
            "exp(%s)": "e^{%s}",
            "log(%s)": "\\mathrm{log}(%s)",
            "ln(%s)": "\\mathrm{ln}(%s)",
            "sin(%s)": "\\mathrm{sin}(%s)",
            "cos(%s)": "\\mathrm{cos}(%s)",
            "tan(%s)": "\\mathrm{tan}(%s)",
            "sqrt(%s)": "\\sqrt{%s}",
            "quadn(%s": "\\mathrm{quadn}(%s",
            "quadp(%s": "\\mathrm{quadp}(%s",
            "average(%s": "\\mathrm{average(%s",
            "minimum(%s": "\\mathrm{minimum(%s",
            "maximum(%s": "\\mathrm{maximum(%s",
            "absolute(%s": "\\mathrm{absolute(%s",
            "moredigits(%s)": "\\mathrm{moredigits}(%s)",
            "uncertainty(%s)": "\\mathrm{uncertainty}(%s)",
    } if math else None
    d = result.setdepth()
    if math:
        template1 = "\(%s = %s%s\)<br>"
        template2 = "<br>\(\\ \\ \\ =%s%s\)<br>"
    else:
        template1 = "%s = %s%s" if d <= 0 else "%s = \n   = %s%s"
        template2 = "   = %s%s"
    flaugs = dict(uncert=("__showuncert__" in flags), hideunits=("__hideunits__" in flags),
                  hidenumbers=("__hidenumbers__" in flags))
    task = result.steps(-1, writer, subs, flaugs)  # task
    if flaugs['hidenumbers']:
        task = result.steps(-1, quantities.latex_writer, subs)
    name = latex_name(sym) if math else sym
    output.append(template1 % (name, task, addon))
    logput.append(template1 % (name, task, addon))
    if not skipsteps:
        for dd in range(1, d + 1):
            if dd == 1:
                first = result.steps(dd, writer, subs, flaugs)
                if flaugs['hidenumbers']:
                    first = result.steps(dd, quantities.latex_writer, subs, dict(hidenumbers=True))
                if first != task:
                    output.append(template2 % (first, addon))
            else:
                output.append(template2 % (result.steps(dd, writer, subs, flaugs), addon))  # intermediate steps
    result_str = result.steps(0, writer, subs, flaugs)  # result
    if result_str != task and not error and not (flaugs['hidenumbers'] and d == 0):
        logput.append(template2 % (result_str, addon))
        output.append(template2 % (result_str, addon))
    if math and not '__latex__' in flags:
        logput.append('<br></span>')
        output.append('<br></span>')
    return output, logput


def convert_units(input_type, command, quant, units, state):
    """
    Shows the quantity in different units, either once only ('in') or from now on ('using')

    :param input_type: Whether conversion is with "using" or "in"
    :param command: user input
    :param quant: Q() to be converted
    :param units: requested units
    :param state: contains known quantities as ordered dict, along with flags and output
    :raise CalcError: if requested units are unknown
    """
    if input_type == ConversionUsing:
        prefu = units.split()
        for p in prefu:
            if p not in unitquant:
                raise CalcError(
                    "PQCalc does not recognize the unit '%s', so 'using' does not work. Try 'in' instead." % p)
        try:
            q = state[quant.strip()] + Q(0.0)
        except KeyError:
            raise CalcError("The quantity '%s' is not defined yet. Check for typos." % quant.strip())
        q.name = ""
        q.provenance = None
        outp, _ = show_work(q, quant, state.flags)
        output = (outp[:-1])
        state[quant.strip()].prefu = set(prefu)
        q = state[quant.strip()] + Q(0.0)
        outp, _ = show_work(q, quant, state.flags)
        output.extend(outp[-2 if not 'plain math' in state.flags else -1:])
    else:
        tmp = interpret(units, state)
        try:
            qq = state[quant.strip()] / tmp
        except KeyError:
            raise CalcError("The quantity '%s' is not defined yet. Check for typos." % quant.strip())
        addon = ("\mathrm{\ %s}" % quantities.latex_name(units)) if state.mob != "ipud" else units
        output, _ = show_work(qq, quant, state.flags, addon=addon)
    state.printit('\n'.join(output))


def create_comment(a, state):
    """

    :param a: user input
    :param state: contains known quantities as ordered dict, along with flags and output
    :return: none (comment is written to state)
    """
    if 'plain math' in state.flags:
        state.printnlog(a)
        return
    if a.startswith("!"):
        state.printnlog('<br><span style="color: maroon;font-size: 14pt;">\\(\\ce{\\ %s}\\)<br></span>' % a[1:])
    else:
        formatted = markup_comments(a[1:])
        state.printnlog('<div style="color: blue; font-size: 11pt;">%s</div>' % formatted)


def markup_comments(line):
    """

    :param line: String containing the comment
    :return: String with variables and chemistry marked-up in LateX
    """
    charlist = [c for c in line]
    interpretation = []
    while charlist:
        if charlist[0] == "[":
            interpretation.append(consume_formula(charlist))
            continue
        if charlist[0] == "{" and not interpretation:
            interpretation.append(consume_image(charlist))
            continue
        if charlist[0] == "_":
            interp = consume_identifier(charlist)
            if interp:
                interpretation.append(interp)
                continue
        interpretation.append(consume_comment(charlist))
    return "".join(interpretation)


def consume_image(charlist):
    cl2 = []
    charlist.pop(0)
    while charlist:
        c = charlist.pop(0)
        if c == "}":
            break
        cl2.append(c)
    return '<img src=%s>' % "".join(cl2)


def consume_comment(charlist):
    cl2 = []
    while charlist and not charlist[0] in "[_":
        c = charlist.pop(0)
        if c == " " and cl2 and cl2[-1] == ' ':
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
    return consume_identifier(["_"] + [c for c in name])


def consume_formula(charlist):
    cl2 = []
    charlist.pop(0)
    while charlist:
        c = charlist.pop(0)
        if c == "]":
            break
        cl2.append(c)
    return "\\(\\ce{%s}\\)" % "".join(cl2)


def change_flag(flags, name, expression):
    if expression.strip() != '0':
        flags.add(name)
    else:
        flags.discard(name)


def deal_with_errors(err, a, state):
    """

    :param err: the exception that was raised
    :param a: the imput that led to the exception
    :param state: contains known quantities as ordered dict, along with flags and output
    :raise err: For exceptions not raised explicitly "unexpected errors"
    """
    if type(err) is QuantError:
        # QuantError((complaint, Q(0, name, provenance=provenance)))
        problem = err.args[0]
        state.printit('<div style="color: red;"><pre>' + a + "</pre>")
        state.printit('Calculation failed: %s<br><br>' % problem[0])
        if problem[1]:
            output, _ = show_work(problem[1], "problem", state.flags, error=True)
            state.printit('\n'.join(output))
        state.printit("</div>")
    elif type(err) is OverflowError:
        state.printit("Overflow error, sorry: %s" % a)
    elif type(err) is CalcError:
        if "__tutor__" not in state.flags:
            state.printit("<pre>\n%s</pre>" % a)
        state.printit(err.args[0])
    else:
        raise err


task = '''for i in range(100000): calc("","dd = exp(45.34) / log(6.9654) \\n yy = 87 mg/uL", False)'''


def test_examples():
    for ex in exdict:
        print('########################################################################')
        print('#          %-60s#' % ex)
        print('########################################################################')
        commands = exdict[ex]
        print (commands)
    # return output, logput, memory, known, mob, oneline, linespace

        output, _, memory, _, _, _, _ = calc("", commands, 'ipud')
        for line in output[1:]:
            print(line)

def profile_program():
    import cProfile

    memory = ""
    cProfile.run(task)


if __name__ == "__main__":
    profile_program()
    calc('', 'a = 10^10^10', 'ipud')
    test_examples()
    commands = raw_input(">>> ")
    memory = ""
    while True:
        output, _, memory, _, _, _, _ = calc(memory, commands, 'ipud')
        for line in output[1:]:
            print(line)
        memory = '\n'.join(memory)
        commands = raw_input(">>> ")

"""
Test input that should fail gracefully:

sadf = 56 * (67 )()

asdf = 5 + t + &#@

gg = sin(45)

vv = 10^10^10

omg = 1 / 10^-1000
"""
