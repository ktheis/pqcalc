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
function_list.extend(["using", "in "])
function_selector = fill_selector("functions", function_list, backup=1)


def quant_selectors(known, mob):
    """ Make the selector for the left (what's next) box and the selector for the right (knowns) box
    """
    choices = known.split("\n")
    if mob:
        return "<br>".join(choices), fill_selector("quantities", choices)
    html = ['<option value="" selected="selected" disable="disabled">Click to use for next calculation</option>']
    for term in choices:
        sym = term.split("=")[0]
        html.append(selectoroption % (sym, term))
    return selector % ("size = 8", 0, "".join(html)), ""


def newform(outp, logp, mem, known, log, mob, prefill=""):
    mem = "\n".join(mem)
    known = "\n".join(known)
    logbook = log + "\n" + "\n".join(logp)
    out = "\n".join(outp)
    if mob:
        keyb = ""
        if mob == "ipod" and out:
            out = calculationtempl % out
    else:
        keyb = 'class="keyboardInput"'
    knownbox, selectors = quant_selectors(known, mob)
    if not known:
        knownbox = " -- nothing yet -- "
    selectors = selectors + unit_selector + function_selector + "<br>"
    if prefill:
        prefill = exdict[prefill]
    data = dict(output=out, memory=mem, known=knownbox, selectors=selectors, logbook=logbook, keyboard=keyb, prefill=prefill, head=head, buttons=buttons)
    if mob == "ipod":
        data["head"] = headipod
        return templateipod % data
    else:
        return template % data + "<h3>Example calculations</h3><pre>%s</pre>" % exhtml


def printableLog(symbols, symbollist, logbook):
    known = "\n".join([s + "=" + symbols[s].__str__() for s in symbollist])
    return printable_view % (known, logbook)


example = '''problem = 1.71
0.6274*1.00e3/(2.205*2.54^3)
a_textbook = 17.4

problem = 1.87
percent = 0.010000000
year = 365 * 24 hr
input_Fertilizer = 1500. kg / year
input_Nitrogen = input_Fertilizer * 10 percent
wash_Nitrogen = input_Nitrogen * 15 percent
flow_stream = 1.4 m^3/min
c[added nitrogen] = wash_Nitrogen / flow_stream
c[added nitrogen] using mg L
a_textbook = 0.031 mg/L

######
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
#calculation
n[CO2] = m[CO2] / M[CO2]
n[C] = n[CO2]
n[H2O] = m[H2O] / M[H2O]
n[H] = n[H2O]*2
n[CxHy] = m[CxHy] / M[CxHy]
ratio[nuC:nuH] = n[C] / n[H]

# M[CxHy] = M[C] * nuC + M[H] * nuH = M[C] * ratio[nuC:nuH] nuH + M[H] * nuH
# M[CxHy] = nuH * (M[C] * ratio[nuC:nuH] + M[H])
nuH = M[CxHy] / (M[C] * ratio[nuC:nuH] + M[H])
nuC = ratio[nuC:nuH] * nuH
#texbook answer: C20H30

######

problem = 3.103
m[KO2] = 2.50 g
m[CO2] = 4.50 g
ratio[nKO2:nO2] = 4/3
ratio[nCO2:nO2] = 2/3

#calculated from chemical formula
M[C] = 12.0107 g/mol
M[O] = 15.9994 g/mol
M[K] = 39.0983 g/mol

M[KO2] = M[K] + 2 * M[O]
M[CO2] = M[C] + 2 * M[O]

#calculation
n[KO2] = m[KO2] / M[KO2]
n[CO2] = m[CO2] / M[CO2]

n[O2 if KO2 were limiting] = n[KO2] / ratio[nKO2:nO2]
n[O2 if CO2 were limiting] = n[CO2] / ratio[nCO2:nO2]

n[O2] = minimum(n[O2 if KO2 were limiting],n[O2 if CO2 were limiting])
V[O2] = n[O2] 8.314 J/(K mol) 298 K / 1 atm
V[O2] using L
m[O2] = n[O2] * 2 * M[O]
#textbook : m[O2] = 0.844 g
######

problem = 4.111
V_An = 100.0 mL
V_Ti = 3.19 mL
c_Ti = 0.0250 M
# 1:1 stochiometry...
c_An = c_Ti * V_Ti / V_An
#answer:
######
problem = 6.87
T = 298 K
p = 1.00 atm
R = 8.314 J / (mol K)
M_Rn = 222. g / mol
n_Rn = 1 mol
#This is arbitrary,
#it cancels out in the end
V0 = n_Rn * R T / p
m0 = n_Rn M_Rn
d = m0 / V0
######

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

pH = -log(xp)
# using the approximation that c[AH] = c[total]
pH = -1/2 log(c / M K_a)
######

problem = 16.115

K1 = 4.10e-4
T1 = CtoKscale(2000.)
T2 = CtoKscale(25.)
DeltaH  = 180.6 kJ/mol
R = 8.314 J/(mol K)
# ln(K2/K1) = -DeltaH/R (1/T2 - 1/T1)
K2 = K1 exp(-DeltaH/R (1/T2 - 1/T1))
######
problem = made.up
T = 298.0 K
R = 8.314 J/(mol K)
K_eq = 2.54e6
DeltaGnaught = - R T ln(K_eq)
'''

