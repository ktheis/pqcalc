# -*- coding: latin-1 -*-
"""

Classes and functions to do arithmetic with physical quantities.

At the core of this module is the class Q, which defines a number that has units, a name, and a crude indication
of uncertainty (significant figures).

The way significant figures are treated here is just for number formatting - all calculations are done to the
maximum precision of python floats (~57 bits, equivalent to ~17 decimal digits). There is a special function
"alldigits" to retrieve the full internal representation of the number.

The online calculator hosted at http:\\\\ktheis.pythonanywhere.com uses this code.

Author: Karsten Theis (ktheis@westfield.ma.edu)
"""
from __future__ import division

from math import log10 as math_log10
from math import log as math_log
from math import exp as math_exp
from math import floor

SIunit_symbols = ["A", "kg", "m", "s", "mol", "K", "Cd", "$"]


class Units(tuple):
    """A class to describe the dimensions of a quantity in terms of base units.

    The base units are the SI units plus the dollar. Units are expressed as tuple containing
    the exponents of the units.

    Example:
      cubic meters is Units(m=3)
      kilogram per cubic meters is Units(m=-3, kg=1)
    """

    def __new__(cls, A=0, kg=0, m=0, s=0, mol=0, K=0, Cd=0, dollar=0):
        return tuple.__new__(cls, (A, kg, m, s, mol, K, Cd, dollar))

    def __repr__(self):
        symbols = ["A", "kg", "m", "s", "mol", "K", "Cd", "dollar"]
        return "Units(" + ",".join("%s=%d" % x for x in zip(symbols, self) if x[1]) + ")"


unity = Units()


class QuantError(ArithmeticError):
    """An exception used by the class Q."""
    pass


def raise_QuantError(complaint, name, provenance):
    raise QuantError((complaint, Q(0, name, provenance=provenance)))


