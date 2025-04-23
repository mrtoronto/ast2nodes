import unittest
from code_parser.parsers.css_parser import CSSParser, CSSRule, MediaQuery

class TestCSSParser(unittest.TestCase):
    def setUp(self):
        self.parser = CSSParser("test_data/test_css_file_1.css")

    def test_basic_rule_parsing(self):
        """Test parsing of basic CSS rules."""
        # Test body rule
        body_rules = self.parser.get_rules_by_selector("body")
        self.assertEqual(len(body_rules), 1)
        body_rule = body_rules[0]
        self.assertEqual(body_rule.properties["background-color"], "#f3f4f6")
        self.assertEqual(body_rule.properties["margin"], "0")
        self.assertEqual(body_rule.properties["padding"], "0")

        # Test container rule
        container_rules = self.parser.get_rules_by_selector(".container")
        self.assertEqual(len(container_rules), 1)
        container_rule = container_rules[0]
        self.assertEqual(container_rule.properties["max-width"], "1200px")
        self.assertEqual(container_rule.properties["margin"], "0 auto")

    def test_media_query_parsing(self):
        """Test parsing of media queries."""
        # Find media queries for min-width
        media_queries = self.parser.get_media_queries_by_feature("min-width")
        self.assertEqual(len(media_queries), 1)
        
        # Check the content of the media query
        media_query = media_queries[0]
        self.assertEqual(media_query.query, "(min-width: 768px)")
        
        # Check rules within the media query
        grid_rules = [rule for rule in media_query.rules if rule.selector == ".grid"]
        self.assertEqual(len(grid_rules), 1)
        self.assertEqual(
            grid_rules[0].properties["grid-template-columns"],
            "repeat(2, 1fr)"
        )

    def test_property_search(self):
        """Test finding rules by property."""
        # Find all rules with display property
        display_rules = self.parser.get_rules_by_property("display")
        self.assertTrue(len(display_rules) >= 3)  # We know there are at least 3 in the test file
        
        # Check specific display values
        grid_rule = next(rule for rule in display_rules if rule.selector == ".grid")
        self.assertEqual(grid_rule.properties["display"], "grid")

    def test_line_numbers(self):
        """Test that line numbers are correctly tracked."""
        # Test a rule we know is near the start
        body_rules = self.parser.get_rules_by_selector("body")
        self.assertEqual(body_rules[0].line_number, 1)

        # Test a rule we know is in the middle
        editor_rules = self.parser.get_rules_by_selector("#htmlEditor")
        self.assertTrue(editor_rules[0].line_number > 1)

    def test_complex_selectors(self):
        """Test parsing of complex selectors."""
        # Test pseudo-class selector
        toggle_slider_before = self.parser.get_rules_by_selector(".toggle-slider:before")
        self.assertEqual(len(toggle_slider_before), 1)
        self.assertEqual(toggle_slider_before[0].properties["content"], '""')
        
        # Test compound selector
        input_checked = self.parser.get_rules_by_selector("input:checked + .toggle-slider")
        self.assertEqual(len(input_checked), 1)
        self.assertEqual(input_checked[0].properties["background-color"], "#2196F3")

if __name__ == '__main__':
    unittest.main() 