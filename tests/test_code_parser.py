import unittest
import os
from pathlib import Path
from code_parser import parse_python_file, Variable, ClassDef, FunctionDef, FunctionCall

class TestPythonCodeParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a test file with known content
        cls.test_file = "tests/test_python_sample.py"
        test_code = '''
import math
from typing import List, Optional

class TestClass:
    """Test class docstring"""
    def __init__(self, value: int = 0):
        self.value = value
        
    def test_method(self, x: int) -> int:
        """Test method docstring"""
        result = x + self.value
        return result

def standalone_function(a: int, b: str = "default") -> List[int]:
    """Standalone function docstring"""
    numbers = [1, 2, 3]
    result = math.sqrt(a)
    print(f"{b}: {result}")
    return numbers

# Variable assignments
test_var = 42
complex_call = standalone_function(10, b="test")
instance = TestClass(100)
instance.test_method(5)
'''
        with open(cls.test_file, 'w') as f:
            f.write(test_code)
            
    @classmethod
    def tearDownClass(cls):
        # Clean up the test file
        if os.path.exists(cls.test_file):
            os.remove(cls.test_file)
            
    def setUp(self):
        self.parser = parse_python_file(self.test_file)
        
    def test_variable_extraction(self):
        """Test that variables are correctly extracted"""
        # Helper to find variables by name and scope
        def find_variable(name, function=None, class_name=None):
            for var in self.parser.variables:
                if (var.name == name and
                    var.defined_in_function == function and
                    var.defined_in_class == class_name):
                    return var
            return None
        
        # Check specific variables
        test_var = find_variable('test_var')
        self.assertIsNotNone(test_var)
        self.assertEqual(test_var.value, 42)
        
        complex_call = find_variable('complex_call')
        self.assertIsNotNone(complex_call)
        self.assertEqual(complex_call.value, 'standalone_function()')
        
        instance = find_variable('instance')
        self.assertIsNotNone(instance)
        self.assertEqual(instance.value, 'TestClass()')
        
        # Test variable relationships
        value_var = find_variable('value', '__init__', 'TestClass')
        self.assertIsNotNone(value_var)
        self.assertEqual(value_var.defined_in_class, 'TestClass')
        self.assertEqual(value_var.defined_in_function, '__init__')
        self.assertIn('test_method', value_var.used_in_functions)
        
        result_var = find_variable('result', 'test_method', 'TestClass')
        self.assertIsNotNone(result_var)
        self.assertEqual(result_var.defined_in_function, 'test_method')
        
    def test_class_extraction(self):
        """Test that classes are correctly extracted"""
        self.assertEqual(len(self.parser.classes), 1)
        test_class = self.parser.classes[0]
        
        self.assertEqual(test_class.name, 'TestClass')
        self.assertEqual(test_class.methods, ['__init__', 'test_method'])
        self.assertEqual(test_class.docstring, 'Test class docstring')
        
        # Test class relationships
        self.assertIn('value', test_class.instance_variables)
        self.assertIn('__init__', test_class.method_objects)
        self.assertIn('test_method', test_class.method_objects)
        
        # Test method objects
        init_method = test_class.method_objects['__init__']
        self.assertEqual(init_method.parent_class, 'TestClass')
        self.assertIn('value', init_method.defined_variables)
        
        test_method = test_class.method_objects['test_method']
        self.assertEqual(test_method.parent_class, 'TestClass')
        self.assertIn('result', test_method.defined_variables)
        self.assertIn('value', test_method.used_variables)
        
    def test_function_extraction(self):
        """Test that functions are correctly extracted"""
        functions = {func.name: func for func in self.parser.functions}
        
        # Check standalone function
        self.assertIn('standalone_function', functions)
        standalone = functions['standalone_function']
        self.assertEqual(standalone.args, ['a', 'b'])
        self.assertEqual(standalone.docstring, 'Standalone function docstring')
        self.assertEqual(standalone.returns, 'List[int]')
        self.assertIsNone(standalone.parent_class)
        
        # Test function relationships
        self.assertIn('numbers', standalone.defined_variables)
        self.assertIn('result', standalone.defined_variables)
        self.assertIn('math.sqrt', standalone.called_functions)
        self.assertIn('print', standalone.called_functions)
        
        # Check class methods
        self.assertIn('__init__', functions)
        self.assertIn('test_method', functions)
        
        init_method = functions['__init__']
        self.assertEqual(init_method.args, ['self', 'value'])
        self.assertEqual(init_method.parent_class, 'TestClass')
        
        test_method = functions['test_method']
        self.assertEqual(test_method.args, ['self', 'x'])
        self.assertEqual(test_method.returns, 'int')
        self.assertEqual(test_method.docstring, 'Test method docstring')
        self.assertEqual(test_method.parent_class, 'TestClass')
        
    def test_function_calls(self):
        """Test that function calls are correctly extracted"""
        calls = self.parser.function_calls
        
        # Find specific calls by name
        standalone_calls = [call for call in calls if call.name == 'standalone_function']
        self.assertTrue(any(standalone_calls))
        standalone_call = standalone_calls[0]
        self.assertEqual(len(standalone_call.args), 1)
        self.assertEqual(standalone_call.args[0], 10)
        self.assertEqual(standalone_call.keywords, {'b': 'test'})
        self.assertIsNone(standalone_call.caller_function)  # Called from module level
        self.assertIsNone(standalone_call.caller_class)
        
        # Test method calls
        method_calls = [call for call in calls if call.name == 'instance.test_method']
        self.assertTrue(any(method_calls))
        method_call = method_calls[0]
        self.assertEqual(len(method_call.args), 1)
        self.assertEqual(method_call.args[0], 5)
        self.assertIsNone(method_call.caller_function)  # Called from module level
        self.assertIsNone(method_call.caller_class)
        
        # Test class instantiation
        class_calls = [call for call in calls if call.name == 'TestClass']
        self.assertTrue(any(class_calls))
        class_call = class_calls[0]
        self.assertEqual(len(class_call.args), 1)
        self.assertEqual(class_call.args[0], 100)
        self.assertIsNone(class_call.caller_function)  # Called from module level
        self.assertIsNone(class_call.caller_class)

    def test_parse_pubmed_file(self):
        """Test parsing of the PubMed fetcher implementation file"""
        parser = parse_python_file("test_data/test_py_file_1.py")
        
        # Test class definitions
        classes = {cls.name: cls for cls in parser.classes}
        
        # Verify TqdmLoggingHandler
        self.assertIn('TqdmLoggingHandler', classes)
        tqdm_handler = classes['TqdmLoggingHandler']
        self.assertIn('emit', tqdm_handler.methods)
        self.assertIn('__init__', tqdm_handler.methods)
        
        # Verify RateLimiter
        self.assertIn('RateLimiter', classes)
        rate_limiter = classes['RateLimiter']
        self.assertIn('acquire', rate_limiter.methods)
        self.assertIn('__init__', rate_limiter.methods)
        
        # Verify PubMedFetcher
        self.assertIn('PubMedFetcher', classes)
        pubmed_fetcher = classes['PubMedFetcher']
        expected_methods = [
            '__init__', '_respect_rate_limit', '_handle_request_with_backoff',
            'get_pmc_full_text', 'search_pubmed', 'fetch_article_details'
        ]
        for method in expected_methods:
            self.assertIn(method, pubmed_fetcher.methods)
        
        # Test standalone functions
        functions = {func.name: func for func in parser.functions}
        expected_functions = [
            'create_rate_limiter', 'process_chunk', 'chunk_list', 'main'
        ]
        for func_name in expected_functions:
            self.assertIn(func_name, functions)
            
        # Verify specific function signatures
        self.assertEqual(functions['create_rate_limiter'].returns, 'RateLimiter')
        self.assertEqual(functions['process_chunk'].returns, 'List[Dict[str, Any]]')
        
        # Test important variables
        variables = {var.name: var for var in parser.variables}
        self.assertIn('logger', variables)
        self.assertEqual(variables['logger'].value, 'logging.getLogger()')
        
        # Test function calls
        calls = parser.function_calls
        
        # Verify logging setup calls
        logging_calls = [call for call in calls if call.name == 'logging.basicConfig']
        self.assertTrue(any(logging_calls))
        basic_config = logging_calls[0]
        self.assertEqual(basic_config.keywords.get('level'), 'logging.INFO')
        
        # Verify Entrez setup in PubMedFetcher init
        entrez_calls = [call for call in calls if 'Entrez' in call.name]
        self.assertTrue(any(entrez_calls))

if __name__ == '__main__':
    unittest.main() 