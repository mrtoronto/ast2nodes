from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set

@dataclass
class BaseEntity:
    """Base class for all code entities"""
    name: str
    line_number: int
    column_offset: int
    docstring: Optional[str] = None

# Python-specific entities
@dataclass
class Variable(BaseEntity):
    """Represents a variable declaration or assignment"""
    value: Any = None
    used_in_functions: Set[str] = field(default_factory=set)  # Functions that use this variable
    defined_in_function: Optional[str] = None  # Function where this variable is defined
    defined_in_class: Optional[str] = None  # Class where this variable is defined

@dataclass
class ClassDef(BaseEntity):
    """Represents a class definition"""
    bases: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    instance_variables: Set[str] = field(default_factory=set)  # Variables defined in this class
    method_objects: Dict[str, 'FunctionDef'] = field(default_factory=dict)  # Method name -> Function object

@dataclass
class FunctionDef(BaseEntity):
    """Represents a function definition"""
    args: List[str] = field(default_factory=list)
    returns: Optional[str] = None
    parent_class: Optional[str] = None  # Name of the class this function belongs to
    called_functions: Set[str] = field(default_factory=set)  # Functions called by this function
    used_variables: Set[str] = field(default_factory=set)  # Variables used in this function
    defined_variables: Set[str] = field(default_factory=set)  # Variables defined in this function

@dataclass
class FunctionCall(BaseEntity):
    """Represents a function call"""
    args: List[Any] = field(default_factory=list)
    keywords: Dict[str, Any] = field(default_factory=dict)
    caller_function: Optional[str] = None  # Function containing this call
    caller_class: Optional[str] = None  # Class containing this call

# JavaScript-specific entities
@dataclass
class JSVariable:
    """Represents a JavaScript variable declaration"""
    name: str
    kind: str  # 'const', 'let', or 'var'
    line_number: int
    column_offset: int
    docstring: Optional[str] = None
    value: Any = None

@dataclass
class JSFunction:
    """Represents a JavaScript function declaration or expression"""
    name: str
    kind: str  # 'function' or 'arrow'
    line_number: int
    column_offset: int
    docstring: Optional[str] = None
    params: List[str] = field(default_factory=list)
    is_async: bool = False

@dataclass
class JSClass:
    """Represents a JavaScript class definition"""
    name: str
    line_number: int
    column_offset: int
    docstring: Optional[str] = None
    methods: List[str] = field(default_factory=list)
    constructor_params: List[str] = field(default_factory=list)

@dataclass
class JSEventListener:
    """Represents a JavaScript event listener"""
    name: str
    event: str
    target: str
    handler: str
    line_number: int
    column_offset: int
    docstring: Optional[str] = None 