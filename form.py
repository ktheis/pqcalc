# coding=utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from quantities import functions, known_units

selector = '''
<select %s onchange="insertAtCaret('commands',this.options[this.selectedIndex].value, %s);">
  %s
</select></FONT>'''

selectoroption = '''
  <option value="%s">%s</option>'''

def fill_selector(header, choices, backup=0):
    html = ['<option value="" selected="selected" disable="disabled">%s</option>' % header]
    for term in choices:
        html.append(selectoroption % (term, term))
    return selector % ("", backup, "".join(html))

# unit selectors, pre-baked
unit_list = known_units.keys()
unit_list.sort(key=lambda x: x.lower())
unit_selector = fill_selector("units", unit_list)

# function selectors, pre-baked
function_list = [f + "()" for f in functions]
function_list.extend(["using  ", "in  "])
function_selector = fill_selector("functions", function_list, backup=1)

# special symbol selector, pre-baked
symbol_list = ["μ", "π","ν％ℳ","ΔᵣG°′","αβγδεζησχ","∞∡ℏ","äöüßø", "ΓΘΛΦΨ"]
symbol_selector = fill_selector("symbols", symbol_list)

def quant_selectors(known):
    """ Make the selector for known quantities
    """
    choices = known.split("\n")
    return fill_selector("quantities", [term.rsplit("=",1)[0] for term in choices])

example_template = '''
<h3>How to use PQcalc</h3>
<p>PQcalc is an online calculator for students learning science in college.
To learn how to use it by example, click on any of the examples below, look at the
input, then press go and study the output. A more comprehensive documentation of
the program is  <a href="http://www.bioinformatics.org/pqcalc/manual">here</a>.
<h3>Example calculations</h3><pre>%s</pre>
'''


def helpform(mob):
    return example_template % exhtml

def newform(outp, logp, mem, known, log, mob, oneline, inputlog, prefill="", linespace="100%", logo=""):
    mem = "\n".join(mem)
    known = "\n".join(known)
    if not outp:
        logo = PQlogo
    mem = mem.replace('"', '&quot;')
    inputlog = inputlog.replace('"', '&quot;')
    logbook = log.replace('"', '&quot;') + "\n" + ("\n".join(logp)).replace('"', '&quot;')
    out = log.replace('&quot;', '"') + "\n".join(outp)
    keyb = "" if mob else 'class="keyboardInput"'
    selectors = quant_selectors(known)
    selectors = selectors + unit_selector + function_selector + symbol_selector
    rows = 3
    if prefill:
        prefill = exdict[prefill][:-2]
        rows =len(prefill.split("\n"))
    data = dict(output=out, memory=mem, rows=rows, selectors=selectors, logbook=logbook, keyboard=keyb,
                prefill=prefill, head=head, buttons=buttons, linespacing=linespace, logo=logo, inputlog=inputlog)
    if oneline and not prefill:
        return template_oneline % data
    return template % data


def printableLog(symbols, logbook, inputlog):
    known = "\n".join([s + "=" + symbols[s].__str__() for s in symbols])
    return printable_view % (known, inputlog, logbook)