class Q(object):
    """A class for arithmetic with physical quantities having units and significant figures

    The class defines the arithmetic operators +, -, *, /, ** for Q. For binary operations, both
    operands must be instances of Q. Other methods serve to show the result and how it was
    calculated.

    Attributes:
      number(float): The number part of the quantity
      units(Units): The base units of the quantity, see Units class
      name(str): The name of the quantity
      sigfig(int) The number of significant figures. 12 refers to an exact integer
      prefu(list(str)): the preferred units for the quantity, given as str in unitquant
      provenance: quantities from which it was derived
      
    Examples:
      Q(2) is the dimensionless number 2
      Q("kg") is the quantity 1 kg
      Q(3.0, "", Units(kg=1), 2, [], None) is 3.0 kg

    """

    def __init__(self, number=0.0, name="", units=unity, sig=12, prefu=[], provenance=None):
        """

        """
        try:
            number + 1.0
            self.number = float(number)
            self.units = Units(*units)
            self.name = name[:]
            self.prefu = set(prefu)
            self.sigfig = sig
            self.provenance = provenance
        except TypeError:
            if number in unitquant:
                q = unitquant[number]
            else:
                q = number2quantity(number)
            self.__dict__ = q.__dict__

    def __repr__(self):
        if self.name in unitquant and self.__dict__ == unitquant[self.name].__dict__:
            return "Q('%s')" % self.name
        self.rnumber = repr(self.number)
        if self.provenance:
            return "Q(%(rnumber)s, '%(name)s', %(units)s, %(sigfig)d, %(prefu)s, %(provenance)s)" % self.__dict__
        if self.prefu:
            return "Q(%(rnumber)s, '%(name)s', %(units)s, %(sigfig)d, %(prefu)s)" % self.__dict__
        if self.name:
            return "Q(%(rnumber)s, '%(name)s', %(units)s, %(sigfig)d)" % self.__dict__
        return "Q(%(rnumber)s, units=%(units)s, sig=%(sigfig)d)" % self.__dict__

    def __str__(self):
        number, units = unit_string(self.number, self.units, self.prefu)
        nstr = numberstring(number, self.sigfig)
        if units.startswith("$"):
            return "$%s%s" % (nstr, units[1:])
        return "%s%s" % (nstr, units)

    def math_value(self):
        number, units = unit_string(self.number, self.units, self.prefu, math=True)
        nstr = numberstring(number, self.sigfig, math=True)
        if units.startswith("$"):
            return "$%s %s" % (nstr, units[1:])
        return "%s %s" % (nstr, units)

    def setdepth(self):
        if not hasattr(self, "depth"):
            if not self.provenance:
                self.depth = 0
            else:
                self.depth = 1 + max(child.setdepth() for child in self.provenance)
        return self.depth

    def intermediate_steps(self, level, math=False):
        if not level or level > self.depth:
            if math:
                return self.math_value()
            return str(self)
        name = self.name[:]
        children = []
        for index, q in enumerate(self.provenance):
            child = q.intermediate_steps(level, math=math)
            if q.provenance and level <= q.depth:
                if opprio[name] > opprio[q.name] and opprio[name] and opprio[q.name]:
                    child = "(" + child + ")"
            if "/" in name:
                ''' and ("/" in child or (index==1 and q.units != unity) or (
                                       math and (q.units != unity or "*" in child) and index==0)):'''
                child = "(" + child + ")"
            elif name.startswith("-") and child.startswith("-"):
                child = "(" + child + ")"
            if "^" in name and q.units != unity:
                child = "(" + child + ")"
            children.append(child)
        if "/" in name and math:
            if morethantwodiv(children[0]):
                children[0] = "(" + children[0] + ")"
        return name % tuple(children)

    def task(self, math=False):
        name = self.name[:]
        if not self.provenance:
            if not name:
                if math:
                    return self.math_value()
                return str(self)
            return math_name(name)
        children = []
        for index, q in enumerate(self.provenance):
            child = q.task(math=math)
            if q.provenance:  # child has children
                if opprio[name] > opprio[q.name] and opprio[name] and opprio[q.name]:
                    child = "(" + child + ")"
            if "/" in name and ("/" in child or (math and (q.units != unity or "*" in child) and index == 0)):
                child = "(" + child + ")"
            elif "^" in name and q.units != unity:
                child = "(" + child + ")"
            children.append(child)
        if "/" in name and math:
            if morethantwodiv(children[0]):
                children[0] = "(" + children[0] + ")"
        return self.name % tuple(children)

    def __mul__(self, other):
        units = tuple([x[0] + x[1] for x in zip(self.units, other.units)])
        number = self.number * other.number
        sigfig = min(self.sigfig, other.sigfig) + 1
        if other.name in unitquant and other.__dict__ == unitquant[other.name].__dict__:
            sigfig = self.sigfig
        name = "%s * %s"
        prefu, provenance = inherit_binary(self, other)
        return Q(number, name, units, sigfig, prefu, provenance)

    def __truediv__(self, other):
        units = tuple([x[0] - x[1] for x in zip(self.units, other.units)])
        try:
            number = self.number / other.number
        except ZeroDivisionError:
            raise_QuantError("denominator is zero", "%s / %s", (self, other))
        name = "%s / %s"
        sigfig = min(self.sigfig, other.sigfig) + 1
        if other.name in unitquant and other.__dict__ == unitquant[other.name].__dict__:
            sigfig = self.sigfig
        prefu, provenance = inherit_binary(self, other)
        return Q(number, name, units, sigfig, prefu, provenance)

    def __neg__(self):
        return Q(-self.number, "-%s", self.units, self.sigfig, self.prefu, (self,))

    def __pos__(self):
        return self

    def __add__(self, other):
        if self.units != other.units and self.number and other.number:
            raise_QuantError("Units in sum not compatible", "%s + %s", (self, other))
        number = self.number + other.number
        name = "%s + %s"
        prefu, provenance = inherit_binary(self, other)
        units, sigfig = sigfig_sum(number, self, other)
        return Q(number, name, units, sigfig, prefu, provenance)

    def __sub__(self, other):
        if self.units != other.units and self.number and other.number:
            raise_QuantError("Units in sum not compatible", "%s + %s", (self, other))
        number = self.number - other.number
        name = "%s - %s"
        prefu, provenance = inherit_binary(self, other)
        units, sigfig = sigfig_sum(number, self, other)
        return Q(number, name, units, sigfig, prefu, provenance)

    def __pow__(self, other):
        if other.units != unity:
            raise_QuantError("the exponent can't have units", "%s ^ %s", (self, other))
        if abs(other.number - round(other.number)) < 0.00000001:
            exponent = int(round(other.number))
            units = tuple([u * exponent for u in self.units])
        elif self.number < 0:
            raise_QuantError("can't raise negative number to non-integral power", "%s ^ %s", (self, other))
        elif abs(0.5 - other.number) < 0.00000001:
            if sum(u % 2 for u in self.units) == 0:
                units = tuple([u / 2 for u in self.units])
            else:
                raise_QuantError("units have to be squares to be able to take square root", "%s ^ %s", (self, other))
        elif self.units == unity:
            units = self.units
        else:
            raise_QuantError("can't have units for non-integral exponent", "%s ^ %s", (self, other))
        try:
            number = self.number ** other.number
        except ValueError:
            raise_QuantError("arithmetic problem", "%s ^ %s", (self, other))
        sig = self.sigfig
        name = "%s ^ %s"
        return Q(number, name, units, sig, self.prefu, (self, other))


