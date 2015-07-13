# coding=utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
"""

Classes and functions to do arithmetic with physical quantities.

At the core of this module is the class Q, which defines a number that has units, a name, and a crude indication
of uncertainty (significant figures).

The way significant figures are treated here is just for number formatting - all calculations are done to the
maximum precision of python floats (~57 bits, equivalent to ~17 decimal digits). There is a special function
"moredigits" to retrieve the full internal representation of the number.

The online calculator hosted at http:\\\\ktheis.pythonanywhere.com uses this code.

Author: Karsten Theis (ktheis@westfield.ma.edu)
"""
from __future__ import division

import math
from math import log10 as math_log10
from math import log as math_log
from math import exp as math_exp
from math import sin as math_sin
from math import cos as math_cos
from math import tan as math_tan
from math import floor
from math import sqrt as math_sqrt
from fractions import Fraction

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
        return "Units(" + ",".join("%s=%s" % (x[0],repr(x[1])) for x in zip(symbols, self) if x[1]) + ")"


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
            self.number = number
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
        if self.name:
            self.fakename = 'somename'
        else:
            self.fakename = ''
        if self.name in unitquant and self.__dict__ == unitquant[self.name].__dict__:
            return u"Q('%s')" % self.name
        self.rnumber = repr(self.number)
        if self.rnumber.startswith("inf"):
            raise OverflowError(self.rnumber)
        self.runcert = repr(self.uncert)
        self.rname = repr(self.name)
        if self.provenance:
            return u"Q(%(rnumber)s, '%(name)s', %(units)s, %(runcert)s, %(prefu)s, %(provenance)s)" % self.__dict__
        if self.prefu:
            return u"Q(%(rnumber)s, '%(name)s', %(units)s, %(runcert)s, %(prefu)s)" % self.__dict__
        if self.name:
            rr =  u"Q(%(rnumber)s, '%(name)s', %(units)s, %(runcert)s)" % self.__dict__
            return rr
        return u"Q(%(rnumber)s, units=%(units)s, uncert=%(runcert)s)" % self.__dict__

    def __str__(self):
        return ascii_qvalue(self)

    def setdepth(self):
        if not hasattr(self, "depth"):
            if not self.provenance:
                self.depth = 0
            else:
                self.depth = 1 + max(child.setdepth() for child in self.provenance)
                if self.name == "-%s":
                    self.depth -= 1
        return self.depth

    def steps(self, level, writer, subs=None, flaigs=dict()):
        '''
        :param level: -1: task, 0: value, 1..n: work
        :param writer: either ascii or latex
        :param subs: modify q.name for latex output
        :return: a string describing an expression
        '''
        if level < 0 and not self.provenance:
            return writer(self, showvalue=False)
        if not level or level > self.depth:
            return writer(self, flags=flaigs, guard=0 if (level <= 1 or not self.provenance) else 1)
        children = []
        name = self.name
        for index, q in enumerate(self.provenance):
            child = q.steps(level, writer, subs)
            if ((q.provenance and level <= q.depth and opprio[name] > opprio[q.name] and opprio[name] and opprio[q.name] and not (subs and "/" in name)) or
                (name.startswith("-") and child.startswith("-")) or
                ("*" in name and index == 1 and child.startswith("-")) or
                ("^" in name and q.units != unity and level >= 0) or
                ("^" in name and child.startswith("-") and index == 0) or
                ("^" in name and ("times" in child or "frac" in child))):
                child = "(" + child + ")"
            children.append(child)
        if subs and name in subs:
            name = subs[name]
        return name % tuple(children)


    def __mul__(self, other):
        units = tuple([x[0] + x[1] for x in zip(self.units, other.units)])
        number = self.number * other.number
        if number:
            uncert = math_sqrt((self.uncert / self.number)**2 + (other.uncert / other.number)**2) * abs(number)
        else:
            uncert = 0.0
        name = "%s * %s"
        if hasattr(number,'denominator') and number.denominator == 1:
            number = int(number)
        prefu, provenance = inherit_binary(self, other)
        return Q(number, name, units, uncert, prefu, provenance)

    def __truediv__(self, other):
        units = tuple([x[0] - x[1] for x in zip(self.units, other.units)])
        try:
            number = self.number / other.number
        except ZeroDivisionError:
            raise_QuantError("denominator is zero", "%s / %s", (self, other))
        name = "%s / %s"
        if self.number:
            uncert = math_sqrt((self.uncert / self.number)**2 + (other.uncert / other.number)**2) * abs(number)
        else:
            uncert = 0.0
        if not uncert:
            try:
                number = Fraction(self.number, other.number)
                if number.denominator == 1:
                    number = int(number)
            except TypeError:
                pass
        prefu, provenance = inherit_binary(self, other)
        return Q(number, name, units, uncert, prefu, provenance)

    def __div__(self, other): return self.__truediv__(other)

    def __neg__(self):
        return Q(-self.number, "-%s", self.units, self.uncert, self.prefu, (self,))

    def __pos__(self):
        return self

    def __add__(self, other):
        if self.units != other.units and self.number and other.number:
            for s, o in zip(self.units, other.units):
                if s == o:
                    continue
                elif '%g' % s == '%g' % o:
                    continue
                else:
                    raise_QuantError("Units in sum have distinct exponents (%g %g)" % (s,o), "%s + %s", (self, other))
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
        if self.units == unity:
            units = self.units
        else:
            if not hasattr(other.number, 'denominator'):
                raise_QuantError("can't raise units to irrational exponent", "%s ^ %s", (self, other))
            if self.number < 0:
                raise_QuantError("can't raise negative number to non-integral power", "%s ^ %s", (self, other))
            units = tuple([fraction_or_int(u * other.number) for u in self.units])
        try:
            if hasattr(self.number, 'denominator') and hasattr(other.number, 'denominator') and other.number>10:
                number = self.number ** float(other.number)
            else:
                number = self.number ** other.number
        except ValueError:
            raise_QuantError("arithmetic problem", "%s ^ %s", (self, other))
        except OverflowError:
            raise_QuantError("overflow: value too high", "%s ^ %s", (self, other))
        name = "%s ^ %s"
        uncert = abs(self.uncert/self.number * number * other.number) + abs(other.uncert * math_log(abs(self.number)) * number)
        return Q(number, name, units, uncert, self.prefu, (self, other))

