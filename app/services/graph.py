"""Graph service via Neo4j driver."""

import os
import re
import logging

from neo4j import AsyncGraphDatabase
import neo4j.graph

from app.models import (
    GraphQueryRequest,
    GraphQueryResponse,
    AddNodeRequest,
    AddNodeResponse,
    AddEdgeRequest,
    AddEdgeResponse,
)

logger = logging.getLogger("graph")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme")

_LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(value: str, pattern: re.Pattern) -> str:
    if not pattern.match(value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


class GraphService:
    def __init__(self):
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
        return self._driver

    @staticmethod
    def _neo4j_to_dict(obj):
        """Convert Neo4j objects to JSON-serializable dicts."""
        if isinstance(obj, neo4j.graph.Node):
            return {"_label": list(obj.labels), **{k: v for k, v in obj.items()}}
        if isinstance(obj, neo4j.graph.Relationship):
            return {
                "_type": obj.type,
                "_start": obj.start_node.element_id,
                "_end": obj.end_node.element_id,
                **{k: v for k, v in obj.items()},
            }
        if isinstance(obj, neo4j.graph.Path):
            return [GraphService._neo4j_to_dict(n) for n in obj.nodes]
        return obj

    async def query(self, req: GraphQueryRequest) -> GraphQueryResponse:
        driver = self._get_driver()
        async with driver.session() as session:
            result = await session.run(req.cypher, req.parameters)
            records = [
                {k: self._neo4j_to_dict(v) for k, v in dict(r).items()}
                async for r in result
            ]
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
                params = {
                    "merge_value": req.properties[req.merge_key],
                    "properties": req.properties,
                }
            else:
                cypher = (
                    f"CREATE (n:{label}) SET n += $properties "
                    "RETURN elementId(n) AS node_id, n AS props"
                )
                params = {"properties": req.properties}

            result = await session.run(cypher, params)
            record = await result.single()

        return AddNodeResponse(
            node_id=record["node_id"], label=label, properties=self._neo4j_to_dict(record["props"])
        )

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
            from_node=self._neo4j_to_dict(record["from_node"]),
            to_node=self._neo4j_to_dict(record["to_node"]),
        )