def try_all_derived(SIunits, derived):
    """Score the benefits of replacing SI units by any of the preferred derived units.

    Yields: A tuple(score, derived unit, exponent)

    There is a reward of 2 for each SIunit dropped, and a penalty of 3 for adding a derived unit.
    E.g. going from m^2 to L/m receives a score of -1, but from m^3 to L a score of +3. 
    """
    for d in derived:
        for sign in [-1, 1]:  # 1 means in numerator, -1 in denominator
            improvement = -3
            if derived[d] * sign < 0:
                continue  # don't take away derived units
            for old, used_in_derived in zip(SIunits, unitquant[d].units):
                improvement += 2 * (abs(old) - abs(old - sign * used_in_derived))
            yield (improvement, d, sign)


def unit_string(value, units, prefu={'M', 'L', 'J', 'C', 'V', 'N', 'W', 'Pa'}, math=False):
    """Determine the most compact set of units for a quantity given in SI units.

    Returns: (the number(float) and the units(str)) of the quantity

    """
    SIunits = list(units)
    derived = dict((pu, 0) for pu in prefu if sum(abs(t) for t in unitquant[pu].units) > 1)
    while (1 and derived):
        (improvement, d, sign) = max(try_all_derived(SIunits, derived))
        if improvement <= 0:
            break
        derived[d] += sign
        for i, used_in_derived in enumerate(unitquant[d].units):
            SIunits[i] -= used_in_derived * sign
        value /= unitquant[d].number ** sign
    allunits = derived
    for pu in prefu:
        if pu not in derived and pu not in SIunit_symbols:
            for i, used_in_alternate in enumerate(unitquant[pu].units):
                if used_in_alternate:  # should be 1 or -1
                    allunits[pu] = SIunits[i] / used_in_alternate
                    SIunits[i] = 0
                    value /= unitquant[pu].number ** allunits[pu]
    for u, d in zip(SIunit_symbols, SIunits):
        allunits[u] = d
    return value, pretty_print(allunits.items(), math)


def pretty_print(zippy, math=False):
    """Formats units as a fraction of units, all with positive exponents"""

    sep = "\\ " if math else " "
    template = "%s^%d" if not math else "text{%s}^%d"
    postext = [template % z for z in zippy if z[1] > 0]
    negtext = [template % z for z in zippy if z[1] < 0]
    if len(negtext) == 1 and negtext[0].endswith("^-1"):
        negtext = "/" + negtext[0][:-3]
    elif negtext:
        negtext = "/(%s)" % sep.join(negtext).replace("-", "").replace("^1", "")
    else:
        negtext = ""
    if math and len(postext) > 0 and negtext:
        postext = "(" + sep.join(postext).replace("^1", "") + ")"
    else:
        postext = sep.join(postext).replace("^1", "")
    if not postext:
        if not negtext:
            return ""
        if math:
            return (" 1" + negtext + "").replace("ohm}", "}Omega")
        else:
            return " 1" + negtext + ""
    if math:
        return (sep + postext + negtext).replace("ohm}", "}Omega")
    return sep + postext + negtext