def fraction_or_int(number):
    if number.denominator == 1:
        return int(number)
    return number

def sigfig(number, uncert):
    try:
        most = int(floor(math_log10(abs(number))))
        sig = int(floor(math_log10(uncert*1.05)))
        sigfig = most - sig + 1
    except:
        return 100
    if sigfig > 0:
        return sigfig
    return 1


def ascii_units(list1):
    list2 = [i[0] for i in list1 if i[1] == 1]
    list2.extend(["%s^%s" % i for i in list1 if i[1] != 1])
    return " ".join(list2)

def latex_units(list1):
    list2 = ["\\mathrm{%s}" % i[0] for i in list1 if i[1] == 1]
    list2.extend(["\\mathrm{%s}^{%s}" % i for i in list1 if i[1] != 1])
    return "\\ ".join(list2)


def ascii_qvalue (q, guard=0):
    """Formats quantities as number times a fraction of units, all with positive exponents"""
    value, poslist, neglist = unit_string(q.number, q.units, q.prefu)
    numbertext = ascii_number(value, sigfig(q.number,q.uncert) + guard)
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


def latex_qvalue (q, guard=0, uncert=False, hideunits=False, hidenumbers=False):
    value, poslist, neglist = unit_string(q.number, q.units, q.prefu)
    try:
        uc = q.uncert * value/q.number
    except:
        uc = 0
    sf = sigfig(value, uc)
    if uncert:
        numbertext = latex_number(ascii_number(value, sf, uc))
    elif hidenumbers:
        numbertext = "\_\_\_\_\_\_\_\_\_\_\_\_"
    else:
        numbertext = latex_number(ascii_number(value, sf + guard))
    if hideunits:
        return numbertext + ("\\phantom{\\frac{km mol}{kg mol}}" if q.units != unity else "")
    if neglist:
        negtext = "\\frac{%%s}{%s}" % latex_units(neglist)
    else:
        negtext = "%s"
    if not poslist:
        if not neglist:
            return numbertext
        return numbertext + negtext % "1"
    return numbertext + "\\  " + negtext % latex_units(poslist)