examples = example.split('problem = ')
exdict = {}
exhtml = []
for ex in examples:
    if "\n" not in ex:
        continue
    head, prob = ex.split("\n", 1)
    exhtml.append('<a href="/example%s">Example %s</a><br>' % (head, head))
    exhtml.append("<pre>%s</pre>" % prob)
    exdict[head] = prob

exhtml = "".join(exhtml)

headipod = '''<head>
<meta name="format-detection" content="telephone=no">

<link rel="stylesheet" type="text/css" href="/css/keyboard.css" media="all" />
<script type="text/javascript" src="/js/keyboard.js" charset="UTF-8"></script>

<script type="text/javascript"
  src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
</script>

<script type="text/javascript">
<!--
function insertAtCaret(thisChar, thereId, backup) {
	function theCursorPosition(ofThisInput) {
		// set a fallback cursor location
		var theCursorLocation = 0;

		// find the cursor location via IE method...
		if (document.selection) {
			ofThisInput.focus();
			var theSelectionRange = document.selection.createRange();
			theSelectionRange.moveStart('character', -ofThisInput.value.length);
			theCursorLocation = theSelectionRange.text.length;
		} else if (ofThisInput.selectionStart || ofThisInput.selectionStart == '0') {
			// or the FF way
			theCursorLocation = ofThisInput.selectionStart;
		}
		return theCursorLocation;
	}

	// now get ready to place our new character(s)...
	var theIdElement = document.getElementById(thereId);
	var currentPos = theCursorPosition(theIdElement);
	var origValue = theIdElement.value;
	var newValue = origValue.substr(0, currentPos) + thisChar + origValue.substr(currentPos);

	theIdElement.value = newValue;

}

</script>

</head>
'''

head = '''<head>
<meta name="format-detection" content="telephone=no">

<link rel="stylesheet" type="text/css" href="/css/keyboard.css" media="all" />
<script type="text/javascript" src="/js/keyboard.js" charset="UTF-8"></script>

<script type="text/javascript"
  src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
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
'''

