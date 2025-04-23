import esprima
from code_parser.entities import JSVariable, JSFunction, JSClass, JSEventListener

class JavaScriptParser:
    """Parser to extract entities from JavaScript code using esprima"""
    
    def __init__(self):
        self.variables = []
        self.functions = []
        self.classes = []
        self.event_listeners = []
        
    def parse(self, code: str):
        """Parse JavaScript code and extract entities"""
        try:
            tree = esprima.parseModule(code, {
                'loc': True, 
                'comment': True,
                'jsx': True,
                'tolerant': True
            })
            self._process_node(tree)
        except Exception as e:
            print(f"Error parsing JavaScript: {e}")
    
    def _process_node(self, node, parent=None):
        """Process an AST node and its children"""
        if hasattr(node, 'type'):
            # Set parent reference
            if parent:
                setattr(node, 'parent', parent)
            
            node_type = node.type
            
            if node_type == 'Program':
                # Process the program body
                for item in node.body:
                    self._process_node(item, node)
            elif node_type == 'VariableDeclaration':
                for declarator in node.declarations:
                    self._process_node(declarator, node)
                self._process_variable_declaration(node)
            elif node_type == 'FunctionDeclaration':
                self._process_function_declaration(node)
            elif node_type == 'ClassDeclaration':
                self._process_class_declaration(node)
            elif node_type == 'ExpressionStatement':
                # Process the expression
                if hasattr(node, 'expression'):
                    self._process_node(node.expression, node)
            elif node_type == 'VariableDeclarator':
                # Handle arrow functions assigned to variables
                if hasattr(node, 'init'):
                    self._process_node(node.init, node)
                if hasattr(node.init, 'type') and node.init.type == 'ArrowFunctionExpression':
                    self._process_arrow_function(node.init, node)
            elif node_type == 'CallExpression':
                # Process nested call expressions (e.g., chained method calls)
                if hasattr(node, 'callee'):
                    self._process_node(node.callee, node)
                for arg in node.arguments:
                    self._process_node(arg, node)
                self._process_call_expression(node)
            elif node_type == 'BlockStatement':
                # Process each statement in the block
                for statement in node.body:
                    self._process_node(statement, node)
            elif node_type == 'MemberExpression':
                if hasattr(node, 'object'):
                    self._process_node(node.object, node)
                if hasattr(node, 'property'):
                    self._process_node(node.property, node)
            
            # Process children, but skip certain attributes to avoid duplicates
            for attr in dir(node):
                if (not attr.startswith('_') and 
                    attr not in ('loc', 'range', 'type', 'body', 'declarations', 'expression', 'right', 'parent',
                               'callee', 'arguments', 'object', 'property', 'init')):
                    value = getattr(node, attr)
                    if isinstance(value, (list, object)):
                        self._process_node(value, node)
        elif isinstance(node, list):
            for item in node:
                self._process_node(item, parent)
    
    def _process_variable_declaration(self, node):
        """Process variable declarations (const, let, var)"""
        kind = node.kind
        for declarator in node.declarations:
            if hasattr(declarator.id, 'type') and declarator.id.type == 'Identifier':
                name = declarator.id.name
                value = self._get_init_value(declarator.init)
                line = declarator.loc.start.line
                col = declarator.loc.start.column
                
                var = JSVariable(
                    name=name,
                    kind=kind,
                    line_number=line,
                    column_offset=col,
                    value=value
                )
                self.variables.append(var)
                
                # Check if this is an arrow function
                if hasattr(declarator.init, 'type') and declarator.init.type == 'ArrowFunctionExpression':
                    self._process_arrow_function(declarator.init, declarator)
    
    def _process_function_declaration(self, node):
        """Process function declarations"""
        if hasattr(node.id, 'name'):
            name = node.id.name
            params = [p.name for p in node.params if hasattr(p, 'type') and p.type == 'Identifier']
            is_async = getattr(node, 'async', False)
            line = node.loc.start.line
            col = node.loc.start.column
            
            func = JSFunction(
                name=name,
                kind='function',
                line_number=line,
                column_offset=col,
                params=params,
                is_async=is_async
            )
            self.functions.append(func)
    
    def _process_class_declaration(self, node):
        """Process class declarations"""
        if hasattr(node.id, 'name'):
            name = node.id.name
            methods = []
            constructor_params = []
            
            for method in node.body.body:
                if hasattr(method, 'type') and method.type == 'MethodDefinition':
                    method_name = method.key.name
                    methods.append(method_name)
                    if method_name == 'constructor':
                        constructor_params = [
                            p.name for p in method.value.params
                            if hasattr(p, 'type') and p.type == 'Identifier'
                        ]
            
            line = node.loc.start.line
            col = node.loc.start.column
            
            cls = JSClass(
                name=name,
                line_number=line,
                column_offset=col,
                methods=methods,
                constructor_params=constructor_params
            )
            self.classes.append(cls)
    
    def _process_call_expression(self, node):
        """Process a call expression node"""
        # Check if this is an event listener registration
        if (hasattr(node, 'callee') and 
            hasattr(node.callee, 'type') and 
            node.callee.type == 'MemberExpression' and
            hasattr(node.callee.property, 'name') and
            node.callee.property.name == 'addEventListener' and
            len(node.arguments) >= 2):
            
            # Get the target (e.g., document, element, etc.)
            target = self._get_call_target(node.callee.object)
            
            # If the target is a variable name, try to find its initialization
            if (hasattr(node.callee.object, 'type') and 
                node.callee.object.type == 'Identifier' and 
                node.callee.object.name != 'document'):
                # Look for variable declarations in the scope
                scope = self._find_scope(node)
                if scope:
                    for statement in scope:
                        if (hasattr(statement, 'type') and 
                            statement.type == 'VariableDeclaration'):
                            for declarator in statement.declarations:
                                if (hasattr(declarator.id, 'name') and 
                                    declarator.id.name == node.callee.object.name and
                                    hasattr(declarator.init, 'type')):
                                    if declarator.init.type == 'CallExpression':
                                        target = self._get_call_target(declarator.init)
            
            # Get the event type (first argument)
            event = self._get_string_value(node.arguments[0])
            
            # Get the handler (second argument)
            handler = self._get_function_body(node.arguments[1])
            
            # Create event listener object
            listener = JSEventListener(
                name=f"{target}__{event}",
                event=event,
                target=target,
                handler=handler,
                line_number=node.loc.start.line,
                column_offset=node.loc.start.column
            )
            self.event_listeners.append(listener)
            
            # Process the handler function body for nested event listeners
            if hasattr(node.arguments[1], 'body'):
                self._process_node(node.arguments[1].body)
        
        # Process nested call expressions
        if hasattr(node, 'callee'):
            self._process_node(node.callee)
        for arg in node.arguments:
            self._process_node(arg)
    
    def _process_arrow_function(self, node, parent):
        """Process arrow function expressions"""
        if hasattr(parent, 'type') and parent.type == 'VariableDeclarator':
            name = parent.id.name
            params = [p.name for p in node.params if hasattr(p, 'type') and p.type == 'Identifier']
            is_async = getattr(node, 'async', False)
            line = node.loc.start.line
            col = node.loc.start.column
            
            func = JSFunction(
                name=name,
                kind='arrow',
                line_number=line,
                column_offset=col,
                params=params,
                is_async=is_async
            )
            self.functions.append(func)
    
    def _get_init_value(self, node):
        """Get the initialization value of a variable"""
        if not node:
            return None
        
        if hasattr(node, 'type'):
            if node.type == 'Literal':
                if isinstance(node.value, str):
                    return f"'{node.value}'"
                return node.value
            elif node.type == 'Identifier':
                return node.name
            elif node.type == 'NewExpression':
                if hasattr(node.callee, 'type') and node.callee.type == 'Identifier':
                    return f"new {node.callee.name}()"
            elif node.type == 'ArrowFunctionExpression':
                return 'arrow function'
        
        return str(getattr(node, 'type', node))
    
    def _get_call_target(self, node):
        """Get the target of a function call"""
        if hasattr(node, 'type'):
            if node.type == 'Identifier':
                return node.name
            elif node.type == 'CallExpression':
                callee = node.callee
                if hasattr(callee, 'type') and callee.type == 'MemberExpression':
                    if (hasattr(callee.object, 'type') and callee.object.type == 'Identifier' and
                        callee.object.name == 'document' and
                        hasattr(callee.property, 'name')):
                        if callee.property.name == 'querySelector':
                            # Handle document.querySelector('#some-id')
                            if len(node.arguments) > 0 and hasattr(node.arguments[0], 'value'):
                                return f"document.querySelector('{node.arguments[0].value}')"
                        elif callee.property.name == 'getElementById':
                            # Handle document.getElementById('some-id')
                            if len(node.arguments) > 0 and hasattr(node.arguments[0], 'value'):
                                return f"document.getElementById('{node.arguments[0].value}')"
            elif node.type == 'MemberExpression':
                if hasattr(node.object, 'type'):
                    return f"{self._get_call_target(node.object)}.{node.property.name}"
        return str(getattr(node, 'type', node))
    
    def _get_string_value(self, node):
        """Get string value from a node"""
        if hasattr(node, 'type') and node.type == 'Literal':
            return node.value
        return None
    
    def _get_function_body(self, node):
        """Get a simplified representation of a function body"""
        if hasattr(node, 'type') and node.type in ['FunctionExpression', 'ArrowFunctionExpression']:
            params = [p.name for p in node.params if hasattr(p, 'type') and p.type == 'Identifier']
            return f"function({', '.join(params)}) {{ ... }}"
        return str(getattr(node, 'type', node))
    
    def _find_scope(self, node):
        """Find the scope (block of statements) containing a node"""
        if hasattr(node, 'parent'):
            parent = node.parent
            while parent:
                if (hasattr(parent, 'type') and 
                    parent.type in ['BlockStatement', 'Program']):
                    return parent.body
                parent = getattr(parent, 'parent', None)
        return None

def parse_javascript_file(file_path: str) -> JavaScriptParser:
    """Parse a JavaScript file and extract all code entities"""
    with open(file_path, 'r') as f:
        code = f.read()
    
    parser = JavaScriptParser()
    parser.parse(code)
    return parser 