def ascii_writer(q, showvalue=True, guard=0, flags=dict()):
    if not showvalue and q.name:
        return q.name
    return ascii_qvalue(q, guard)


def latex_writer(q, showvalue=True, guard=0, flags=dict()):
    if not showvalue and q.name:
        return latex_name(q.name)
    return latex_qvalue(q, guard, **flags)

def try_all_derived(SIunits, derived):
    """Score the benefits of replacing SI units by any of the preferred derived units.

    Yields: A tuple(score, derived unit, exponent)

    There is a reward of 20 for each SIunit dropped, and a penalty of 30 for adding a derived unit.
    E.g. going from m^2 to L/m receives a score of -10, but from m^3 to L a score of +30.
    """
    for d in derived:
        for sign in [-1, 1]:  # 1 means in numerator, -1 in denominator
            improvement = -30
            if derived[d] * sign < 0:
                continue  # don't take away derived units
            for old, used_in_derived in zip(SIunits, unitquant[d].units):
                improvement += 20 * (abs(old) - abs(old - sign * used_in_derived))
                if old and not (old - sign * used_in_derived):
                    improvement += 6
            yield (improvement, d, sign)

def unit_string(value, units, prefu={'M', 'L', 'J', 'C', 'V', 'N', 'W', 'Pa'}):
    """Determine the most compact set of units for a quantity given in SI units.

    Returns: (the number(float) and the units(str)) of the quantity

    """
    if units == unity or not value:
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
    if derived.get('V') == 0 and derived.get('kJ') == 0 and SIunits[0] == 1 and SIunits[3] == 1:
        derived['V'] -= 1
        derived['kJ'] += 1
        SIunits[0] = 0
        SIunits[3] = 0
        value /= 1000
    allunits = dict([(x,derived[x]) for x in derived if derived[x]])
    DUS = [du for du in allunits if du in derived]
    for DU in DUS:
        choices = [pu for pu in derived if unitquant[pu].units == unitquant[DU].units]
        if not choices:
            break
        quality = [(abs(math_log10(abs(value) / (unitquant[c].number/unitquant[DU].number) ** allunits[DU])-1.0), c) for c in choices]
        best = min(quality)[1]
        if best != DU:
            allunits[best] = allunits[DU]
            value /= (unitquant[best].number/unitquant[DU].number) ** allunits[best]
            allunits[DU] = 0
    for i, SIU in enumerate(SIunit_symbols):
        if not SIunits[i]:
            continue
        choices = [pu for pu in prefu if (pu not in derived) and unitquant[pu].units[i]]
        if not choices:
            break
        quality = [(abs(math_log10(abs(value) / unitquant[c].number ** (SIunits[i] / unitquant[c].units[i]))-1.0), c) for c in choices]
        best = min(quality)[1]
        allunits[best] = Fraction(SIunits[i],unitquant[best].units[i])
        if allunits[best].denominator == 1:
            allunits[best] = int(allunits[best])
        SIunits[i] = 0
        value /= unitquant[best].number ** allunits[best]
    for u, d in zip(SIunit_symbols, SIunits):
        if d:
            allunits[u] = d
    poslist = [(u,exp) for u, exp in allunits.items() if exp > 0]
    neglist = [(u,-exp) for u, exp in allunits.items() if exp < 0]
    return value, poslist, neglist


