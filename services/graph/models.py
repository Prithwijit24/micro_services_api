from typing import Optional, Any
from pydantic import BaseModel, Field


class GraphQueryRequest(BaseModel):
    cypher: str = Field(..., description="Parameterized Cypher query")
    parameters: dict[str, Any] = Field(default_factory=dict)


class GraphQueryResponse(BaseModel):
    records: list[dict[str, Any]]
    count: int


class AddNodeRequest(BaseModel):
    label: str = Field(..., description="Node label, e.g. 'Person'")
    properties: dict[str, Any] = Field(default_factory=dict)
    merge_key: Optional[str] = Field(
        default=None, description="Property key to MERGE on instead of always CREATE"
    )


class AddNodeResponse(BaseModel):
    node_id: str
    label: str
    properties: dict[str, Any]


class AddEdgeRequest(BaseModel):
    from_label: str
    from_key: str
    from_value: Any
    to_label: str
    to_key: str
    to_value: Any
    relationship: str
    properties: dict[str, Any] = Field(default_factory=dict)


class AddEdgeResponse(BaseModel):
    relationship: str
    from_node: dict[str, Any]
    to_node: dict[str, Any]
