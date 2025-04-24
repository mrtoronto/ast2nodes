import ast
from code_parser.entities import Variable, ClassDef, FunctionDef, FunctionCall

__all__ = ['parse_python_file']

class PythonCodeParser(ast.NodeVisitor):
    """Parser to extract entities from Python code using AST"""
    
    def __init__(self):
        self.variables = []
        self.classes = []
        self.functions = []
        self.function_calls = []
        self.current_function = None
        self.current_class = None
        self.imported_names = {}  # Maps imported names to their modules
        self.defined_functions = set()  # Set of function names defined in this file
        
    def visit_Assign(self, node):
        """Extract variable assignments"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Regular variable assignment
                var = self._create_variable(
                    name=target.id,
                    line_number=target.lineno,
                    column_offset=target.col_offset,
                    value=self._get_value(node.value)
                )
                
                # Track variable relationships
                if self.current_function:
                    self.current_function.defined_variables.add(var.name)
                if self.current_class:
                    self.current_class.instance_variables.add(var.name)
            elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                # Handle instance variable assignment (self.attr = value)
                if target.value.id == 'self' and self.current_class:
                    var = self._create_variable(
                        name=target.attr,
                        line_number=target.lineno,
                        column_offset=target.col_offset,
                        value=self._get_value(node.value)
                    )
                    self.current_class.instance_variables.add(target.attr)
                    if self.current_function:
                        self.current_function.defined_variables.add(target.attr)
                        
        # Track variables used in the assignment value
        self._track_variable_usage(node.value)
        self.generic_visit(node)
    
    def _create_variable(self, name: str, line_number: int, column_offset: int, value: any) -> Variable:
        """Create a new variable or update existing one based on scope"""
        # Create a new variable with current scope
        var = Variable(
            name=name,
            line_number=line_number,
            column_offset=column_offset,
            value=value,
            defined_in_function=self.current_function.name if self.current_function else None,
            defined_in_class=self.current_class.name if self.current_class else None
        )
        
        # For variables in methods, we want to track them separately
        if self.current_function:
            self.variables.append(var)
            return var
            
        # For module-level variables, check if it exists
        existing_var = None
        for v in self.variables:
            if (v.name == name and 
                v.defined_in_function is None and 
                v.defined_in_class is None):
                existing_var = v
                break
                
        if existing_var:
            existing_var.value = value
            return existing_var
        else:
            self.variables.append(var)
            return var
    
    def visit_Attribute(self, node):
        """Handle attribute access (e.g., self.value)"""
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            # This is accessing an instance variable
            if self.current_function:
                self.current_function.used_variables.add(node.attr)
                # Find the variable and mark it as used
                for var in self.variables:
                    if var.name == node.attr and var.defined_in_class == self.current_class.name:
                        var.used_in_functions.add(self.current_function.name)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Extract class definitions"""
        bases = [self._get_name(base) for base in node.bases]
        methods = [method.name for method in node.body if isinstance(method, ast.FunctionDef)]
        
        class_def = ClassDef(
            name=node.name,
            line_number=node.lineno,
            column_offset=node.col_offset,
            bases=bases,
            methods=methods,
            docstring=ast.get_docstring(node)
        )
        
        # Set current class context
        previous_class = self.current_class
        self.current_class = class_def
        self.classes.append(class_def)
        
        # Visit class body to process methods and variables
        self.generic_visit(node)
        
        # Restore previous class context
        self.current_class = previous_class
    
    def visit_FunctionDef(self, node):
        """Extract function definitions"""
        # Track this as a defined function
        self.defined_functions.add(node.name)
        if self.current_class:
            self.defined_functions.add(f"{self.current_class.name}.{node.name}")
            
        args = [arg.arg for arg in node.args.args]
        returns = None
        if node.returns:
            returns = self._get_name(node.returns)
            
        func_def = FunctionDef(
            name=node.name,
            line_number=node.lineno,
            column_offset=node.col_offset,
            args=args,
            returns=returns,
            docstring=ast.get_docstring(node),
            parent_class=self.current_class.name if self.current_class else None
        )
        
        # Mark as internal function and store docstring in properties
        func_def.properties['source'] = 'internal'
        if func_def.docstring:
            func_def.properties['docstring'] = func_def.docstring
        
        # Set current function context
        previous_function = self.current_function
        self.current_function = func_def
        self.functions.append(func_def)
        
        # Add method to class if we're in a class context
        if self.current_class:
            self.current_class.method_objects[func_def.name] = func_def
        
        # Visit function body to track variable usage and function calls
        self.generic_visit(node)
        
        # Restore previous function context
        self.current_function = previous_function
    
    def visit_Call(self, node):
        """Extract function calls"""
        func_name = self._get_name(node.func)
        args = [self._get_value(arg) for arg in node.args]
        keywords = {kw.arg: self._get_value(kw.value) for kw in node.keywords}
        
        call = FunctionCall(
            name=func_name,
            line_number=node.lineno,
            column_offset=node.col_offset,
            args=args,
            keywords=keywords,
            caller_function=self.current_function.name if self.current_function else None,
            caller_class=self.current_class.name if self.current_class else None
        )
        
        # Determine if this is an external or internal function call
        if func_name in self.imported_names:
            call.properties['source'] = 'external'
            call.properties['import_info'] = self.imported_names[func_name]
        elif func_name in self.defined_functions:
            call.properties['source'] = 'internal'
        else:
            # Could be builtin or undefined
            call.properties['source'] = 'unknown'
        
        self.function_calls.append(call)
        
        # Track function call relationships
        if self.current_function:
            self.current_function.called_functions.add(func_name)
        
        # Track variable usage in arguments
        for arg in node.args:
            self._track_variable_usage(arg)
        for kw in node.keywords:
            self._track_variable_usage(kw.value)
            
        self.generic_visit(node)
    
    def visit_Name(self, node):
        """Track variable usage"""
        if isinstance(node.ctx, ast.Load):
            self._track_variable_usage(node)
        self.generic_visit(node)
    
    def _track_variable_usage(self, node):
        """Helper to track variable usage in expressions"""
        if isinstance(node, ast.Name):
            # Find the variable in our list
            for var in self.variables:
                if var.name == node.id:
                    if self.current_function:
                        var.used_in_functions.add(self.current_function.name)
                        self.current_function.used_variables.add(var.name)
        elif isinstance(node, (ast.Call, ast.Attribute)):
            self.generic_visit(node)
    
    def _get_name(self, node) -> str:
        """Helper to get name from various node types"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Subscript):
            # Handle type annotations like List[int]
            value = self._get_name(node.value)
            if isinstance(node.slice, ast.Tuple):
                # Handle multiple type args like Dict[str, Any]
                elts = [self._get_name(elt) for elt in node.slice.elts]
                slice_value = ', '.join(elts)
            else:
                slice_value = self._get_name(node.slice)
            return f"{value}[{slice_value}]"
        return str(node)
    
    def _get_value(self, node) -> any:
        """Helper to get value from various node types"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return f"{self._get_name(node.func)}()"
        elif isinstance(node, ast.List):
            return [self._get_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            return {
                self._get_value(key): self._get_value(value)
                for key, value in zip(node.keys, node.values)
            }
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)

    def visit_Import(self, node):
        """Track imported names"""
        for alias in node.names:
            imported_name = alias.asname if alias.asname else alias.name
            self.imported_names[imported_name] = {
                'module': alias.name,
                'alias': alias.asname,
                'type': 'import'
            }
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Track from ... import names"""
        for alias in node.names:
            imported_name = alias.asname if alias.asname else alias.name
            self.imported_names[imported_name] = {
                'module': node.module,
                'name': alias.name,
                'alias': alias.asname,
                'type': 'import_from'
            }
        self.generic_visit(node)

def parse_python_file(file_path: str) -> PythonCodeParser:
    """Parse a Python file and extract all code entities"""
    with open(file_path, 'r') as f:
        code = f.read()
    
    tree = ast.parse(code)
    parser = PythonCodeParser()
    parser.visit(tree)
    return parser 