template = '''<html>
%(head)s
<body>
<table>
    <tr><td><h1> PQCalc</h1></td><td>
    <h3> : a scientific calculator that keeps track of units and significant figures of physical quantities</h3>
    </td></tr></table>
<table width=100%% cellspacing="2" cellpadding="10">
    <tr>
        <td width=50%% valign="top" style="border-width:6;border-color:#1132FF;border-style:ridge">
            <h2>What's next?</h2>
            %(selectors)s
            %(buttons)s
            <form enctype="multipart/form-data" action="." method="post">
            <textarea rows="6" cols="30" id="commands" name="commands" %(keyboard)s  type="number" autocapitalize="off"
              autocomplete="off" spellcheck="false" style="font-weight: bold; font-size: 12pt;"
              >%(prefill)s</textarea><p><input name="sub" value="calculate" type="submit">
            <input type="submit" name = "sub" value="start over" />
            <input type="submit" name = "sub" value="printable view" /> </p>
            <input type="hidden" name="memory" value = "%(memory)s"/>
            <input type="hidden" name="logbook" value = "%(logbook)s"/>
            </td>
        <td  valign="top" style="border-width:6;border-color:#FFBD32;border-style:ridge">
            <h2> Known quantities </h2>
            <div style="height:150px;width:280px;overflow:auto;">
            %(known)s
            </div>
            </td>
        </tr>
    <tr><td colspan = 2 valign="top" style="width:100%%;border-width:6;border-color:#BBFF32;border-style:ridge">
        <h2> Calculation log </h2>
        <script type="text/javascript">
            function scrollDiv()
            {
            var el;
            if ((el = document.getElementById('log'))
            && ('undefined' != typeof el.scrollTop))
            {
            el.scrollTop = 0;
            el.scrollTop = 5000;
            }
            }

            window.onload = scrollDiv;

            </script>
        <div id="log" style="width=100%%;overflow:auto;">
        %(output)s
        </div>
        </td>
    </tr>
</table>

</body>
</html>
'''

calculationtempl = '''<tr>
<td valign="top" style="border-width:6;border-color:#BBFF32;border-style:ridge">
<h2> Calculation log </h2>
<script type="text/javascript">
function scrollDiv()
{
var el;
if ((el = document.getElementById('log'))
&& ('undefined' != typeof el.scrollTop))
{
el.scrollTop = 0;
el.scrollTop = 5000;
}
}

window.onload = scrollDiv;

</script>
<div id="log" style="overflow:auto;">
%s
</div>
</td>
</tr>
'''


templateipod = '''<html>
%(head)s
<body>
<h1> PQCalc ipod</h1>
<table cellspacing="2" cellpadding="10">
    %(output)s
    <tr><td valign="top" style="border-width:6;border-color:#1132FF;border-style:ridge">
        <h2>What's next?</h2>
        %(selectors)s <br>
        %(buttons)s
        <form enctype="multipart/form-data" action="." novalidate method="post">
        <input id="commands" name="commands" size="35" %(keyboard)s  type="email" autocapitalize="off" autocomplete="off" autocorrect="off" spellcheck="false"
        tyle="font-weight: bold; font-size: 12pt;">%(prefill)s</textarea><p><input name="sub" value="calculate" type="submit">
        <input type="submit" name = "sub" value="start over" />
        <input type="submit" name = "sub" value="printable view" /> </p>
        <input type="hidden" name="memory" value = "%(memory)s"/>
        <input type="hidden" name="logbook" value = "%(logbook)s"/>
        </td></tr>
    <tr><td  valign="top" style="border-width:6;border-color:#FFBD32;border-style:ridge">
        <h2> Known quantities </h2>
        <div style="overflow:auto;">
        %(known)s
        </div>
        </td></tr>
    </table>
</body>
</html>
'''

printable_view = '''<html>
<body>Calculation done with PQCalc, the physical quantity calculator<br>
that knows about quantities, units and significant figures.<br><br>
by Karsten Theis, Chemical and Physical Sciences, Westfield State University<br>
inquiries and bug reports to ktheis@westfield.ma.edu<br><br>
Program currently hosted at
<a href="http://www.bioinformatics.org/pdbtools/PQCalc">
bioinformatics.org/pdbtools/PQCalc </a> and
<a href="http://ktheis.pythonanywhere.com/">
http://ktheis.pythonanywhere.com/ </a>
<h2> Known quantities </h2>
<PRE>%s</PRE>

<h2> Log of the calculation </h2>
<PRE>%s</PRE>
</div>
</body>
</html>
'''
