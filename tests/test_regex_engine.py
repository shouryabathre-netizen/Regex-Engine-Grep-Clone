import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex_engine import Regex, RegexSyntaxError


class TestLiteralsAndConcat(unittest.TestCase):
    def test_simple_literal(self):
        self.assertTrue(Regex("abc").fullmatch("abc"))
        self.assertFalse(Regex("abc").fullmatch("abd"))
        self.assertFalse(Regex("abc").fullmatch("ab"))

    def test_empty_pattern_matches_empty_string(self):
        self.assertTrue(Regex("").fullmatch(""))
        self.assertFalse(Regex("").fullmatch("a"))


class TestQuantifiers(unittest.TestCase):
    def test_star(self):
        r = Regex("ab*c")
        for s in ["ac", "abc", "abbbbbc"]:
            self.assertTrue(r.fullmatch(s), s)
        self.assertFalse(r.fullmatch("abbd"))

    def test_plus(self):
        r = Regex("ab+c")
        self.assertFalse(r.fullmatch("ac"))
        self.assertTrue(r.fullmatch("abc"))
        self.assertTrue(r.fullmatch("abbbc"))

    def test_question(self):
        r = Regex("colou?r")
        self.assertTrue(r.fullmatch("color"))
        self.assertTrue(r.fullmatch("colour"))
        self.assertFalse(r.fullmatch("colouur"))

    def test_nested_quantifiers(self):
        r = Regex("(ab)+")
        self.assertTrue(r.fullmatch("ab"))
        self.assertTrue(r.fullmatch("ababab"))
        self.assertFalse(r.fullmatch("aba"))


class TestDotAndClasses(unittest.TestCase):
    def test_any_char(self):
        r = Regex("a.c")
        self.assertTrue(r.fullmatch("abc"))
        self.assertTrue(r.fullmatch("azc"))
        self.assertFalse(r.fullmatch("ac"))

    def test_char_class(self):
        r = Regex("[abc]+")
        self.assertTrue(r.fullmatch("aabbcc"))
        self.assertFalse(r.fullmatch("aabbccd"))

    def test_negated_class(self):
        r = Regex("[^0-9]+")
        self.assertTrue(r.fullmatch("hello"))
        self.assertFalse(r.fullmatch("hello1"))

    def test_range_class(self):
        r = Regex("[a-zA-Z][a-zA-Z0-9_]*")
        self.assertTrue(r.fullmatch("var_1"))
        self.assertFalse(r.fullmatch("1var"))

    def test_shorthand_classes(self):
        self.assertTrue(Regex(r"\d+").fullmatch("12345"))
        self.assertFalse(Regex(r"\d+").fullmatch("123a"))
        self.assertTrue(Regex(r"\w+").fullmatch("hello_123"))
        self.assertTrue(Regex(r"\s+").fullmatch("   \t"))


class TestAlternationAndGroups(unittest.TestCase):
    def test_alternation(self):
        r = Regex("cat|dog")
        self.assertTrue(r.fullmatch("cat"))
        self.assertTrue(r.fullmatch("dog"))
        self.assertFalse(r.fullmatch("catdog"))

    def test_grouped_alternation(self):
        r = Regex("gr(a|e)y")
        self.assertTrue(r.fullmatch("gray"))
        self.assertTrue(r.fullmatch("grey"))
        self.assertFalse(r.fullmatch("groy"))

    def test_complex_email_like_pattern(self):
        r = Regex(r"[a-zA-Z0-9._]+@[a-zA-Z0-9]+\.[a-zA-Z]+")
        self.assertTrue(r.fullmatch("user.name@example.com"))
        self.assertFalse(r.fullmatch("not-an-email"))


class TestAnchors(unittest.TestCase):
    def test_start_anchor(self):
        r = Regex("^abc")
        m = r.search("xabc")
        self.assertIsNone(m)
        m = r.search("abcxyz")
        self.assertIsNotNone(m)
        self.assertEqual(m.start, 0)

    def test_end_anchor(self):
        r = Regex("abc$")
        self.assertIsNone(r.search("abcxyz"))
        m = r.search("xyzabc")
        self.assertIsNotNone(m)

    def test_both_anchors(self):
        r = Regex("^abc$")
        self.assertTrue(r.fullmatch("abc"))
        self.assertIsNone(r.search("abcd"))


class TestSearchAndFinditer(unittest.TestCase):
    def test_search_finds_substring(self):
        r = Regex("wor")
        m = r.search("hello world")
        self.assertEqual((m.start, m.end), (6, 9))

    def test_finditer_multiple_matches(self):
        r = Regex(r"\d+")
        matches = list(Regex(r"\d+").finditer("a1 b22 c333"))
        self.assertEqual([m.group for m in matches], ["1", "22", "333"])

    def test_greedy_matching(self):
        r = Regex("a+")
        m = r.search("baaaab")
        self.assertEqual(m.group, "aaaa")


class TestSyntaxErrors(unittest.TestCase):
    def test_unbalanced_paren(self):
        with self.assertRaises(RegexSyntaxError):
            Regex("(abc").fullmatch("abc")

    def test_unterminated_class(self):
        with self.assertRaises(RegexSyntaxError):
            Regex("[abc").fullmatch("a")

    def test_dangling_escape(self):
        with self.assertRaises(RegexSyntaxError):
            Regex("abc\\").fullmatch("abc")


if __name__ == "__main__":
    unittest.main()
