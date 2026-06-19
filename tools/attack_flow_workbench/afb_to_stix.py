"""
Convert a generated attack_flow_v2 .afb into a STIX 2.1 Attack Flow bundle (.json).

Why STIX instead of patching .afb:
  - .afb is the Builder's internal *editor state* (anchors/latches/layout/camera). It has
    no published schema and the loader enforces undocumented invariants -> brittle to hand-build.
  - STIX 2.1 Attack Flow is the FORMAL, schema-validated exchange format. It is pure semantics
    (attack-action / attack-condition / attack-operator / relationships) with NO geometry,
    so the whole class of layout/anchor bugs cannot occur.
  - It is exactly what MITRE's own `attack-flow` CLI emits via `export-stix`.

Output validates against attack-flow-schema-2.0.0.json and can be imported by STIX tooling
and the attack-flow Python library. (To open in the *web Builder*, run it through MITRE's
afb CLI import, since that UI reads .afb.)
"""
import json, sys, uuid
from datetime import datetime, timezone

AF_EXT = "extension-definition--fb9c968a-745b-4ade-9b25-c324172197f4"
EXT_BLOCK = {AF_EXT: {"extension_type": "new-sdo"}}

# Attack Flow confidence is a STIX integer 0-100. Map the generator's vocabulary onto the
# scale's representative midpoints (see Attack Flow "confidence scale" in the language ref).
CONF_INT = {
    "certain": 100, "very-probable": 90, "probable": 75, "even-odds": 50,
    "doubtful": 30, "very-doubtful": 10, "speculative": 0,
    # generator vocabulary -> scale
    "observed": 100, "confirmed": 100, "reported": 75, "speculation": 0,
}

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
           f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"

def props(o):
    return {p[0]: p[1] for p in o.get("properties", []) if isinstance(p, list) and len(p) == 2}

def sid(t):
    return f"{t}--{uuid.uuid4()}"

