import unittest
import os
from code_parser.parsers.html_parser import HTMLParser

class TestHTMLParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get the path to the test HTML file
        cls.test_file = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'test_html_file_1.html')
        cls.parser = HTMLParser(cls.test_file)

    def test_basic_html_structure(self):
        # Test that we have a valid HTML document
        html = next(elem for elem in self.parser.elements if elem.tag_name == 'html')
        self.assertEqual(html.attributes.get('lang'), 'en')
        
        # Test head section
        head = next(elem for elem in html.children if elem.tag_name == 'head')
        self.assertIsNotNone(head)
        
        # Test title
        title = next(elem for elem in head.children if elem.tag_name == 'title')
        self.assertEqual(title.content, 'LLM HTML Editor Demo')

    def test_script_parsing(self):
        # Test that all script tags are parsed
        self.assertTrue(len(self.parser.scripts) > 0)
        
        # Test external script
        prettier_script = next(
            script for script in self.parser.scripts 
            if script.src and 'prettier' in script.src
        )
        self.assertIsNotNone(prettier_script)
        self.assertTrue(prettier_script.src.startswith('https://unpkg.com/prettier'))

    def test_style_links(self):
        # Test that CSS links are properly parsed
        head = next(elem for elem in self.parser.elements[0].children if elem.tag_name == 'head')
        css_links = [
            link for link in head.children 
            if link.tag_name == 'link' and link.attributes.get('rel') == 'stylesheet'
        ]
        self.assertEqual(len(css_links), 2)
        
        # Test Font Awesome CSS
        font_awesome = next(
            link for link in css_links 
            if 'font-awesome' in link.attributes.get('href', '')
        )
        self.assertIsNotNone(font_awesome)

    def test_form_elements(self):
        # Test API key input form elements
        api_key_input = self.parser.get_elements_by_id('apiKeyInput')[0]
        self.assertEqual(api_key_input.tag_name, 'input')
        self.assertEqual(api_key_input.attributes.get('type'), 'password')
        
        # Test that the input has the correct class
        self.assertIn('api-key-input', api_key_input.attributes.get('class', ''))

    def test_element_queries(self):
        # Test getting elements by class
        buttons = self.parser.get_elements_by_class('button')
        self.assertTrue(len(buttons) > 0)
        
        # Test getting elements by tag
        divs = self.parser.get_elements_by_tag('div')
        self.assertTrue(len(divs) > 0)
        
        # Test getting element by ID
        preview_elements = self.parser.get_elements_by_id('preview')
        self.assertEqual(len(preview_elements), 1)  # Should only be one element with this ID
        preview = preview_elements[0]
        self.assertEqual(preview.tag_name, 'div')

    def test_nested_structure(self):
        # Test that nested elements are properly parsed
        container = self.parser.get_elements_by_class('container')[0]
        self.assertTrue(len(container.children) > 0)
        
        # Test that the grid structure is properly parsed
        grid = next(child for child in container.children if 'grid' in child.attributes.get('class', ''))
        self.assertTrue(len(grid.children) > 0)

if __name__ == '__main__':
    unittest.main()