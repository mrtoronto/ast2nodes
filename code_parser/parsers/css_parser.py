from dataclasses import dataclass
from typing import List, Dict, Optional
import re

@dataclass
class CSSRule:
    selector: str
    properties: Dict[str, str]
    line_number: int

@dataclass
class MediaQuery:
    query: str
    rules: List[CSSRule]
    line_number: int

class CSSParser:
    def __init__(self, file_path: str = None, content: str = None):
        """Initialize CSS parser with either a file path or direct content."""
        if file_path:
            with open(file_path, 'r') as f:
                self.content = f.read()
        elif content:
            self.content = content
        else:
            raise ValueError("Either file_path or content must be provided")
        
        self.rules: List[CSSRule] = []
        self.media_queries: List[MediaQuery] = []
        self._parse()

    def _parse(self):
        """Parse the CSS content and extract rules and media queries."""
        # Remove comments
        content = re.sub(r'/\*.*?\*/', '', self.content, flags=re.DOTALL)
        
        # Split into potential media queries and regular rules
        parts = re.split(r'(@media[^{]+{)', content)
        
        current_line = 1
        if parts[0].strip():  # Process regular rules before any media queries
            rules = self._parse_rules(parts[0], current_line)
            self.rules.extend(rules)
            current_line += parts[0].count('\n')

        # Process media queries
        for i in range(1, len(parts), 2):
            if i < len(parts):
                media_start = parts[i]
                media_content = parts[i + 1] if i + 1 < len(parts) else ''
                
                # Extract media query
                query = media_start.strip()[6:-1].strip()  # Remove '@media' and '{'
                
                # Parse rules within media query
                line_number = current_line + media_start.count('\n')
                media_rules = self._parse_rules(media_content, line_number)
                
                self.media_queries.append(MediaQuery(
                    query=query,
                    rules=media_rules,
                    line_number=current_line
                ))
                
                current_line += media_start.count('\n') + media_content.count('\n')

    def _parse_rules(self, content: str, start_line: int) -> List[CSSRule]:
        """Parse CSS rules from content string."""
        rules = []
        # Track our position in the content for line numbers
        pos = 0
        current_line = start_line
        
        while pos < len(content):
            # Find the next rule start
            rule_start = content.find('{', pos)
            if rule_start == -1:
                break
                
            # Extract the selector
            selector = content[pos:rule_start].strip()
            if not selector or selector.startswith('@'):
                # Skip this section if it's empty or an at-rule
                pos = rule_start + 1
                continue
                
            # Find the matching closing brace
            brace_count = 1
            rule_end = rule_start + 1
            while rule_end < len(content) and brace_count > 0:
                if content[rule_end] == '{':
                    brace_count += 1
                elif content[rule_end] == '}':
                    brace_count -= 1
                rule_end += 1
                
            if brace_count > 0:
                # Unmatched brace, stop processing
                break
                
            # Extract properties
            properties_str = content[rule_start + 1:rule_end - 1].strip()
            
            # Skip if this is a nested block
            if '{' in properties_str:
                pos = rule_end
                current_line += content[pos:rule_end].count('\n')
                continue
                
            # Count lines up to this rule
            current_line += content[pos:rule_start].count('\n')
            
            # Parse properties
            properties = {}
            for prop in properties_str.split(';'):
                prop = prop.strip()
                if prop:
                    key_value = prop.split(':', 1)
                    if len(key_value) == 2:
                        key, value = key_value
                        properties[key.strip()] = value.strip()
            
            # Create and store the rule
            rule = CSSRule(
                selector=selector,
                properties=properties,
                line_number=current_line
            )
            rules.append(rule)
            
            # Update position and line count
            pos = rule_end
            current_line += properties_str.count('\n') + 1  # +1 for the closing brace
        
        return rules

    def _normalize_selector(self, selector: str) -> str:
        """Normalize a selector for comparison."""
        # Handle both single and double colon pseudo-elements
        s = selector.strip()
        # Convert single colon to double colon for standard pseudo-elements
        s = re.sub(r':(?:before|after|first-line|first-letter|selection|backdrop)\b', 
                  lambda m: '::' + m.group(0)[1:], s)
        # Convert double colon to single colon for comparison
        s = s.replace('::', ':')
        # Normalize whitespace
        return ' '.join(s.split())

    def get_rules_by_selector(self, selector: str) -> List[CSSRule]:
        """Get all rules matching a specific selector."""
        normalized_selector = self._normalize_selector(selector)
        matching_rules = []
        
        # Check regular rules
        for rule in self.rules:
            if self._normalize_selector(rule.selector) == normalized_selector:
                matching_rules.append(rule)
                
        # Check rules in media queries
        for media_query in self.media_queries:
            for rule in media_query.rules:
                if self._normalize_selector(rule.selector) == normalized_selector:
                    matching_rules.append(rule)
                    
        return matching_rules

    def get_rules_by_property(self, property_name: str) -> List[CSSRule]:
        """Get all rules that contain a specific property."""
        matching_rules = []
        for rule in self.rules:
            if property_name in rule.properties:
                matching_rules.append(rule)
        for media_query in self.media_queries:
            for rule in media_query.rules:
                if property_name in rule.properties:
                    matching_rules.append(rule)
        return matching_rules

    def get_media_queries_by_feature(self, feature: str) -> List[MediaQuery]:
        """Get all media queries that match a specific feature (e.g., 'min-width')."""
        return [mq for mq in self.media_queries if feature in mq.query] 