def convert(inp, outp):
    d = json.load(open(inp))
    objs = {o["instance"]: o for o in d["objects"] if "instance" in o}

    # --- reconstruct the edge graph (source node -> target node) from the .afb wiring ---
    latch_anchor = {}
    for o in d["objects"]:
        if o.get("id") in ("horizontal_anchor", "vertical_anchor"):
            for l in o.get("latches", []):
                latch_anchor[l] = o["instance"]
    anchor_node = {}
    for o in d["objects"]:
        if "anchors" in o:
            for off, a in o["anchors"].items():
                anchor_node[a] = o["instance"]
    def lnode(latch):
        return anchor_node.get(latch_anchor.get(latch))

    succ = {}  # afb node instance -> list of successor afb node instances
    for o in d["objects"]:
        if o.get("id") == "dynamic_line":
            s, t = lnode(o.get("source")), lnode(o.get("target"))
            if s and t:
                succ.setdefault(s, []).append(t)

    ts = now()
    bundle_objs = []

    # --- identity (producer) ---
    flow_node = next(o for o in d["objects"] if o.get("id") == "flow")
    fp = props(flow_node)
    author = {k: v for k, v in (fp.get("author") or [])} if isinstance(fp.get("author"), list) else {}
    ident_id = sid("identity")
    bundle_objs.append({
        "type": "identity", "spec_version": "2.1", "id": ident_id,
        "created": ts, "modified": ts,
        "name": author.get("name", "OIC Attack Flow Workbench"),
        "identity_class": "system",
    })

    # --- map each afb action/asset/condition to a STIX object id ---
    afb_to_stix = {}
    action_nodes = [o for o in d["objects"] if o.get("id") == "action"]
    asset_nodes = [o for o in d["objects"] if o.get("id") == "asset"]

    for o in action_nodes:
        afb_to_stix[o["instance"]] = sid("attack-action")
    for o in asset_nodes:
        afb_to_stix[o["instance"]] = sid("attack-asset")

    # --- build attack-action objects with effect_refs (edges) ---
    for o in action_nodes:
        p = props(o)
        a = {
            "type": "attack-action", "spec_version": "2.1",
            "id": afb_to_stix[o["instance"]],
            "created": ts, "modified": ts,
            "name": p.get("name", "Unnamed action"),
            "tactic_id": p.get("tactic_id"),
            "technique_id": p.get("technique_id"),
            "description": p.get("description", ""),
            "extensions": EXT_BLOCK,
        }
        if p.get("tactic_ref"):
            a["tactic_ref"] = p["tactic_ref"]
        if p.get("technique_ref"):
            a["technique_ref"] = p["technique_ref"]
        # confidence -> integer
        c = p.get("confidence")
        if isinstance(c, str) and c.lower().strip() in CONF_INT:
            a["confidence"] = CONF_INT[c.lower().strip()]
        # edges
        effects = [afb_to_stix[t] for t in succ.get(o["instance"], []) if t in afb_to_stix]
        if effects:
            a["effect_refs"] = effects
        # drop None-valued optional keys (schema dislikes nulls)
        a = {k: v for k, v in a.items() if v is not None}
        bundle_objs.append(a)

    # --- build attack-asset objects ---
    for o in asset_nodes:
        p = props(o)
        bundle_objs.append({
            "type": "attack-asset", "spec_version": "2.1",
            "id": afb_to_stix[o["instance"]],
            "created": ts, "modified": ts,
            "name": p.get("name", "Unnamed asset"),
            "extensions": EXT_BLOCK,
        })

    # --- start_refs = action nodes with no incoming edge ---
    has_incoming = set()
    for s, tlist in succ.items():
        for t in tlist:
            has_incoming.add(t)
    starts = [afb_to_stix[o["instance"]] for o in action_nodes
              if o["instance"] not in has_incoming]
    if not starts and action_nodes:  # fallback: first action
        starts = [afb_to_stix[action_nodes[0]["instance"]]]

    # --- the attack-flow SDO (exactly one) ---
    flow_id = sid("attack-flow")
    af = {
        "type": "attack-flow", "spec_version": "2.1", "id": flow_id,
        "created": ts, "modified": ts,
        "created_by_ref": ident_id,
        "start_refs": starts,
        "name": fp.get("name", "Generated Attack Flow"),
        "description": fp.get("description", ""),
        "scope": fp.get("scope", "incident"),
        "extensions": EXT_BLOCK,
    }
    # external references (provenance) if present on the flow
    ext_refs = fp.get("external_references")
    if isinstance(ext_refs, list) and ext_refs:
        refs = []
        for _, body in ext_refs:
            r = {k: v for k, v in body}
            refs.append(r)
        if refs:
            af["external_references"] = refs
    bundle_objs.insert(1, af)  # right after identity, conventional ordering

    # --- the extension-definition object MUST be present in the bundle ---
    bundle_objs.insert(0, {
        "type": "extension-definition", "spec_version": "2.1",
        "id": AF_EXT,
        "created": "2022-08-02T19:34:35.143Z", "modified": "2022-08-02T19:34:35.143Z",
        "created_by_ref": ident_id,
        "name": "Attack Flow",
        "description": "Extends STIX 2.1 with features to create Attack Flows.",
        "schema": "https://center-for-threat-informed-defense.github.io/attack-flow/stix/attack-flow-schema-2.0.0.json",
        "version": "2.0.0",
        "extension_types": ["new-sdo"],
    })

    bundle = {
        "type": "bundle",
        "id": sid("bundle"),
        "objects": bundle_objs,
    }
    json.dump(bundle, open(outp, "w"), indent=2)
    return len(action_nodes), len(asset_nodes), sum(len(v) for v in succ.values()), len(starts)

if __name__ == "__main__":
    na, nas, ne, ns = convert(sys.argv[1], sys.argv[2])
    print(f"actions: {na}, assets: {nas}, edges: {ne}, start_refs: {ns}")
