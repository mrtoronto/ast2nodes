from typing import List, Dict, Optional, Union, Literal
from pydantic import BaseModel, Field

# Define valid entity and relation types using Literal types
EntityTypeStr = Literal["function", "variable", "class", "function_call"]
RelationTypeStr = Literal["calls", "defines", "defined_by", "uses", "called_by", "used_by"]

class EntityTypeModel(BaseModel):
    type: EntityTypeStr = Field(
        description="Type of the code entity",
    )

class RelationTypeModel(BaseModel):
    type: RelationTypeStr = Field(
        description="Type of relationship between entities",
    )

class CodeEntity(BaseModel):
    """Represents a code entity with its relationships"""
    name: str = Field(description="Name of the code entity")
    type: EntityTypeStr = Field(description="Type of the code entity")
    sources: Optional[List[Dict[str, Union[str, int]]]] = Field(
        default=None,
        description="Source locations where this entity is defined"
    )
    relationships: Dict[RelationTypeStr, List[str]] = Field(
        default_factory=dict,
        description="Relationships this entity has with other entities"
    )
    
    @property
    def file(self) -> Optional[str]:
        """Get the first source file path"""
        if self.sources and len(self.sources) > 0:
            return self.sources[0].get('file')
        return None
        
    @property
    def line_number(self) -> Optional[int]:
        """Get the first source line number"""
        if self.sources and len(self.sources) > 0:
            return self.sources[0].get('line_number')
        return None

class GraphQuery(BaseModel):
    """Query parameters for searching the knowledge graph"""
    entity_type: Optional[EntityTypeStr] = Field(
        default=None,
        description="Type of entity to search for"
    )
    name_pattern: Optional[str] = Field(
        default=None,
        description="Pattern to match against entity names"
    )
    relationship_type: Optional[RelationTypeStr] = Field(
        default=None,
        description="Type of relationship to filter by"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="File path to filter entities by"
    )

class DependencyInfo(BaseModel):
    """Information about dependencies between entities"""
    source: str = Field(description="Source entity name")
    target: str = Field(description="Target entity name")
    relationship_type: RelationTypeStr = Field(description="Type of relationship")
    source_type: EntityTypeStr = Field(description="Type of source entity")
    target_type: EntityTypeStr = Field(description="Type of target entity")

class SearchCodeRequest(BaseModel):
    """Request parameters for searching code entities"""
    entity_type: Optional[EntityTypeStr] = Field(
        default=None,
        description="Type of entity to search for (function, variable, class, or function_call)"
    )
    name_pattern: Optional[str] = Field(
        default=None,
        description="Pattern to match against entity names"
    )
    relationship_type: Optional[RelationTypeStr] = Field(
        default=None,
        description="Type of relationship to filter by"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="File path to filter entities by"
    )

class EntityInfoRequest(BaseModel):
    """Request parameters for getting entity information"""
    name: str = Field(description="Name of the entity to look up")

class DependencyRequest(BaseModel):
    """Request parameters for finding dependencies"""
    entity_name: str = Field(description="Name of the entity to find dependencies for")
    relationship_type: Optional[RelationTypeStr] = Field(
        default=None,
        description="Type of relationship to filter by"
    )

class CallerRequest(BaseModel):
    """Request parameters for finding function callers"""
    function_name: str = Field(description="Name of the function to find callers for")

class ClassHierarchyRequest(BaseModel):
    """Request parameters for finding class hierarchy"""
    class_name: str = Field(description="Name of the class to find hierarchy for") 