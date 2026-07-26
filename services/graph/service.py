import os
import re
import logging

from neo4j import AsyncGraphDatabase

from models import (
    GraphQueryRequest, GraphQueryResponse,
    AddNodeRequest, AddNodeResponse,
    AddEdgeRequest, AddEdgeResponse,
)

logger = logging.getLogger("graph")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme")

_LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(value: str, pattern: re.Pattern) -> str:
    """Validate a label/relationship-type identifier to prevent Cypher injection,
    since Neo4j does not support parameterizing labels or relationship types."""
    if not pattern.match(value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


class GraphService:
    def __init__(self):
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        return self._driver

    async def close(self):
        if self._driver is not None:
            await self._driver.close()

    async def query(self, req: GraphQueryRequest) -> GraphQueryResponse:
        driver = self._get_driver()
        async with driver.session() as session:
            result = await session.run(req.cypher, req.parameters)
            records = [dict(r) async for r in result]
        return GraphQueryResponse(records=records, count=len(records))

    async def add_node(self, req: AddNodeRequest) -> AddNodeResponse:
        label = _safe_identifier(req.label, _LABEL_RE)
        driver = self._get_driver()
        async with driver.session() as session:
            if req.merge_key and req.merge_key in req.properties:
                cypher = (
                    f"MERGE (n:{label} {{{req.merge_key}: $merge_value}}) "
                    "SET n += $properties "
                    "RETURN elementId(n) AS node_id, n AS props"
                )
                params = {"merge_value": req.properties[req.merge_key], "properties": req.properties}
            else:
                cypher = f"CREATE (n:{label}) SET n += $properties RETURN elementId(n) AS node_id, n AS props"
                params = {"properties": req.properties}

            result = await session.run(cypher, params)
            record = await result.single()

        return AddNodeResponse(node_id=record["node_id"], label=label, properties=dict(record["props"]))

    async def add_edge(self, req: AddEdgeRequest) -> AddEdgeResponse:
        from_label = _safe_identifier(req.from_label, _LABEL_RE)
        to_label = _safe_identifier(req.to_label, _LABEL_RE)
        rel = _safe_identifier(req.relationship, _REL_RE)

        cypher = (
            f"MATCH (a:{from_label} {{{req.from_key}: $from_value}}) "
            f"MATCH (b:{to_label} {{{req.to_key}: $to_value}}) "
            f"MERGE (a)-[r:{rel}]->(b) "
            "SET r += $properties "
            "RETURN a AS from_node, b AS to_node"
        )
        params = {
            "from_value": req.from_value,
            "to_value": req.to_value,
            "properties": req.properties,
        }

        driver = self._get_driver()
        async with driver.session() as session:
            result = await session.run(cypher, params)
            record = await result.single()
            if record is None:
                raise ValueError("One or both endpoint nodes were not found")

        return AddEdgeResponse(
            relationship=rel,
            from_node=dict(record["from_node"]),
            to_node=dict(record["to_node"]),
        )


graph_service = GraphService()
