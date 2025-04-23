from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class HTMLElement:
    tag_name: str
    attributes: Dict[str, str]
    content: Optional[str]
    children: List['HTMLElement']
    line_number: int

@dataclass
class HTMLScript:
    src: Optional[str]
    content: Optional[str]
    type: Optional[str]
    line_number: int

@dataclass
class HTMLStyle:
    content: str
    line_number: int

@dataclass
class HTMLForm:
    action: Optional[str]
    method: str
    inputs: List[Dict[str, str]]
    line_number: int

class HTMLParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.elements: List[HTMLElement] = []
        self.scripts: List[HTMLScript] = []
        self.styles: List[HTMLStyle] = []
        self.forms: List[HTMLForm] = []
        self._parse()

    def _parse(self):
        with open(self.file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Parse the root element (html)
            if soup.html:
                root_element = self._parse_elements(soup.html)
                if root_element:
                    self.elements = [root_element]
            
            # Parse scripts
            for script in soup.find_all('script'):
                self.scripts.append(HTMLScript(
                    src=script.get('src'),
                    content=script.string,
                    type=script.get('type'),
                    line_number=self._get_line_number(script)
                ))
            
            # Parse styles
            for style in soup.find_all('style'):
                self.styles.append(HTMLStyle(
                    content=style.string or '',
                    line_number=self._get_line_number(style)
                ))
            
            # Parse forms
            for form in soup.find_all('form'):
                inputs = []
                for input_elem in form.find_all(['input', 'textarea', 'select']):
                    input_attrs = {k: ' '.join(v) if isinstance(v, list) else v 
                                 for k, v in input_elem.attrs.items()}
                    inputs.append(input_attrs)
                
                self.forms.append(HTMLForm(
                    action=form.get('action'),
                    method=form.get('method', 'get'),
                    inputs=inputs,
                    line_number=self._get_line_number(form)
                ))

    def _parse_elements(self, element, parent: Optional[HTMLElement] = None) -> Optional[HTMLElement]:
        if not hasattr(element, 'name') or element.name is None:
            return None

        # Convert BeautifulSoup's attribute lists to space-separated strings
        attrs = {}
        for key, value in element.attrs.items():
            if isinstance(value, list):
                attrs[key] = ' '.join(value)
            else:
                attrs[key] = value

        html_element = HTMLElement(
            tag_name=element.name,
            attributes=attrs,
            content=element.string if not element.find_all() else None,
            children=[],
            line_number=self._get_line_number(element)
        )

        for child in element.children:
            child_element = self._parse_elements(child, html_element)
            if child_element:
                html_element.children.append(child_element)
        
        return html_element

    def _get_line_number(self, element) -> int:
        # BeautifulSoup doesn't provide line numbers directly
        # This is a basic implementation that counts newlines
        content = str(element)
        with open(self.file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
            pos = file_content.find(content)
            if pos == -1:
                return 0
            return file_content.count('\n', 0, pos) + 1

    def get_elements_by_tag(self, tag_name: str) -> List[HTMLElement]:
        """Get all elements with the specified tag name."""
        result = []
        def search(element):
            if element.tag_name == tag_name:
                result.append(element)
            for child in element.children:
                search(child)
        
        for element in self.elements:
            search(element)
        return result

    def get_elements_by_class(self, class_name: str) -> List[HTMLElement]:
        """Get all elements with the specified class."""
        result = []
        def search(element):
            if 'class' in element.attributes:
                classes = element.attributes['class'].split()
                if class_name in classes:
                    result.append(element)
            for child in element.children:
                search(child)
        
        for element in self.elements:
            search(element)
        return result

    def get_elements_by_id(self, id_value: str) -> List[HTMLElement]:
        """Get elements with the specified ID (should typically be one or zero)."""
        result = []
        def search(element):
            if element.attributes.get('id') == id_value:
                result.append(element)
            for child in element.children:
                search(child)
        
        for element in self.elements:
            search(element)
        return result

def parse_html_file(file_path: str) -> HTMLParser:
    """Parse an HTML file and return the parser instance with extracted entities"""
    parser = HTMLParser(file_path)
    return parser