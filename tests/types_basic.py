#!/usr/bin/env python
#
# types_basic.py - tests for basic types conversions
#
# Copyright (C) 2004-2010 Federico Di Gregorio  <fog@debian.org>
#
# psycopg2 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# In addition, as a special exception, the copyright holders give
# permission to link this program with the OpenSSL library (or with
# modified versions of OpenSSL that use the same license as OpenSSL),
# and distribute linked combinations including the two.
#
# You must obey the GNU Lesser General Public License in all respects for
# all of the code used other than OpenSSL.
#
# psycopg2 is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.

try:
    import decimal
except:
    pass
import sys
import testutils
from testutils import unittest
from testconfig import dsn

import psycopg2
from psycopg2.extensions import b


class TypesBasicTests(unittest.TestCase):
    """Test that all type conversions are working."""

    def setUp(self):
        self.conn = psycopg2.connect(dsn)

    def tearDown(self):
        self.conn.close()

    def execute(self, *args):
        curs = self.conn.cursor()
        curs.execute(*args)
        return curs.fetchone()[0]

    def testQuoting(self):
        s = "Quote'this\\! ''ok?''"
        self.failUnless(self.execute("SELECT %s AS foo", (s,)) == s,
                        "wrong quoting: " + s)

    def testUnicode(self):
        s = u"Quote'this\\! ''ok?''"
        self.failUnless(self.execute("SELECT %s AS foo", (s,)) == s,
                        "wrong unicode quoting: " + s)

    def testNumber(self):
        s = self.execute("SELECT %s AS foo", (1971,))
        self.failUnless(s == 1971, "wrong integer quoting: " + str(s))
        s = self.execute("SELECT %s AS foo", (1971L,))
        self.failUnless(s == 1971L, "wrong integer quoting: " + str(s))
        if sys.version_info[0:2] < (2, 4):
            s = self.execute("SELECT %s AS foo", (19.10,))
            self.failUnless(abs(s - 19.10) < 0.001,
                        "wrong float quoting: " + str(s))

    def testBoolean(self):
        x = self.execute("SELECT %s as foo", (False,))
        self.assert_(x is False)
        x = self.execute("SELECT %s as foo", (True,))
        self.assert_(x is True)

    def testDecimal(self):
        if sys.version_info[0:2] >= (2, 4):
            s = self.execute("SELECT %s AS foo", (decimal.Decimal("19.10"),))
            self.failUnless(s - decimal.Decimal("19.10") == 0,
                            "wrong decimal quoting: " + str(s))
            s = self.execute("SELECT %s AS foo", (decimal.Decimal("NaN"),))
            self.failUnless(str(s) == "NaN", "wrong decimal quoting: " + str(s))
            self.failUnless(type(s) == decimal.Decimal, "wrong decimal conversion: " + repr(s))
            s = self.execute("SELECT %s AS foo", (decimal.Decimal("infinity"),))
            self.failUnless(str(s) == "NaN", "wrong decimal quoting: " + str(s))
            self.failUnless(type(s) == decimal.Decimal, "wrong decimal conversion: " + repr(s))
            s = self.execute("SELECT %s AS foo", (decimal.Decimal("-infinity"),))
            self.failUnless(str(s) == "NaN", "wrong decimal quoting: " + str(s))
            self.failUnless(type(s) == decimal.Decimal, "wrong decimal conversion: " + repr(s))
        else:
            return self.skipTest("decimal not available")

    def testFloatNan(self):
        try:
            float("nan")
        except ValueError:
            return self.skipTest("nan not available on this platform")

        s = self.execute("SELECT %s AS foo", (float("nan"),))
        self.failUnless(str(s) == "nan", "wrong float quoting: " + str(s))
        self.failUnless(type(s) == float, "wrong float conversion: " + repr(s))

    def testFloatInf(self):
        try:
            self.execute("select 'inf'::float")
        except psycopg2.DataError:
            return self.skipTest("inf::float not available on the server")
        except ValueError:
            return self.skipTest("inf not available on this platform")
        s = self.execute("SELECT %s AS foo", (float("inf"),))
        self.failUnless(str(s) == "inf", "wrong float quoting: " + str(s))      
        self.failUnless(type(s) == float, "wrong float conversion: " + repr(s))

        s = self.execute("SELECT %s AS foo", (float("-inf"),))
        self.failUnless(str(s) == "-inf", "wrong float quoting: " + str(s))      

    def testBinary(self):
        if sys.version_info[0] < 3:
            s = ''.join([chr(x) for x in range(256)])
            b = psycopg2.Binary(s)
            buf = self.execute("SELECT %s::bytea AS foo", (b,))
            self.assertEqual(s, str(buf))
        else:
            s = bytes(range(256))
            b = psycopg2.Binary(s)
            buf = self.execute("SELECT %s::bytea AS foo", (b,))
            self.assertEqual(s, buf)

    def testBinaryEmptyString(self):
        # test to make sure an empty Binary is converted to an empty string
        if sys.version_info[0] < 3:
            b = psycopg2.Binary('')
            self.assertEqual(str(b), "''::bytea")
        else:
            b = psycopg2.Binary(bytes([]))
            self.assertEqual(str(b), "''::bytea")

    def testBinaryRoundTrip(self):
        # test to make sure buffers returned by psycopg2 are
        # understood by execute:
        if sys.version_info[0] < 3:
            s = ''.join([chr(x) for x in range(256)])
            buf = self.execute("SELECT %s::bytea AS foo", (psycopg2.Binary(s),))
            buf2 = self.execute("SELECT %s::bytea AS foo", (buf,))
            self.assertEqual(s, str(buf2))
        else:
            s = bytes(range(256))
            buf = self.execute("SELECT %s::bytea AS foo", (psycopg2.Binary(s),))
            buf2 = self.execute("SELECT %s::bytea AS foo", (buf,))
            self.assertEqual(s, buf2)

    def testArray(self):
        s = self.execute("SELECT %s AS foo", ([],))
        self.failUnlessEqual(s, [])
        s = self.execute("SELECT %s AS foo", ([[1,2],[3,4]],))
        self.failUnlessEqual(s, [[1,2],[3,4]])
        s = self.execute("SELECT %s AS foo", (['one', 'two', 'three'],))
        self.failUnlessEqual(s, ['one', 'two', 'three'])

    @testutils.skip_on_python3
    def testTypeRoundtripBuffer(self):
        o1 = buffer("".join(map(chr, range(256))))
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(type(o1), type(o2))

        # Test with an empty buffer
        o1 = buffer("")
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(type(o1), type(o2))

    @testutils.skip_on_python3
    def testTypeRoundtripBufferArray(self):
        o1 = buffer("".join(map(chr, range(256))))
        o1 = [o1]
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(type(o1[0]), type(o2[0]))

    @testutils.skip_on_python2
    def testTypeRoundtripBytes(self):
        o1 = bytes(range(256))
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(memoryview, type(o2))

        # Test with an empty buffer
        o1 = bytes([])
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(memoryview, type(o2))

    @testutils.skip_on_python2
    def testTypeRoundtripBytesArray(self):
        o1 = bytes(range(256))
        o1 = [o1]
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(memoryview, type(o2[0]))

    @testutils.skip_on_python2
    def testAdaptBytearray(self):
        o1 = bytearray(range(256))
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(memoryview, type(o2))

        # Test with an empty buffer
        o1 = bytearray([])
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(memoryview, type(o2))

    @testutils.skip_on_python2
    def testAdaptMemoryview(self):
        o1 = memoryview(bytes(range(256)))
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(memoryview, type(o2))

        # Test with an empty buffer
        o1 = memoryview(bytes([]))
        o2 = self.execute("select %s;", (o1,))
        self.assertEqual(memoryview, type(o2))