def mostsig(number, ope=1.00000000001): return int(floor(math_log10(abs(number) * ope)))


def numberstring(number, sigfig, math=False, delta=0.0000000001):
    """Formats a number with given significant figures as a string"""

    if number == 0.0 or number == 0:
        return "0"
    least = mostsig(number) - sigfig + 1
    if sigfig == 12 and int(number) and number - (int(number)) < delta:
        return "%d" % int(number)
    if least < 0 and least + sigfig > -2:
        return "%.*f" % (-least, number)
    if not least:
        if math:
            return "text{%.0f.}" % number
        return "%.0f." % number
    if sigfig:
        if math:
            return ("%.*e" % (sigfig - 1, number)).replace("e", "xx10^(").replace("^(+0", "^(").replace("^(-0",
                                                                                                        "^(-") + ")"
        return "%.*e" % (sigfig - 1, number)
    return "%.0f" % number


def number2quantity(text):
    """Turn a number (represented as a string or float) into a quantity.

    The main task is to determine the number of significant figures,
    e.g. 2.51e89 => sigfig = 3
         4.513   => sigfig = 4
         0.037   => sigfig = 2
         1000.   => sigfig = 4
         50000   => sigfig = 12 (NOT 1 or 5)     
    """
    text = text.strip()
    f = float(text)
    text = text.lower().lstrip("-0")
    dot = False
    if "e" in text:
        text, expo = text.split("e")
        dot = True
    if "." in text:
        before, after = text.split(".")
        if before:
            sig = len(text) - 1
        else:
            sig = len(after.lstrip("0"))
        dot = True
    else:
        sig = len(text.strip("0"))
    if not dot:
        sig = 12
    return Q(f, "", sig=sig)


def math_name(name):
    mathname = []
    parts = name.split("_")
    if len(parts[0]) > 1:
        try:
            i = int(parts[0][1:])
            mathname.append("%s_%d" % (parts[0][0], i))
        except ValueError:
            mathname.append("bb{text{%s}}" % parts[0])
    else:
        mathname.append(parts[0])
    if len(parts) > 1 and parts[1]:
        mathname.append("_")
        if len(parts[1]) > 1:
            mathname.append("text{%s}" % parts[1])
        else:
            mathname.append(parts[1])
        if len(parts) > 2:
            mathname.append("bb{text{%s}}" % parts[2])
    return "".join(mathname).replace("Delta", "&Delta;").replace("naught", "&deg;")


def inherit_ternary(q1, q2, q3):
    prefu = q1.prefu | q2.prefu | q3.prefu
    provenance = (q1, q2, q3)
    return prefu, provenance


def inherit_binary(q1, q2):
    prefu = q1.prefu | q2.prefu
    provenance = (q1, q2)
    return prefu, provenance


def sigfig_sum(n, q1, q2):
    """Calculates the significant figures in a sum of two quantities"""

    worst = max((mostsig(q.number) - q.sigfig + 1) for q in (q1, q2))
    sigfig = mostsig(n) - worst + 1 if n else 1
    units = q1.units if q1.number else q2.units
    return units, sigfig


import collections

opprio = collections.defaultdict(int)
opprio["%s ^ %s"] = 5
opprio["%s * %s"] = 3
opprio["%s / %s"] = 4
opprio["%s + %s"] = 2
opprio["-%s"] = 2
opprio["%s - %s"] = 2


def morethantwodiv(string):
    nrdiv = 0
    parenth = 0
    for c in string:
        if c == "(":
            parenth += 1
        elif c == ")":
            parenth -= 1
        elif not parenth and c == "/":
            nrdiv += 1
    return nrdiv >= 2


