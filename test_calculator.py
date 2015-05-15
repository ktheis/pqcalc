__author__ = 'Karsten Theis'

import unittest
import calculator
from calculator import scan, make_paired_tokens, fixoperator


class Classify_TestCase(unittest.TestCase):

    def test_calculation(self):
        pass

class Scan_TestCase(unittest.TestCase):

    def test_numbers(self):
        t = scan("5 + 7")
        s = [('N', '5'), ('O', '+'), ('N', '7'), ('O', ''), ('Z', '')]
        self.assertEqual(t, s, 'problem scanning pure numbers')


    def test_quantities(self):
        t = scan("5. km / 3. s")
        s = [('N', '5.'), ('O', ''), ('U', 'km'), ('O', '/'), ('N', '3.'), ('O', ''), ('U', 's'), ('O', ''), ('Z', '')]
        self.assertEqual(t, s, 'problem scanning quantities')


    def test_symbols(self):
        t = scan("a + b")
        s = [('I', 'a'), ('O', '+'), ('I', 'b'), ('O', ''), ('Z', '')]
        self.assertEqual(t, s, 'problem scanning symbols')


    def test_functions(self):
        t = scan("log(10)")
        s = [('F', 'log'), ('O', '('), ('N', '10'), ('O', ')'), ('Z', '')]
        self.assertEqual(t, s, 'problem scanning functions')


    def test_comment(self):
        t = scan("42 # the meaning of life")
        s = [('N', '42'), ('O', ''), ('C', '# the meaning of life'), ('Z', '')]
        self.assertEqual(t, s, 'problem scanning comments')


    def test_combo(self):
        t = scan("sqrt(5.0 cm^2 / (2 Pi))")
        s = [('F', 'sqrt'), ('O', '('), ('N', '5.0'), ('O', ''), ('U', 'cm'), ('O', '^'),
             ('N', '2'), ('O', '/ ('), ('N', '2'), ('O', ''), ('I', 'Pi'), ('O', '))'), ('Z', '')]
        self.assertEqual(t, s, 'problem scanning combos')


    def test_mangled(self):
        with self.assertRaises(calculator.CalcError):
            scan("5 + [[")


class Paired_Tokens_TestCase(unittest.TestCase):

    def test_implied_multiplication(self):
        t = make_paired_tokens(scan("5 7"))
        s = [['N', '*', '5'], ['N', '*', '7'], ['Z', '*', '']]
        self.assertEqual(t, s, 'problem with implied multiplication')

    def test_functions(self):
        t = make_paired_tokens(scan("log(7)"))
        s = [['N', '*', '5'], ['N', '*', '7'], ['Z', '*', '']]
        self.assertEqual(t, s, 'problem with function calls')

    def test_comments(self):
        t = make_paired_tokens(scan("5 + 6 # + 56"))
        s = [['N', '*', '5'], ['N', '+', '6'], ['Z', '*', '']]
        self.assertEqual(t, s, 'problem with comments')

class Fixoperator_TestCase(unittest.TestCase):

    def test_implicit_multiplication(self):
        t = fixoperator(" ",[])
        s = ' *'
        self.assertEqual(t, s, 'problem with implied multiplication')

    def test_parentheses(self):
        t = fixoperator("(",[])
        s = '*('
        self.assertEqual(t, s, 'problem with parentheses')

    def test_function_call(self):
        t = fixoperator("(",[('F', '*', 'log')])
        s = '('
        self.assertEqual(t, s, 'problem with function call')

'''
interpret_N_U_cluster(["Q('8.314')"],make_paired_tokens(scan("8.314 J/(mol K) * 274 K"))[1:],[])

a = make_paired_tokens(scan("8.314 J/(mol K) * 274 K"))
interpret_N_U_cluster(["Q('8.314')"],a[1:],[])

>>> scan("5 + 7")
[['N', '5'], ['O', '+'], ['N', '7'], ['O', ''], ['Z', '']]
>>> scan("5. m / 3. s")
[['N', '5.'], ['O', ''], ('U', 'm'), ['O', '/'], ['N', '3.'], ['O', ''], ('U', 's'), ['O', ''], ['Z', '']]

    '''