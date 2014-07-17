__author__ = 'Karsten Theis'

import unittest
import quantities
from quantities import number2quantity, uncert_sum, Q, try_all_derived, Units

class Number2quantity_TestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_expo(self):
        q = number2quantity("2.51e89")
        self.assertEqual(q.sigfig, 3,
                         'incorrect sigfig')

    def test_greater1(self):
        q = number2quantity("4.513")
        self.assertEqual(q.sigfig, 4,
                         'incorrect sigfig')

    def test_dotatend(self):
        q = number2quantity("1000.")
        self.assertEqual(q.sigfig, 4,
                         'incorrect sigfig')

    def test_integer(self):
        q = number2quantity("50000")
        self.assertEqual(q.sigfig, 100,'incorrect sigfig')

class uncert_sum_TestCase(unittest.TestCase):
    def setUp(self):
        self.q1 = number2quantity("5.1")
        self.q2 = number2quantity("0.143")
        self.q3 = number2quantity("0.35")
        self.q4 = self.q3 * quantities.unitquant["g"]

    def test_add23(self):
        n = self.q2.number + self.q3.number
        self.assertEqual(uncert_sum(n, self.q2, self.q3)[1] , 2,
                         'incorrect sigfig')

    def test_add13(self):
        n = self.q1.number + self.q3.number
        self.assertEqual(uncert_sum(n, self.q1, self.q3)[1] , 2,
                         'incorrect sigfig')


class addition_TestCase(unittest.TestCase):
    def setUp(self):
        self.q1 = Q("5.1")
        self.q2 = Q("0.143")
        self.q3 = Q("0.35")
        self.q4 = self.q3 * Q("g")

    def test_incompatibe_units(self):
        with self.assertRaises(quantities.QuantError):
            a = self.q1 + self.q4

    def test_adding_integer(self):
        q14 = Q(1)+Q(4)
        q5 = Q(5)
        self.assertEqual(q14.number, q5.number)
        self.assertEqual(q14.sigfig, q5.sigfig)
        self.assertEqual(q14.units, q5.units)
        self.assertNotEqual(q14.name, q5.name)
        self.assertNotEqual(q14.provenance, q5.provenance)

class try_all_derived_TestCase(unittest.TestCase):
    def test_LiterJoule1(self):
        query = list(try_all_derived(Units(kg=1,m=4),dict(L=0,J=0)))
        result = [(-13, 'J', -1), (-1, 'J', 1), (-9, 'L', -1), (3, 'L', 1)]
        self.assertEqual(query, result)
    def test_LiterJoule2(self):
        query = list(try_all_derived(Units(kg=1,m=4),dict(L=1,J=0)))
        result = [(-13, 'J', -1), (-1, 'J', 1), (3, 'L', 1)]
        self.assertEqual(query, result)

if __name__ == '__main__':
    unittest.main(verbosity=110)

