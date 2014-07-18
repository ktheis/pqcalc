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
from math import sqrt as math_sqrt

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
      sigfig(int): The number of significant figures. 100 refers to an exact integer
      uncert(float): An estimate of the uncertainty of the quantity
      prefu(list(str)): the preferred units for the quantity, given as str in unitquant
      provenance: quantities from which it was derived

    Examples:
      Q(2) is the dimensionless number 2
      Q("kg") is the quantity 1 kg
      Q(3.0, "", Units(kg=1), 2, [], None) is 3.0 kg

    """

    def __init__(self, number=0.0, name="", units=unity, uncert=0.0, prefu=[], provenance=None):
        """

        """

        try:
            number + 1.0
            self.number = float(number)
            self.units = Units(*units)
            self.name = name[:]
            self.prefu = set(prefu)
            self.uncert = uncert
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
        self.runcert = repr(self.uncert)
        if self.provenance:
            return "Q(%(rnumber)s, '%(name)s', %(units)s, %(runcert)s, %(prefu)s, %(provenance)s)" % self.__dict__
        if self.prefu:
            return "Q(%(rnumber)s, '%(name)s', %(units)s, %(runcert)s, %(prefu)s)" % self.__dict__
        if self.name:
            return "Q(%(rnumber)s, '%(name)s', %(units)s, %(runcert)s)" % self.__dict__
        return "Q(%(rnumber)s, units=%(units)s, uncert=%(runcert)s)" % self.__dict__

    def __str__(self):
        return ascii_qvalue(self)

    @property
    def sigfig(self):
        try:
            most = int(floor(math_log10(abs(self.number))))
            sig = int(floor(math_log10(self.uncert)))
            sigfig = most - sig + 1
        except:
            return 100
        if sigfig > 0:
            return sigfig
        return 1

    def setdepth(self):
        if not hasattr(self, "depth"):
            if not self.provenance:
                self.depth = 0
            else:
                self.depth = 1 + max(child.setdepth() for child in self.provenance)
        return self.depth

    def steps(self, level, writer, subs=None):
        '''
        :param level: -1: task, 0: value, 1..n: work
        :param writer: either ascii or latex
        :param subs: modify q.name for latex output
        :return: a string describing an expression
        '''
        if level < 0 and not self.provenance:
            return writer(self, showvalue=False)
        if not level or level > self.depth:
            return writer(self, guard=0 if (level <= 1 or not self.provenance) else 1)
        children = []
        name = self.name
        if subs and name in subs:
            name = subs[name]
        for index, q in enumerate(self.provenance):
            child = q.steps(level, writer, subs)
            if q.provenance and level <= q.depth:
                if opprio[name] > opprio[q.name] and opprio[name] and opprio[q.name]:
                    child = "(" + child + ")"
            if "/" in name and ("/" in child or (index==1 and level >= 0 and q.units != unity)):
                child = "(" + child + ")"
            elif name.startswith("-") and child.startswith("-"):
                child = "(" + child + ")"
            if "^" in name and q.units != unity:
                child = "(" + child + ")"
            children.append(child)
        return name % tuple(children)


    def __mul__(self, other):
        units = tuple([x[0] + x[1] for x in zip(self.units, other.units)])
        number = self.number * other.number
        uncert = math_sqrt((self.uncert / self.number)**2 + (other.uncert / other.number)**2) * number
        name = "%s * %s"
        prefu, provenance = inherit_binary(self, other)
        return Q(number, name, units, uncert, prefu, provenance)

    def __truediv__(self, other):
        units = tuple([x[0] - x[1] for x in zip(self.units, other.units)])
        try:
            number = self.number / other.number
        except ZeroDivisionError:
            raise_QuantError("denominator is zero", "%s / %s", (self, other))
        name = "%s / %s"
        uncert = math_sqrt((self.uncert / self.number)**2 + (other.uncert / other.number)**2) * number
        prefu, provenance = inherit_binary(self, other)
        return Q(number, name, units, uncert, prefu, provenance)

    def __div__(self, other): return self.__truediv__(other)

    def __neg__(self):
        return Q(-self.number, "-%s", self.units, self.uncert, self.prefu, (self,))

    def __pos__(self):
        return self

    def __add__(self, other):
        if self.units != other.units and self.number and other.number:
            raise_QuantError("Units in sum not compatible", "%s + %s", (self, other))
        number = self.number + other.number
        name = "%s + %s"
        prefu, provenance = inherit_binary(self, other)
        units, uncert = uncert_sum(number, self, other)
        return Q(number, name, units, uncert, prefu, provenance)

    def __sub__(self, other):
        if self.units != other.units and self.number and other.number:
            raise_QuantError("Units in sum not compatible", "%s + %s", (self, other))
        number = self.number - other.number
        name = "%s - %s"
        prefu, provenance = inherit_binary(self, other)
        units, uncert = uncert_sum(number, self, other)
        return Q(number, name, units, uncert, prefu, provenance)

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
        name = "%s ^ %s"
        return Q(number, name, units, self.uncert/self.number * number * other.number, self.prefu, (self, other))


def ascii_units(list1):
    list2 = [i[0] for i in list1 if i[1] == 1]
    list2.extend(["%s^%d" % i for i in list1 if i[1] > 1])
    return " ".join(list2)

def latex_units(list1):
    list2 = ["\\rm{%s}" % i[0] for i in list1 if i[1] == 1]
    list2.extend(["\\rm{%s}^{%d}" % i for i in list1 if i[1] > 1])
    return "\\ ".join(list2)


def ascii_qvalue (q, guard=0):
    """Formats quantities as number times a fraction of units, all with positive exponents"""
    value, poslist, neglist = unit_string(q.number, q.units, q.prefu)
    numbertext = ascii_number(value, q.sigfig, q.uncert * value/q.number)
    # numbertext = ascii_number(value, q.sigfig + guard)
    if len(neglist) == 1 and neglist[0][1] == 1:
        negtext = "/" + neglist[0][0]
    elif neglist:
        negtext = "/(%s)" % ascii_units(neglist)
    else:
        negtext = ""
    if not poslist:
        if not neglist:
            return numbertext
        return numbertext + " 1" + negtext
    return numbertext + " " +  ascii_units(poslist) + negtext


def latex_qvalue (q, guard=0):
    value, poslist, neglist = unit_string(q.number, q.units, q.prefu)
    #  numbertext = latex_number(ascii_number(value, q.sigfig, q.uncert * value/q.number))
    numbertext = latex_number(ascii_number(value, q.sigfig + guard))
    if neglist:
        negtext = "\\frac{%%s}{%s}" % latex_units(neglist)
    else:
        negtext = "%s"
    if not poslist:
        if not neglist:
            return numbertext
        return numbertext + negtext % "1"
    return numbertext + "\\  " + negtext % latex_units(poslist)


def ascii_writer(q, showvalue=True, guard=0):
    if not showvalue and q.name:
        return q.name
    return ascii_qvalue(q, guard)


def latex_writer(q, showvalue=True, guard=0):
    if not showvalue and q.name:
        return latex_name(q.name)
    #  return repr(q)
    return latex_qvalue(q, guard)


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

def unit_string(value, units, prefu={'M', 'L', 'J', 'C', 'V', 'N', 'W', 'Pa'}):
    """Determine the most compact set of units for a quantity given in SI units.

    Returns: (the number(float) and the units(str)) of the quantity

    """
    if units == unity:
        return value, "", ""
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
    poslist = [(u,exp) for u, exp in allunits.items() if exp > 0]
    neglist = [(u,-exp) for u, exp in allunits.items() if exp < 0]
    return value, poslist, neglist


def mostsig(number, ope=1.00000000001): return int(floor(math_log10(abs(number) * ope)))


def latex_number(ascii):
    if "e" in ascii:
        return ascii.replace("e", r"\times 10^{") + "}"
    if "/" in ascii:
        n, d = ascii.split("/")
        return "\\frac{%s}{%s}" % (n[1:], d[:-1])
    return ascii

from fractions import Fraction

def ascii_number(number, sigfig, uncert=None, delta=0.0000000001):
    """Formats a number with given significant figures as a string"""

    if number == 0.0 or number == 0:
        return "0"
    if (not uncert) and sigfig >= 100:
        if int(number) and number - (int(number)) < delta:
            return "%d" % int(number)
        a = Fraction(number).limit_denominator()
        return "(%d / %d)" % (a.numerator,a.denominator)

    u = "%.5G" % uncert if uncert else ""
    u = u.replace(".","").lstrip("0")
    if ("E" in u):
        u = u.split("E")[0]
    if u:
        if len(u) > 1:
            sigfig += 1
            u = u[:2]
        u = "(" + u + ")"
    least = mostsig(number) - sigfig + 1
    print (number, uncert, u, sigfig)
    if least < 0 and least + sigfig > -2:
        return "%.*f%s" % (-least, number, u)
    if not least:
        return "%.0f%s." % (number, u)
    if sigfig:
        t = ("%.*e" % (sigfig - 1, number)).replace("^+0", "^").replace("^-0", "^-")
        m,e = t.split("e")
        return "%s%se%s" % (m, u, e)
    return "%.0(?)f" % number


def number2quantity(text):
    """Turn a number (represented as a string or float) into a quantity.

    The main task is to determine the uncertainty,
    e.g. 2.51e89 => uncert = 1e87
         4.513   => uncert = 1e-3
         0.037   => uncert = 1e-3
         1000.   => uncert = 1
         50000   => uncert = 0.0
    """
    text = text.strip()
    mult = 1
    if "(" in text and ")" in text:
        before, tmp = text.split("(")
        uncert, after = tmp.split(")")
        text = before + after
        mult = float(uncert)
    f = float(text)
    text = text.lower().lstrip("-0")
    dot = False
    expo = 0
    if "e" in text:
        text, expotext = text.split("e")
        expo = int(expotext)
        dot = True
    if "." in text or mult != 1:
        if "." in text:
            before, after = text.split(".")
            expo -= len(after)
        dot = True
    else:
        uncert = 1.
    if not dot:
        uncert = 0.0
    else:
        uncert = float("1e%s" % expo)
    return Q(f, "", uncert=uncert*mult)


def latex_name(name):
    mathname = []
    parts = name.split("_")
    if len(parts[0]) > 1:
        try:
            i = int(parts[0][1:])
            mathname.append("%s_{%d}" % (parts[0][0], i))
        except ValueError:
            mathname.append("\\rm{%s}" % parts[0])
    else:
        mathname.append(parts[0])
    if len(parts) > 1 and parts[1]:
        mathname.append("_")
        if len(parts[1]) > 1:
            mathname.append("\\rm{%s}" % parts[1])
        else:
            mathname.append(parts[1])
        if len(parts) > 2:
            mathname.append("\\rm{%s}" % parts[2])
    return "".join(mathname).replace("Delta", "\Delta ").replace("naught", "\deg ")


def inherit_binary(q1, q2):
    prefu = q1.prefu | q2.prefu
    provenance = (q1, q2)
    return prefu, provenance


def uncert_sum(n, q1, q2):
    """Calculates the significant figures in a sum of two quantities"""

    units = q1.units if q1.number else q2.units
    uncert = math_sqrt(q1.uncert**2 + q2.uncert**2)
    return units, uncert


import collections

opprio = collections.defaultdict(int)
opprio["%s ^ %s"] = 5
opprio["%s * %s"] = 3
opprio["%s / %s"] = 4
opprio["%s + %s"] = 2
opprio["-%s"] = 2
opprio["%s - %s"] = 2


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
    Pa=(1.0, Units(kg=1, m=-1, s=-2)),
    Hz=(1.0, Units(s=-1)),
    atm=(101325.0, Units(kg=1, m=-1, s=-2)),
    mmHg=(133.322368421, Units(kg=1, m=-1, s=-2)),
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
    return Q(m.number, "text{minimum}(%s, %s)", m.units, m.uncert, m.prefu[:], (a, b))


def exp(a):
    try:
        if a.units == unity:
            number = math_exp(a.number)
            return Q(number, "exp(%s)", a.units, abs(a.uncert * number), a.prefu, (a,))
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
    try:
        if a.units == unity:
            number = math_log10(a.number)
            return Q(number, "log(%s)", a.units, abs(a.uncert / a.number), a.prefu, (a,))
        else:
            raise_QuantError("Can't take log() of quantity with units", "log(%s)", (a,))
    except ValueError:
        raise_QuantError("The argument of log() can't be zero or negative", "log(%s)", (a,))


def ln(a):
    try:
        if a.units == unity:
            number = math_log(a.number)
            return Q(number, "ln(%s)", a.units, a.uncert / a.number, a.prefu, (a,))
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
        sol_big_temp = Q(sol_big.number, uncert=sol_big.uncert, units=sol_big.units, prefu=sol_big.prefu)
        sol_big_temp.provenance = (A, B, C)
        sol_big_temp.name = "(text{quadp}(%s, %s, %s))"
        sol_small = C / A / sol_big_temp
    return sol_big, sol_small


def quadp(A, B, C):
    return quad(A, B, C)[0]


def quadn(A, B, C):
    return quad(A, B, C)[1]


def alldigits(a):
    return Q(a.number, "alldigits(%s)", a.units, a.uncert / 100000., a.prefu, [a])


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


functions = '''exp sqrt log ln quadp quadn minimum CtoKscale FtoKscale alldigits'''.split(" ")
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