def mostsig(number, ope=1.00000000001): return int(floor(math_log10(abs(number) * ope)))


def latex_number(ascii):
    if "e" in ascii:
        return ascii.replace("e", r"\times 10^{") + "}"
    if "/" in ascii:
        sign, rest = ascii.split("(")
        n, d = rest.split("/")
        return "%s\\frac{%s}{%s}" % (sign, n, d[:-1])
    return ascii


def ascii_number(number, sigfig, uncert=None, delta=0.0000000001):
    """Formats a number with given significant figures as a string"""

    if number == 0.0 or number == 0:
        return "0"
    if (not uncert) and sigfig >= 100:
        if hasattr(number, 'denominator'):
            if number.denominator == 1:
                return "%d" % int(number)
            else:
                if number.numerator > 0:
                    return "(%d / %d)" % (number.numerator,number.denominator)
                return "-(%d / %d)" % (-number.numerator,number.denominator)
        if int(number) and abs(number) - abs(int(number)) < delta:
            return "%d" % int(number)
            raise_QuantError('What a crazy coincidence', '', None)
        a = Fraction(number).limit_denominator()
        if a.numerator:
            discr = number * a.denominator / a.numerator
            if a.denominator < 10000 and discr < 1.00000001 and discr > 0.99999999:
                if a.numerator > 0:
                    return "(%d / %d)" % (a.numerator,a.denominator)
                return "-(%d / %d)" % (-a.numerator,a.denominator)
        sigfig = 17
    if uncert:
        u = "%.1G" % uncert
        if "." in u:
            least = -len(u.split(".")[1])
        else:
            least = len(u)
        u = u.replace(".","").lstrip("0")
        if ("E" in u):
            u, exp = u.split("E")
            least = int(exp) - 1
        u = "(" + u + ")"
    else:
        u = ""
        least = mostsig(number) - sigfig + 1
    if least < 0 and least + sigfig > -2 and least + sigfig < 5:
        return "%.*f%s" % (-least, number, u)
    if not least:
        return "%.0f%s." % (number, u)
    if sigfig:
        t = ("%.*e" % (sigfig - 1, number)).replace("e+", "e").replace("e0","e").replace("e-0", "e-")
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
    if '/' in text:
        numerator, denominator = text.split('/')
        return Q(Fraction(int(numerator),int(denominator)), "", uncert=0) # pure fraction such as 1/2
    try:
        f = int(text)
    except:
        f = float(text)
    if math.isinf(f) and math.isnan(f):
        raise OverflowError(text)
    text = text.lower().lstrip("-0")
    dot = False
    expo = 0
    if "e" in text:
        text, expotext = text.split("e")
        expo = int(expotext)
    #    dot = True
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
    if "[" in name:
        name, brackets = name.split("[")
        bb = brackets.split("]")
        if len(bb) > 1 and len(bb[1]) > 0:
            appendix = bb[1]
        else:
            appendix = ""
    else:
        brackets = ""
    parts = name.split("_")
    if len(parts[0]) > 1:
        try:
            i = int(parts[0][1:])
            mathname.append(parts[0][0])
            mathname.append(parts[0][1:])
        except ValueError:
            mathname.append("\\mathrm{%s}" % parts[0])
    elif parts[0]:
        mathname.append(parts[0])
    for part in parts[1:]:
        if part:
            mathname.append("\\mathrm{%s}" % part)
    if brackets:
        if mathname:
            mathname.append("\\ce{" + bb[0] + "}")
        else:
            mathname.append("[\\ce{" + bb[0] + "}]")
        for part in appendix.split("_"):
            if part:
                 mathname.append("\\mathrm{%s}" % part)
    if len(mathname) > 1:
        return mathname[0] + "_{" + ",".join(mathname[1:]) + "}"
    return mathname[0]

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
opprio["%s / %s"] = 3
opprio["%s + %s"] = 2
opprio["-%s"] = 3
opprio["%s - %s"] = 2


