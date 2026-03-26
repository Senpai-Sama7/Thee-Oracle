import pytest
from hypothesis import given, strategies as st
from src.oracle.agent_graph import AgentGraph, AgentNode, NodeTask, NodeResult, EdgeType


class DummyNode(AgentNode):
    async def run(self, task: NodeTask) -> NodeResult:
        return NodeResult(
            task_id=task.task_id, node_id=self.node_id, output="dummy", tool_calls=[], success=True, latency_ms=10.0
        )


def test_add_node():
    graph = AgentGraph(registry=None)
    node = DummyNode("node1")
    graph.add_node(node)
    assert "node1" in graph.nodes


@given(st.lists(st.tuples(st.text(min_size=1), st.text(min_size=1)), min_size=1, max_size=10))
def test_acyclic_property(edges):
    graph = AgentGraph(registry=None)
    nodes_added = set()

    # Try to add edges, should reject cycles
    for from_id, to_id in edges:
        # Self loops
        if from_id == to_id:
            with pytest.raises(ValueError, match="cycle"):
                graph.add_edge(from_id, to_id, EdgeType.DATA)
            continue

        if from_id not in nodes_added:
            graph.add_node(DummyNode(from_id))
            nodes_added.add(from_id)
        if to_id not in nodes_added:
            graph.add_node(DummyNode(to_id))
            nodes_added.add(to_id)

        if graph._would_cause_cycle(from_id, to_id):
            with pytest.raises(ValueError):
                graph.add_edge(from_id, to_id, EdgeType.DATA)
        else:
            graph.add_edge(from_id, to_id, EdgeType.DATA)

    # Final check to ensure we indeed have no cycles (just in case the check is faulty)
    # A DAG must have at least one node with in-degree 0 if it has edges,
    # but more formally topological sort must succeed.
    if graph.edges:
        in_degrees = {n: 0 for n in graph.nodes}
        for e in graph.edges:
            in_degrees[e["to_id"]] += 1

        queue = [n for n, d in in_degrees.items() if d == 0]
        visited_count = 0

        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for e in graph.edges:
                if e["from_id"] == curr:
                    in_degrees[e["to_id"]] -= 1
                    if in_degrees[e["to_id"]] == 0:
                        queue.append(e["to_id"])

        assert visited_count == len(graph.nodes), "Cycle detected in final graph despite prevention"