class AdaptSubclassTest(unittest.TestCase):
    def test_adapt_subtype(self):
        from psycopg2.extensions import adapt
        class Sub(str): pass
        s1 = "hel'lo"
        s2 = Sub(s1)
        self.assertEqual(adapt(s1).getquoted(), adapt(s2).getquoted())

    def test_adapt_most_specific(self):
        from psycopg2.extensions import adapt, register_adapter, AsIs

        class A(object): pass
        class B(A): pass
        class C(B): pass

        register_adapter(A, lambda a: AsIs("a"))
        register_adapter(B, lambda b: AsIs("b"))
        try:
            self.assertEqual(b('b'), adapt(C()).getquoted())
        finally:
           del psycopg2.extensions.adapters[A, psycopg2.extensions.ISQLQuote]
           del psycopg2.extensions.adapters[B, psycopg2.extensions.ISQLQuote]

    @testutils.skip_on_python3
    def test_no_mro_no_joy(self):
        from psycopg2.extensions import adapt, register_adapter, AsIs

        class A: pass
        class B(A): pass

        register_adapter(A, lambda a: AsIs("a"))
        try:
            self.assertRaises(psycopg2.ProgrammingError, adapt, B())
        finally:
           del psycopg2.extensions.adapters[A, psycopg2.extensions.ISQLQuote]


    @testutils.skip_on_python2
    def test_adapt_subtype_3(self):
        from psycopg2.extensions import adapt, register_adapter, AsIs

        class A: pass
        class B(A): pass

        register_adapter(A, lambda a: AsIs("a"))
        try:
            self.assertEqual(b("a"), adapt(B()).getquoted())
        finally:
           del psycopg2.extensions.adapters[A, psycopg2.extensions.ISQLQuote]


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()