known_units = dict(
    A=(1, Units(A=1)),
    g=(Fraction(1,1000), Units(kg=1)),
    m=(1, Units(m=1)),
    cm=(Fraction(1/100), Units(m=1)),
    s=(1, Units(s=1)),
    mol=(1, Units(mol=1)),
    K=(1, Units(K=1)),
    Cd=(1, Units(Cd=1)),
    N=(1, Units(kg=1, m=1, s=-2)),
    J=(1, Units(kg=1, m=2, s=-2)),
    eV=(1.602176565e-19, Units(kg=1, m=2, s=-2)),
    V=(1, Units(A=-1, kg=1, m=2, s=-3)),
    C=(1, Units(A=1, s=1)),
    L=(Fraction(1/1000), Units(m=3)),
    M=(1000, Units(mol=1, m=-3)),
    Pa=(1, Units(kg=1, m=-1, s=-2)),
    Hz=(1, Units(s=-1)),
    atm=(101325, Units(kg=1, m=-1, s=-2)),
    mmHg=(133.322368421, Units(kg=1, m=-1, s=-2)),
    min=(60, Units(s=1)),
    h=(3600, Units(s=1)),
    W=(1, Units(kg=1, m=2, s=-3))
)
known_units["Ω"] =(1.0, Units(A=-2, kg=1, m=2, s=-3))

known_units["$"] = (1.0, Units(dollar=1))

metric_prefices = dict(
    f=Fraction(1,1000000000000000),
    p=Fraction(1,1000000000000),
    n=Fraction(1,1000000000),
    u=Fraction(1,1000000),
    m=Fraction(1,1000),
    k=1000,
    M=1000000,
    G=1000000000,
    T=1000000000000)

metric_prefices['μ']= Fraction(1,1000000)

unitquant = {}
for unit in known_units:
    unitquant[unit] = Q(known_units[unit][0], unit, known_units[unit][1], prefu=[unit])
    if unit in ["cm", "h", "d", "atm", "kg", "min", "mmHg", "$"]:
        continue
    for prefix in metric_prefices:
        unitquant[prefix + unit] = Q(known_units[unit][0] * metric_prefices[prefix], prefix + unit,
                                     known_units[unit][1], prefu=[prefix + unit])

def absolute(m):
    return Q(abs(m.number), "\\mathrm{absolute}(%s)", m.units, m.uncert, m.prefu, (m,))


def minimum(*a):
    units = a[0].units
    for q in a:
        if units != q.units:
            raise_QuantError("Can't compare quantities with different dimensions", "minimum(%s, ... %s)", (a[0],q))
    m = min(*a, key=lambda x: x.number)
    return Q(m.number, "\\mathrm{minimum}(%s)" % ", ".join(["%s"] * len(a)), m.units, m.uncert, m.prefu, tuple(a))


def maximum(*a):
    units = a[0].units
    for q in a:
        if units != q.units:
            raise_QuantError("Can't compare quantities with different dimensions", "maximum(%s, ... %s)", (a[0],q))
    m = max(*a, key=lambda x: x.number)
    return Q(m.number, "\\mathrm{minimum}(%s)" % ", ".join(["%s"] * len(a)), m.units, m.uncert, m.prefu, tuple(a))


def average(*a):
    units = a[0].units
    for q in a:
        if units != q.units:
            raise_QuantError("Can't average quantities with different dimensions", "average(%s, ... %s)", (a[0],q))
    m = sum(a,Q(0.0))/Q(len(a))
    return Q(m.number, "\\mathrm{average}(%s)" % ", ".join(["%s"] * len(a)), m.units, m.uncert, m.prefu, tuple(a))