head = '''<head>
<meta name="format-detection" content="telephone=no">
<meta name="viewport" content="width=device-width; initial-scale=0.8;">

<link rel="shortcut icon" href="/ico/favicon.ico">

<script type="text/javascript"
  src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
</script>
<script type="text/x-mathjax-config">
  MathJax.Hub.Config({ TeX: { extensions: ["mhchem.js"] }});
</script>

<script type="text/javascript">

function goToAnchor() {
  location.href = "#commands";
}

</script>


<script type="text/javascript">
<!--

function insertAtCaret(areaId,text,backup) {
    var txtarea = document.getElementById(areaId);
    var scrollPos = txtarea.scrollTop;
    var strPos = 0;
    var br = ((txtarea.selectionStart || txtarea.selectionStart == '0') ?
        "ff" : (document.selection ? "ie" : false ) );
    if (br == "ie") {
        txtarea.focus();
        var range = document.selection.createRange();
        range.moveStart ('character', -txtarea.value.length);
        strPos = range.text.length;
    }
    else if (br == "ff") strPos = txtarea.selectionStart;

    var front = (txtarea.value).substring(0,strPos);
    var back = (txtarea.value).substring(strPos,txtarea.value.length);
    txtarea.value=front+text+back;
    strPos = strPos + text.length - backup;
    if (br == "ie") {
        txtarea.focus();
        var range = document.selection.createRange();
        range.moveStart ('character', -txtarea.value.length);
        range.moveStart ('character', strPos);
        range.moveEnd ('character', 0);
        range.select();
    }
    else if (br == "ff") {
        txtarea.selectionStart = strPos;
        txtarea.selectionEnd = strPos;
        txtarea.focus();
    }
    txtarea.scrollTop = scrollPos;
}
</script>
<style>
@media all {
	.page-break	{ display: none; }
}

@media print {
	.page-break	{ display: block; page-break-before: always; }
}
</style>

</head>
'''

buttons = '''
<input type="button" value="+" onclick="insertAtCaret('commands','+',0);" />
<input type="button" value="-" onclick="insertAtCaret('commands','-',0);" />
<input type="button" value="*" onclick="insertAtCaret('commands',' * ',0);" />
<input type="button" value="/" onclick="insertAtCaret('commands',' / ',0);" />
<input type="button" value="^" onclick="insertAtCaret('commands','^',0);" />
<input type="button" value="()" onclick="insertAtCaret('commands','()', 1);" />
<input type="button" value="=" onclick="insertAtCaret('commands',' = ', 0);" />
<input type="button" value="[]" onclick="insertAtCaret('commands','[]', 1);" />
'''

rest ='''
'''

PQlogo = '''<table><tr><td>

   <img  src="data:image/gif;base64,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"
width="115" height="76">



    </td><td>
    <h3> <br> 1. Set up a problem <br> 2. Solve it and press "go" <br> 3. See the work and the results </h3>
    </td></tr></table><br>
'''

template = '''<html>
%(head)s
<body>

    %(logo)s
    <div style="line-height:%(linespacing)s">

            %(output)s
            <div class="page-break"></div>
            <form enctype="multipart/form-data" action="." method="post">
            <textarea autofocus rows="%(rows)d" cols="42" id="commands" name="commands" %(keyboard)s  type="number" autocapitalize="off"
              autocomplete="on" spellcheck="false" style="font-weight: bold; font-size: 12pt;"
              >%(prefill)s</textarea> <p>
            <input type="submit" name="sub" value="  go  ">

            %(selectors)s </p>
            %(buttons)s
            <input type="submit" name = "sub" value="export" />
            <input type="submit" name = "sub" value="reset" />
            <input type="submit" name = "sub" value="help" />

            <input type="hidden" name="memory" value = "%(memory)s"/>
            <input type="hidden" name="inputlog" value = "%(inputlog)s"/>
            <input type="hidden" name="logbook" value = "%(logbook)s"/>
    </div>
</body>
</html>
'''

template_oneline = '''<html>
%(head)s
<body onload="goToAnchor();">
<table>
    <tr><td><h1> PQCalc</h1></td><td>
    <h3> : a scientific calculator that keeps track of units and uncertainties of physical quantities</h3>
    </td></tr></table>
<table width=100%% cellspacing="2" cellpadding="10">

    <tr>
        <td width=100%% valign="top" style="border-width:6;border-color:#1132FF;border-style:ridge">
            %(output)s
            <form enctype="multipart/form-data" action="." method="post">
            <input type="text" autofocus size="50" id="commands" name="commands" %(keyboard)s  autocapitalize="off"
              autocomplete="off" spellcheck="false" style="font-weight: bold; font-size: 12pt;">
            <input type="submit" name="sub" value="  go  ">
            <p>
            <a name="myAnchor" ></a>
            %(buttons)s
            <input type="submit" name = "sub" value="print" />
            <input type="submit" name = "sub" value="reset" />
            <input type="submit" name = "sub" value="help" />
            </p>
            %(selectors)s
            <input type="hidden" name="memory" value = "%(memory)s"/>
            <input type="hidden" name="inputlog" value = "%(inputlog)s"/>
            <input type="hidden" name="logbook" value = "%(logbook)s"/>

</body>
</html>
'''



