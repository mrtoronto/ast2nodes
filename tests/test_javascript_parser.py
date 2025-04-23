import unittest
import os
from pathlib import Path
from code_parser import parse_javascript_file, JSVariable, JSFunction, JSClass, JSEventListener

class TestJavaScriptParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a test file with known content
        cls.test_file = "tests/test_javascript_sample.js"
        test_code = '''
// Import statement
import { renderTodo } from './todoRenderer.js';

// Class definition
class TodoList {
    constructor() {
        this.todos = [];
        this.container = document.getElementById('todo-list');
    }

    addTodo(text) {
        const todo = {
            id: Date.now(),
            text,
            completed: false
        };
        this.todos.push(todo);
        this.render();
    }

    toggleTodo(id) {
        const todo = this.todos.find(t => t.id === id);
        if (todo) {
            todo.completed = !todo.completed;
            this.render();
        }
    }

    render() {
        this.container.innerHTML = this.todos
            .map(todo => renderTodo(todo))
            .join('');
    }
}

// Variables and constants
const todoList = new TodoList();
let currentFilter = 'all';

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    const addButton = document.querySelector('#add-todo');
    const inputField = document.querySelector('#todo-input');

    addButton.addEventListener('click', () => {
        const text = inputField.value.trim();
        if (text) {
            todoList.addTodo(text);
            inputField.value = '';
        }
    });

    // Event delegation for todo items
    document.getElementById('todo-list').addEventListener('click', (event) => {
        if (event.target.matches('.todo-item')) {
            const id = parseInt(event.target.dataset.id);
            todoList.toggleTodo(id);
        }
    });
});

// Function declarations
function filterTodos(filter) {
    currentFilter = filter;
    const filteredTodos = todoList.todos.filter(todo => {
        if (filter === 'active') return !todo.completed;
        if (filter === 'completed') return todo.completed;
        return true;
    });
    return filteredTodos;
}

// Arrow function
const countTodos = () => todoList.todos.length;
'''
        with open(cls.test_file, 'w') as f:
            f.write(test_code)
            
    @classmethod
    def tearDownClass(cls):
        # Clean up the test file
        if os.path.exists(cls.test_file):
            os.remove(cls.test_file)
            
    def setUp(self):
        self.parser = parse_javascript_file(self.test_file)
        
    def test_variable_extraction(self):
        """Test that variables are correctly extracted"""
        variables = {var.name: var for var in self.parser.variables}
        
        # Check specific variables
        self.assertIn('todoList', variables)
        self.assertEqual(variables['todoList'].kind, 'const')
        self.assertEqual(variables['todoList'].value, 'new TodoList()')
        
        self.assertIn('currentFilter', variables)
        self.assertEqual(variables['currentFilter'].kind, 'let')
        self.assertEqual(variables['currentFilter'].value, "'all'")
        
    def test_class_extraction(self):
        """Test that classes are correctly extracted"""
        self.assertEqual(len(self.parser.classes), 1)
        todo_list = self.parser.classes[0]
        
        self.assertEqual(todo_list.name, 'TodoList')
        expected_methods = ['constructor', 'addTodo', 'toggleTodo', 'render']
        self.assertEqual(todo_list.methods, expected_methods)
        
    def test_function_extraction(self):
        """Test that functions are correctly extracted"""
        functions = {func.name: func for func in self.parser.functions}
        
        # Check regular function
        self.assertIn('filterTodos', functions)
        filter_todos = functions['filterTodos']
        self.assertEqual(filter_todos.params, ['filter'])
        self.assertEqual(filter_todos.kind, 'function')
        
        # Check arrow function
        self.assertIn('countTodos', functions)
        count_todos = functions['countTodos']
        self.assertEqual(count_todos.params, [])
        self.assertEqual(count_todos.kind, 'arrow')
        
    def test_event_listener_extraction(self):
        """Test that event listeners are correctly extracted"""
        listeners = self.parser.event_listeners
        
        # Check DOMContentLoaded listener
        dom_ready_listeners = [l for l in listeners if l.event == 'DOMContentLoaded']
        self.assertEqual(len(dom_ready_listeners), 1)
        
        # Check click listeners
        click_listeners = [l for l in listeners if l.event == 'click']
        self.assertEqual(len(click_listeners), 2)
        
        # Verify listener details
        add_button_listener = next(l for l in click_listeners if "querySelector('#add-todo')" in l.target)
        self.assertEqual(add_button_listener.target, "document.querySelector('#add-todo')")

if __name__ == '__main__':
    unittest.main() 