def sumover(*a):
    units = a[0].units
    for q in a:
        if units != q.units:
            raise_QuantError("Can't add quantities with different dimensions", "sumover(%s, ... %s)", (a[0],q))
    m = sum(a,Q(0.0))
    return Q(m.number, "\\mathrm{sumover}(%s)" % ", ".join(["%s"] * len(a)), m.units, m.uncert, m.prefu, tuple(a))


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
    answer = a ** Q('1/2')
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
            return Q(number, "ln(%s)", a.units, abs(a.uncert / a.number), a.prefu, (a,))
        else:
            raise_QuantError("Can't take ln() of quantity with units", "ln(%s)", (a,))
    except ValueError:
        raise_QuantError("The argument of ln() can't be zero or negative", "ln(%s)", (a,))


def sin(a):
    try:
        if a.units == unity:
            number = math_sin(a.number)
            return Q(number, "sin(%s)", a.units, abs(a.uncert * math_cos(a.number)), a.prefu, (a,))
        else:
            raise_QuantError("Can't take sin() of quantity with units", "sin(%s)", (a,))
    except ValueError:
        raise_QuantError("argument of sin()?", "sin(%s)", (a,))


def cos(a):
    try:
        if a.units == unity:
            number = math_cos(a.number)
            return Q(number, "cos(%s)", a.units, abs(a.uncert * math_sin(a.number)), a.prefu, (a,))
        else:
            raise_QuantError("Can't take cos() of quantity with units", "cos(%s)", (a,))
    except ValueError:
        raise_QuantError("argument of cos()?", "cos(%s)", (a,))


def tan(a):
    try:
        if a.units == unity:
            number = math_tan(a.number)
            return Q(number, "tan(%s)", a.units, a.uncert * (1 + number**2), a.prefu, (a,))
        else:
            raise_QuantError("Can't take tan() of quantity with units", "tan(%s)", (a,))
    except ValueError:
        raise_QuantError("argument of tan()?", "tan(%s)", (a,))


def quad(A, B, C):
    BB = B ** Q(2)
    AC4 = Q(4) * A * C
    if BB.units != AC4.units:
        raise_QuantError("B * B has to have the same units as 4 * A * C ", "quad(%s, %s, %s)", (A, B, C))
    discriminant = BB - AC4
    if discriminant.number < 0:
        raise_QuantError("discriminant %f is negative, can't take its root" % discriminant.number, "quad(%s, %s, %s)",
                         (A, B, C))
    root = sqrt(discriminant)
    sol_big, sol_small = (-B + root) / (Q(2) * A), (-B - root) / (Q(2) * A)
    if B.number > 0:
        sol_big, sol_small = sol_small, sol_big
    if abs(abs(B.number) - root.number) < 0.000001:
        sol_big_temp = Q(sol_big.number, uncert=sol_big.uncert, units=sol_big.units, prefu=sol_big.prefu)
        sol_big_temp.provenance = (A, B, C)
        sol_big_temp.name = "(quadp(%s, %s, %s))"
        sol_small = C / A / sol_big_temp
    return sol_big, sol_small


def quadp(A, B, C):
    return quad(A, B, C)[0]


def quadn(A, B, C):
    return quad(A, B, C)[1]


def moredigits(a):
    return Q(a.number, "moredigits(%s)", a.units, a.uncert / 100000., a.prefu, [a])

def uncertainty(a):
    return Q(a.uncert, "uncertainty(%s)", a.units, a.uncert / 100000., a.prefu, [a])


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


functions = '''sin cos tan exp sqrt log ln quadp quadn minimum maximum absolute CtoKscale FtoKscale moredigits uncertainty average sumover'''.split(" ")
unit_list = []

if __name__ == "__main__":
    g5 = Q(4.5, u'blaν', Units(m=1), 0.1)
    print(g5)
    print(str(g5))
    rr= repr(g5)
    print(rr)
    print('%s' % g5.name)

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