printable_view = '''<html>
<head>
<meta name="format-detection" content="telephone=no">

<script type="text/javascript"
  src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
</script>
<script type="text/x-mathjax-config">
  MathJax.Hub.Config({ TeX: { extensions: ["mhchem.js"] }});
</script>
</head>
<body>Calculation done with PQCalc, the physical quantity calculator<br>
that knows about quantities, units and uncertainties.<br><br>
by Karsten Theis, Chemical and Physical Sciences, Westfield State University<br>
inquiries and bug reports to ktheis@westfield.ma.edu<br><br>
Program currently hosted at
<a href="http://www.bioinformatics.org/pqcalc">
bioinformatics.org/PQCalc </a> and
<a href="http://ktheis.pythonanywhere.com/">
http://ktheis.pythonanywhere.com/ </a>
<h2> Known quantities </h2>
<PRE>%s</PRE>
<h2> Input </h2>
<PRE>%s</PRE>

<h2> Log of the calculation </h2>
%s
</div>
</body>
</html>
'''

example = '''problem = 1.71
0.6274*1.00e3/(2.205*2.54^3)
a_textbook = 17.4

problem = Units
t1 = 180 s
t2 = 4 min
t_sum = t1 + t2

problem = SigFigs Multiply
a_3sigfig = 2.63
a_5sigfig = 2.6300
b_4sigfig = 0.3128
c_less = a_3sigfig * b_4sigfig
c_more = a_5sigfig * b_4sigfig

problem = SigFigs Add
a_3sigfig = 2.63
a_5sigfig = 2.6300
b_4sigfig = 0.3128
c_less = a_3sigfig + b_4sigfig
c_more = a_5sigfig + b_4sigfig

problem = Addition
a = 5.1 s
b = 3.4 s
c = a + b

problem = division
# 12.05 mol of dry ice have a mass of 530.4 g.
# What is the molar mass of [CO2]?
m[CO2] = 530.4 g
n[CO2]=12.05 mol
ℳ[CO2] = m[CO2] /  n[CO2]

problem = 4.111
V_Analyte = 100.0 mL
V_Titrant = 3.19 mL
c_Titrant = 0.0250 M
# 1:1 stochiometry...
c_Analyte = c_Titrant * V_Titrant / V_Analyte
#answer: c_Analyte =7.98e-4 M

problem = GenChem constants
R = 8.314 J/(mol K)
T_room = 293.15 K
P_atm = 1 atm
q_e = 1.602176E-19 C
c0 = 299792458 m/s
F = 96485.33 C/mol
M_H = 1.08 g/mol
M_C = 12.011 g/mol
M_O = 15.999 g/mol
M_Na = 22.9897 g/mol
M_Cl = 35.45g/mol
M_N = 14.007 g/mol
N_A = 6.02214E23 /mol

problem = languages
# Chemical equation
# 化学方程式
# Химическое уравнение
# 化学反応式
# Reaktionsgleichung
# 화학반응식
# Ecuación química
# إنشاء حسابد خول
# Równanie reakcji
# Phương trình hóa học
! O2(g) + 2H2(g) -> 2H2O(g)


problem = 1.87
percent = 1/100
year = 365 * 24 h
input_Fertilizer = 1500. kg / year
input_N = 10 percent * input_Fertilizer
wash_N = 15 percent * input_N
flow_stream = 1.4 m^3/min
[N]added = wash_N / flow_stream
[N]added using mg L
a_textbook = 0.031 mg/L

problem = 1.96
pi = 3.14159265
d_gasoline = 0.73 g/mL
d_water = 1.00 g/mL
diameter = 3.2 cm
radius = diameter / 2
m_water = 34.0 g
m_gasoline = 34.0 g
V_water = m_water / d_water
V_gasoline = m_gasoline / d_gasoline
V_total = V_water + V_gasoline
h_total = V_total / (radius^2 * pi)

#######
problem = 3.91

#given
m[CxHy] = 135.0 mg
m[CO2] = 440.0 mg
m[H2O] = 135.0 mg
M[CxHy] = 270.0 g/mol

#calculated from chemical formula
M[C] = 12.0107 g/mol
M[O] = 15.9994 g/mol
M[H] = 1.00794 g/mol
M[CO2] = M[C] + 2 * M[O]
M[H2O] = 2 * M[H] + M[O]
#<div class="page-break"></div>
#calculation
n[CO2] = m[CO2] / M[CO2]
n[C] = n[CO2]
n[H2O] = m[H2O] / M[H2O]
n[H] = n[H2O]*2
n[CxHy] = m[CxHy] / M[CxHy]
ratio[nuC:nuH] = n[C] / n[H]

# _M[CxHy] = _M[C] * _nuC + _M[H] * _nuH = _M[C] * _ratio[nuC:nuH] _nuH + _M[H] * _nuH
# _M[CxHy] = _nuH * (_M[C] * _ratio[nuC:nuH] + _M[H] )
nuH = M[CxHy] / (M[C] * ratio[nuC:nuH] + M[H])
nuC = ratio[nuC:nuH] * nuH
#texbook answer: [C20H30]

######
problem = 3.103

# If 2.50 g of [KO2] react with
# 4.50 g of [CO2], how much dioxygen
# will form (together with [K2CO3])?
m[KO2] = 2.50 g
m[CO2] = 4.50 g
! 4KO2 + 2CO2 -> 3O2 + 2K2CO3
ν[KO2] = 4
ν[CO2] = 2
ν[O2] = 3

#calculate M from chemical formula
__skip__=1
M[C] = 12.0107 g/mol
M[O] = 15.9994 g/mol
M[K] = 39.0983 g/mol

M[KO2] = M[K] + 2 * M[O]
M[CO2] = M[C] + 2 * M[O]

#calculation
__skip__=0
n[KO2] = m[KO2] / M[KO2]
n[CO2] = m[CO2] / M[CO2]

n[KO2 -> lim] = n[KO2] / ν[KO2]
n[CO2 -> lim] = n[CO2] / ν[CO2]

n[lim] = minimum(n[KO2 -> lim], n[CO2 -> lim])
V[O2] = n[lim] ν[O2] 8.314 J/(K mol) 298 K / 1 atm
V[O2] using L
m[O2] = n[lim] ν[O2] * 2 * M[O]
# textbook : _m[O2] = 0.844 g



problem = 6.87
# What is the density of radon at 298 K and 1 atm?
T = 298 K
P = 1.00 atm
R = 8.314 J / (mol K)
R using atm L
M_Rn = 222. g / mol
# Consider _n_Rn  = 1 mol
# Any other value would give the same result...
n_Rn = 1 mol
V0 = n_Rn * R T / P
m0 = n_Rn M_Rn
ρ = m0 / V0


problem = 17.27
[H+] = 3.45e-8 M
pH = -log([H+]/1 M)
#answer =
######

problem = 17.49
K_a = 1.80e-4
c = 0.0600 M
# K_a = x^2/(0.06-x) <=> x^2 + x K_a - 0.06 K_a c/M = 0
# solve quadratic: either quadp or quadn gives physically sensible answer
A_ = 1
B_ = K_a
C_ = - K_a c / 1 M
xp = quadp(A_, B_, C_)
xn = quadn(A_, B_, C_)

pH = -log(xn)
# using the approximation that c[AH] = c[total]
pH = -1/2 log(c / M K_a)
######

problem = 16.115

K1 = 4.10e-4
T1 = CtoKscale(2000.)
T2 = CtoKscale(25.)
ΔH  = 180.6 kJ/mol
R = 8.314 J/(mol K)
# ln(_K2 / _K1) = -ΔH/R (1/_T2 - 1/_T1)
K2 = K1 exp(-ΔH/R (1/T2 - 1/T1))
######
problem = made.up
T = 298.0 K
R = 8.314 J/(mol K)
K_eq = 2.54e6
ΔG° = - R T ln(K_eq)

problem = first semester
5 + 3
__tutor__ = 1
6 + 8
R_gas = 0.08205746(14) L atm K^-1 mol^-1
R_ryd = 1.0973731568539(55)e7 m^-1

problem = practice units
__hideunits__ = 1
R = 8.3144621(75) J/(K mol)
T = 298.0 K
K_eq = 2.54e6
ΔG° = - R T ln(K_eq)


problem = second semester
R = 8.3144621(75) J/(K mol)
T = 298.0 K
K_eq = 2.54e6
ΔG° = - R T ln(K_eq)

problem = physical chemistry
__showuncert__= 1

# gas constant
R =  8.3144621(75) J/(K mol)
# Boltzmann constant
k_B = 1.3806488(13)e-23 J/K
# Plank constant
h = 6.62606957(29)e-34 J s
# Speed of light (nowadays not a measurement, but a definition)
c0 = 299792458 m/s
# Mathematical constant Pi to 17 digits
π = 3.1415926535897932
# Permeability in vacuum
μ0 = 4 N A^-2 π / 10000000
# Permittivity in vacuum
ε0 = 1 / (c0^2 μ0)
# mass of electron
m_elec= 9.10938215(45)e-31kg
# Elementary charge
e = 1.60217657e-19 C
# Rydberg constant from first principles
R_H = m_elec e^4 / (8 h_^3 ε0^2 c0)
#Bohr radius to check
ħ = h_ / (2π)
a0 = 4 π ε0 ħ^2 /(m_elec e^2)

problem = R_units
R = 8.314 Pa m^3/(mol K)
R2 = R / (101325 Pa * 1 m^3) * 1 atm * 1000 L
R3 = R * 1 atm * 1000 L / (101325 Pa * 1 m^3)
R4 = R * (1 atm / 101325 Pa) * (1000 L / 1 m^3)
P = 1 atm
P using Pa

problem = concentration
# Titration of KOH with [H2SO4] to equivalence point
# Given:
V[KOH] = 5.00 mL
[H2SO4] = 0.100 M
V[H2SO4] = 34.5 mL
# Plan: 1) _n[H2SO4] via c=n/V,
#       2) _n[KOH] via coefficients,
#       3) _[KOH] via c=n/V
n[H2SO4] = [H2SO4] * V[H2SO4]
!H2SO4 + 2 KOH -> 2 H2O + 2 K+ + 2 SO4^2-
n[KOH] = n[H2SO4] / 1 * 2
[KOH]original = n[KOH] / V[KOH]


problem = showcase chemistry markup
# Limiting reagent problem
# The balanced reaction is:
! H2SO4 + 2 KOH -> 2 H2O + 2 K+ + 2 SO4^2-
# Given:
n[H2SO4]start = 3.4 mmol
n[KOH]start = 7.4 mmol
n[->] = minimum(n[H2SO4]start/1, n[KOH]start/2)
n[H2SO4]end = n[H2SO4]start - 1 * n[->]
n[KOH]end = n[KOH]start - 2 * n[->]

problem = J Chem Ed 2012, 89, 326−334
#   0.564 grams of [AgNO3] is dissolved in 25.00 mL of 0.250 molar [BaCl2].
#   A precipitate forms and is isolated and weighed.
#   Its mass is 0.392 grams.
#   What is the percent yield of the reaction?
m[AgNO3]= 0.564 g
V[BaCl2 sol] = 25.00 mL
c[BaCl2] = 0.250 M
m_prec= 0.392 g
#   Plan:
#      1) Nature of precipitate
#      2) Find limiting reagent
#      3) Calculate yield!
#
#   1) Nature of precipitate
! BaCl2(s) -> Ba^2+(aq) + 2 Cl- (aq)
! AgNO3(s) -> Ag+(aq) + NO3- (aq)
#   [AgNO3], [BaCl2], and [Ba(NO3)2] are soluble, [AgCl] isn't
#
#   2) Find limiting reagent
#      First, need a balanced chemical equation
! 2AgNO3 + BaCl2 -> 2AgCl(s) + Ba^2+ + 2 NO3-
#      Try either reagent in excess and see which gives least product
#        Case A: [AgNO3] limiting and [BaCl2] in excess
M[AgNO3] = 169.87 g/mol
n[AgNO3] = m[AgNO3] / M[AgNO3]
#            [AgNO3] and [AgCl] at equimolar ratio
n[AgCl]A = n[AgNO3]
#        Case B: [AgNO3] in excess and [BaCl2] limiting
n[BaCl2] = c[BaCl2] V[BaCl2 sol]
#          [BaCl2] and [AgCl] at 1:2 molar ratio
n[AgCl]B = n[BaCl2] * 2
#     _n[AgCl]A is smaller than _n[AgCl]A , so [AgNO3] is limiting
#
#   3) Calculate yield
M[AgCl] = 143.32 g/mol
m[AgCl]theoretical = n[AgCl]A * M[AgCl]
m[AgCl]actual = m_prec
yield = m[AgCl]actual / m[AgCl]theoretical

problem = error in adding
a = 5.6 km + 25.1 mol

problem = error in power
a = 5.6 ^ (25 mol)

problem = error in division
a = 5.6 / 0.0

problem = error with parentheses
a = (5 + 6))

problem = error in minimum function
a = minimum(7 M, 34 mol)

problem = limitations: numeric overflow
a = 10^10^10

problem = error in square root
#This works
a = sqrt(2.3 mm * 4.9 km)
#This doesn't
a = sqrt(2.3 mm * 4.13 g)

problem = limitations: imaginary numbers
#PQcalc works with real numbers, only
a = sqrt(-1)

problem = error in log function
a = log(0.34 mol/L)

problem = error in log function
a = log(-23.8)

problem = tutorial
# You are asked to make about 80 mL of a 0.150 mol/L aqueous solution of magnesium chloride by mixing the pure solid with water.
V_requested = 80 mL

[MgCl2] = 0.150 mol/L

# First, calculate how much [MgCl2] you need.
n[MgCl2] = [MgCl2] V_requested

# Because we want to use a balance to measure the pure solid, we need to calculate the mass from the chemical amount.

M[MgCl2] = 95.211 g/mol

m[MgCl2]exact = n[MgCl2] M[MgCl2]

# You took a bit more than the required mass and placed 1.213 g of [MgCl2] into a 100 mL graduated cylinder.
#
# To which volume do you have to add water to obtain a 0.150 M solution?

V_exact = m[MgCl2]exact / (M[MgCl2] [MgCl2] )

m[MgCl2]actual = 1.213g

V_actual = m[MgCl2]actual / (M[MgCl2] [MgCl2])


# Another, simpler way of calculating: Instead of 1.143 g, you have 1.213 g, so you have to add more  water to obtain a proportionally larger volume

V_made_2 = V_exact * m[MgCl2]actual / m[MgCl2]exact

problem = integrate images

#How does water form from the elements, and what is the chemical equation?
#{"http://bit.ly/1PvpnpD" width ="160"}
!H2 + O2 -> 2H2O

'''

examples = example.split('problem = ')
from collections import OrderedDict


exdict = OrderedDict()
exhtml = []
for ex in examples:
    if "\n" not in ex:
        continue
    head2, prob = ex.split("\n", 1)
    exhtml.append('<a href="/example%s">Example %s</a><br>' % (head2, head2))
    exhtml.append("<pre>%s</pre>" % prob)
    exdict[head2] = prob

exhtml = "".join(exhtml)
