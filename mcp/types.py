"""Type definitions for MCP tools"""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass

@dataclass
class TextContent:
    """Text content returned by tools"""
    type: str
    text: str

@dataclass
class Tool:
    """Tool definition"""
    name: str
    description: str
    inputSchema: Dict 