known_units = dict(
    A=(1.0, Units(A=1)),
    g=(0.001, Units(kg=1)),
    m=(1.0, Units(m=1)),
    cm=(0.01, Units(m=1)),
    s=(1.0, Units(s=1)),
    mol=(1.0, Units(mol=1)),
    K=(1.0, Units(K=1)),
    Cd=(1.0, Units(Cd=1)),
    N=(1.0, Units(kg=1, m=1, s=-2)),
    J=(1.0, Units(kg=1, m=2, s=-2)),
    eV=(1.602176565e-19, Units(kg=1, m=2, s=-2)),
    V=(1.0, Units(A=-1, kg=1, m=2, s=-3)),
    ohm=(1.0, Units(A=-1, kg=1, m=2, s=-3)),
    C=(1.0, Units(A=-1, kg=1, m=2, s=-3)),
    L=(0.001, Units(m=3)),
    M=(1000., Units(mol=1, m=-3)),
    Pa=(1.0, Units(kg=1, m=-2, s=-2)),
    Hz=(1.0, Units(s=-1)),
    atm=(101325.0, Units(kg=1, m=-2, s=-2)),
    mmHg=(133.322368421, Units(kg=1, m=-2, s=-2)),
    min=(60.0, Units(s=1)),
    hr=(3600.0, Units(s=1)),
    W=(1.0, Units(kg=1, m=2, s=-3))
)
known_units["$"] = (1.0, Units(dollar=1))

metric_prefices = dict(
    f=1e-15,
    p=1e-12,
    n=1e-09,
    u=1e-06,
    m=1e-03,
    k=1e+03,
    M=1e+06,
    G=1e+09,
    T=1e+12)

metric_prefices['μ']= 1e-06

unitquant = {}
for unit in known_units:
    unitquant[unit] = Q(known_units[unit][0], unit, known_units[unit][1], prefu=[unit])
    if unit in ["cm", "hr", "atm", "kg", "min", "mmHg", "$"]:
        continue
    for prefix in metric_prefices:
        unitquant[prefix + unit] = Q(known_units[unit][0] * metric_prefices[prefix], prefix + unit,
                                     known_units[unit][1], prefu=[prefix + unit])


def minimum(a, b):
    if a.units != b.units:
        raise TypeError("Can't compare two quantities with different dimensions")
    m = min(a, b, key=lambda x: x.number)
    return Q(m.number, "text{minimum}(%s, %s)", m.units, m.sigfig, m.prefu[:], (a, b))


def exp(a):
    """uses rules by C Mullis and coworkers

    exp(10.34) has 3 significant figures (two decimal places in 10.34, always add one)
    sigfig(10.34) = 4
    mostsig(10.34) = +1
    decimals(10.34) = 2 = sigfig - most - 1
    """
    try:
        if a.units == unity:
            number = math_exp(a.number)
            mostinargument = mostsig(a.number)
            return Q(number, "exp(%s)", a.units, a.sigfig - mostinargument, a.prefu, (a,))
        else:
            raise_QuantError("Can't take e to the power of quantity with units", "exp(%s)", (a,))
    except OverflowError:
        raise_QuantError("The exponent is too large for this calculator", "exp(%s)", (a,))


def sqrt(a):
    if a.number < 0.0:
        raise_QuantError("Won't take square root of negative number", "sqrt(%s)", (a,))
    answer = a ** Q(0.5)
    answer.name = "sqrt(%s)"
    answer.provenance = (a,)
    return answer


def log(a):
    """uses rules by C Mullis and coworkers

    log(10.34) has 5 significant decimal places (four significant figures in 10.34, always add 1)
    sigfig(10.34) = 4
    mostsig(result = ~1) = 0
    sigfig(result) = mostsig(result) + sigdec(result) + 1 = 6
    """
    try:
        if a.units == unity:
            number = math_log10(a.number)
            mostinresult = mostsig(number)
            return Q(number, "log(%s)", a.units, a.sigfig + mostinresult + 2, a.prefu, (a,))
        else:
            raise_QuantError("Can't take log() of quantity with units", "log(%s)", (a,))
    except ValueError:
        raise_QuantError("The argument of log() can't be zero or negative", "log(%s)", (a,))


