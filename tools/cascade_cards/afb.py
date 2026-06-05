"""Stage A - parse an Attack Flow Builder ``.afb`` file (build spec §4).

IMPORTANT FORMAT NOTE
---------------------
The build spec is written against the *STIX 2.1* serialization of Attack Flow
(``attack-flow`` / ``attack-action`` SDOs with ``start_refs`` / ``effect_refs``).
The corpus shipped in ``refdocs/flowcorpus`` is the Attack Flow Builder **native**
format (``"schema": "attack_flow_v2"``), which stores the same information as a node
+ edge graph:

* Each node (``flow``, ``action``, ``asset``, ``condition``, ``AND_operator`` ...) has
  ``properties`` (``[key, value]`` pairs) and an ``anchors`` map (angle/label -> anchor id).
* ``horizontal_anchor`` / ``vertical_anchor`` objects own ``latches``.
* ``dynamic_line`` objects are directed edges: ``source`` latch -> ``target`` latch.
* ``condition`` nodes expose ``branch:True`` / ``branch:False`` anchors (= on_true/on_false).

We reconstruct the directed graph (node -> node) from those primitives, which is the
native-format equivalent of following ``effect_refs`` / ``on_true_refs``. The downstream
stages are format-agnostic. A STIX loader could be added later returning the same
:class:`ParsedFlow`.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Templates that represent semantic nodes.
ACTION = "action"
CONDITION = "condition"
OPERATORS = {"AND_operator", "OR_operator"}
CONNECTORS = {CONDITION} | OPERATORS  # traversed-through, not emitted as steps
CONTEXT_TEMPLATES = {
    "asset", "tool", "malware", "threat_actor", "infrastructure",
    "vulnerability", "process", "url", "ipv4_addr", "directory", "note",
}
SEMANTIC_TEMPLATES = {"flow", ACTION, CONDITION} | OPERATORS | CONTEXT_TEMPLATES


@dataclass
class Edge:
    target: str
    branch: Optional[str] = None  # "True"/"False" when leaving a condition anchor


@dataclass
class Node:
    instance: str
    template: str
    props: dict
    out: list[Edge] = field(default_factory=list)
    indeg: int = 0
    file_index: int = 0


@dataclass
class Step:
    """An ``action`` node = one cascade gate."""

    instance: str
    name: str
    technique_id: Optional[str]
    technique_ref: Optional[str]
    description: str
    order: int = 0
    asset_names: list[str] = field(default_factory=list)


@dataclass
class BranchMarker:
    """An OR operator or a condition split between steps (feeds the Branching section)."""

    instance: str
    kind: str  # "OR" | "condition"
    description: str
    after_step: Optional[str] = None  # instance id of the nearest upstream action


@dataclass
class ParsedFlow:
    name: str
    description: str
    scope: Optional[str]
    author: Optional[str]
    external_references: list[dict]
    created: Optional[str]
    source_file: str
    steps: list[Step]
    entry_steps: list[str]
    terminal_steps: list[str]
    branches: list[BranchMarker]
    assets: dict[str, str]  # name -> description (topology preconditions)
    nodes: dict[str, Node] = field(default_factory=dict)


def _props_to_dict(properties) -> dict:
    """Flatten AFB ``[[key, value], ...]`` property lists into a dict."""
    out: dict = {}
    for item in properties or []:
        if isinstance(item, list) and len(item) == 2:
            out[item[0]] = item[1]
    return out


def load_afb(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def parse(path: str | Path) -> ParsedFlow:
    """Parse a ``.afb`` file into a :class:`ParsedFlow`."""
    raw = load_afb(path)
    objects = raw.get("objects", [])

    # 1. Index nodes and build latch/anchor -> node + branch maps.
    nodes: dict[str, Node] = {}
    anchor_to_node: dict[str, str] = {}
    anchor_branch: dict[str, str] = {}
    for i, obj in enumerate(objects):
        tmpl = obj.get("id")
        inst = obj.get("instance")
        if not inst:
            continue
        if tmpl in SEMANTIC_TEMPLATES:
            nodes[inst] = Node(inst, tmpl, _props_to_dict(obj.get("properties")), file_index=i)
            for key, anchor_inst in (obj.get("anchors") or {}).items():
                anchor_to_node[anchor_inst] = inst
                if key.startswith("branch:"):
                    anchor_branch[anchor_inst] = key.split(":", 1)[1]

    latch_to_node: dict[str, tuple[str, Optional[str]]] = {}
    for obj in objects:
        if obj.get("id") in ("horizontal_anchor", "vertical_anchor"):
            node = anchor_to_node.get(obj.get("instance"))
            branch = anchor_branch.get(obj.get("instance"))
            for latch in obj.get("latches", []) or []:
                latch_to_node[latch] = (node, branch)

    # 2. Reconstruct directed edges from dynamic_line source/target latches.
    for obj in objects:
        if obj.get("id") != "dynamic_line":
            continue
        src = latch_to_node.get(obj.get("source"))
        tgt = latch_to_node.get(obj.get("target"))
        if not src or not tgt or not src[0] or not tgt[0]:
            continue
        s_node, s_branch = src
        t_node = tgt[0]
        if s_node == t_node:
            continue
        nodes[s_node].out.append(Edge(target=t_node, branch=s_branch))
        nodes[t_node].indeg += 1

    flow_node = next((n for n in nodes.values() if n.template == "flow"), None)
    if flow_node is None:
        raise ValueError(f"{path}: no 'flow' node found (not a valid Attack Flow file)")

    # 3. Collapse to an action-level graph (traverse through connectors).
    action_succ, branch_markers = _action_graph(nodes)

    # 4. Topological order over actions (Kahn, stable by file index).
    order = _topo_sort(action_succ, nodes)
    steps: list[Step] = []
    for idx, inst in enumerate(order, start=1):
        node = nodes[inst]
        steps.append(
            Step(
                instance=inst,
                name=(node.props.get("name") or "").strip(),
                technique_id=node.props.get("technique_id"),
                technique_ref=node.props.get("technique_ref"),
                description=(node.props.get("description") or "").strip(),
                order=idx,
                asset_names=_attached_assets(node, nodes),
            )
        )

    action_instances = set(action_succ)
    entry = [i for i in order if nodes[i].indeg == 0 or not _has_action_pred(i, action_succ)]
    entry = entry[:1] if not entry else _entry_actions(order, action_succ)
    terminal = _terminal_actions(order, action_succ, nodes)

    assets = {
        n.props.get("name", "").strip(): (n.props.get("description") or "").strip()
        for n in nodes.values()
        if n.template == "asset" and n.props.get("name")
    }

    fp = flow_node.props
    author = None
    if isinstance(fp.get("author"), list):
        author = _props_to_dict(fp["author"]).get("name")
    return ParsedFlow(
        name=(fp.get("name") or Path(path).stem).strip(),
        description=(fp.get("description") or "").strip(),
        scope=fp.get("scope"),
        author=author,
        external_references=_parse_external_refs(fp.get("external_references")),
        created=fp.get("created"),
        source_file=Path(path).name,
        steps=steps,
        entry_steps=entry,
        terminal_steps=terminal,
        branches=branch_markers,
        assets=assets,
        nodes=nodes,
    )


def _action_graph(nodes: dict[str, Node]) -> tuple[dict[str, list[str]], list[BranchMarker]]:
    """Return action->action adjacency (through connectors) and branch markers."""
    succ: dict[str, list[str]] = {i: [] for i, n in nodes.items() if n.template == ACTION}
    branch_markers: list[BranchMarker] = []
    seen_markers: set[str] = set()

    for inst in succ:
        # BFS through connector nodes to the next action(s).
        stack = [(e.target, inst) for e in nodes[inst].out]
        visited: set[str] = set()
        while stack:
            cur, origin_action = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            node = nodes.get(cur)
            if node is None:
                continue
            if node.template == ACTION:
                if cur not in succ[inst]:
                    succ[inst].append(cur)
                continue
            if node.template in CONNECTORS:
                if cur not in seen_markers:
                    seen_markers.add(cur)
                    if node.template == CONDITION:
                        branch_markers.append(
                            BranchMarker(cur, "condition",
                                         (node.props.get("description") or "").strip(),
                                         after_step=inst))
                    elif node.template == "OR_operator":
                        branch_markers.append(
                            BranchMarker(cur, "OR",
                                         (node.props.get("operator") or "OR").strip(),
                                         after_step=inst))
                for e in node.out:
                    stack.append((e.target, origin_action))
            # context/leaf nodes are not part of the action chain
    return succ, branch_markers


def _topo_sort(succ: dict[str, list[str]], nodes: dict[str, Node]) -> list[str]:
    indeg: dict[str, int] = {i: 0 for i in succ}
    for i, outs in succ.items():
        for t in outs:
            indeg[t] = indeg.get(t, 0) + 1
    # Stable: process ready nodes in original file order.
    ready = deque(sorted((i for i in succ if indeg[i] == 0), key=lambda x: nodes[x].file_index))
    order: list[str] = []
    while ready:
        cur = ready.popleft()
        order.append(cur)
        for t in succ[cur]:
            indeg[t] -= 1
            if indeg[t] == 0:
                ready.append(t)
        ready = deque(sorted(ready, key=lambda x: nodes[x].file_index))
    # Append any nodes left out by cycles, preserving file order (defensive).
    for i in sorted(succ, key=lambda x: nodes[x].file_index):
        if i not in order:
            order.append(i)
    return order


def _has_action_pred(inst: str, succ: dict[str, list[str]]) -> bool:
    return any(inst in outs for outs in succ.values())


def _entry_actions(order: list[str], succ: dict[str, list[str]]) -> list[str]:
    return [i for i in order if not _has_action_pred(i, succ)]


def _terminal_actions(order: list[str], succ: dict[str, list[str]], nodes: dict[str, Node]) -> list[str]:
    # Actions with no downstream action are terminal; impact-tactic detection is
    # finalized in Stage B once tactics are resolved.
    return [i for i in order if not succ.get(i)]


def _attached_assets(node: Node, nodes: dict[str, Node]) -> list[str]:
    names: list[str] = []
    for e in node.out:
        t = nodes.get(e.target)
        if t and t.template == "asset":
            nm = (t.props.get("name") or "").strip()
            if nm and nm not in names:
                names.append(nm)
    return names


def _parse_external_refs(refs) -> list[dict]:
    out: list[dict] = []
    if isinstance(refs, list):
        for item in refs:
            # AFB stores as [id, [[k,v]...]]
            if isinstance(item, list) and len(item) == 2 and isinstance(item[1], list):
                out.append(_props_to_dict(item[1]))
    return out