def ln(a):
    """uses rules by C Mullis and coworkers

    log(10.34) has 5 significant decimal places (four significant figures in 10.34, don't add 1)
    sigfig(10.34) = 4
    mostsig(result = ~1) = 0
    sigfig(result) = mostsig(result) + sigdec(result) = 5
    """
    try:
        if a.units == unity:
            number = math_log(a.number)
            mostinresult = mostsig(number)
            return Q(number, "ln(%s)", a.units, a.sigfig + mostinresult + 1, a.prefu, (a,))
        else:
            raise_QuantError("Can't take ln() of quantity with units", "ln(%s)", (a,))
    except ValueError:
        raise_QuantError("The argument of ln() can't be zero or negative", "ln(%s)", (a,))


def quad(A, B, C):
    discriminant = B ** Q(2) - Q(4) * A * C
    if discriminant.number < 0:
        raise_QuantError("discriminant %f is negative, can't take its root" % discriminant.number, "quad(%s, %s, %s)",
                         (A, B, C))
    root = sqrt(discriminant)
    sol_big, sol_small = (-B + root) / (Q(2) * A), (-B - root) / (Q(2) * A)
    if B.number > 0:
        sol_big, sol_small = sol_small, sol_big
    if abs(B.number) - root.number < 0.000001:
        sol_big_temp = Q(sol_big.number, sig=sol_big.sigfig, units=sol_big.units, prefu=sol_big.prefu)
        sol_big_temp.provenance = (A, B, C)
        sol_big_temp.name = "(text{quadp}(%s, %s, %s))"
        sol_small = C / A / sol_big_temp
    return sol_big, sol_small


def quadp(A, B, C):
    return quad(A, B, C)[0]


def quadn(A, B, C):
    return quad(A, B, C)[1]


def alldigits(a):
    return Q(a.number, "alldigits(%s)", a.units, 20, a.prefu[:], [a])


Kelvin = Q("K")
Kelvinshift = Q(273.15) * Kelvin


def FtoKscale(a):
    if a.units == unity and not a.provenance:
        Kscale = (a - Q(32)) * Q(5) / Q(9) * Kelvin + Kelvinshift
        if Kscale.number < 0:
            raise_QuantError("Input temperature is lower than absolute zero", "text{FtoKscale}(%s)", (a,))
        return Kscale
    else:
        raise_QuantError("Input temperature has to be a unit-less number", "text{FtoKscale}(%s)", (a,))


def CtoKscale(a):
    if a.units == unity and not a.provenance:
        Kscale = a * Kelvin + Kelvinshift
        if Kscale.number < 0:
            raise_QuantError("Input temperature is lower than absolute zero", "text{CtoKscale}(%s)", (a,))
        return Kscale
    else:
        raise_QuantError("Input temperature has to be a unit-less number", "text{CtoKscale}(%s)", (a,))


functions = '''exp sqrt log ln quadp quadn minimum CtoKscale FtoKscale'''.split(" ")
unit_list = []

""" Tests and ideas

c = 7 (g m)/(mol s)

calc([],["f = 3.4 mg + 20 s"],True)

unitquant[kg]

Quantity(3.5)
Quantity("3.5")
Quantity("kg")

figure_out_name("fg90 = 3.4 mg", [], [])

calc([],["f = 3.4 mg", "m = 20 s"],False)

text = "24.5e-65 kg/m/s^2 / g0 + t0^2 + log(x0)"
tokens = scan(text)
triple_tokens = make_triple_tokens(tokens)
stripped = "".join(t[1] if t[0]=="O" else "%*s" % (len(t[1]),t[1]) for t in tokens)
shortcut = "".join(t[1] if t[0]=="O" else "%*s" % (len(t[1]),t[0]) for t in tokens)
triple_shortcut = "".join(t[1]+("%*s" % (len(t[2]),t[0])) for t in triple_tokens)
print(text)
print(tokens)
print(stripped)
print(shortcut.replace("O","*"))
print(triple_shortcut)
i = create_Python_expression(triple_tokens, dict(g0="g_val", t0="t_val", x0="x_val"))
print (i)


"""
