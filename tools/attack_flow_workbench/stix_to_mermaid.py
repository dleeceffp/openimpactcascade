#!/usr/bin/env python3
"""
stix_to_mermaid.py — convert a STIX 2.1 Attack Flow bundle to a Mermaid flowchart.

Usage:
    python stix_to_mermaid.py attack_flow.json                 # prints mermaid to stdout
    python stix_to_mermaid.py attack_flow.json -o flow.mmd      # writes a .mmd file
    python stix_to_mermaid.py attack_flow.json --md             # wraps in a ```mermaid fence

The Mermaid text can be pasted into:
  - https://mermaid.live  (instant render, export PNG/SVG)
  - any Markdown that supports mermaid (GitHub, Obsidian, MkDocs, etc.)
  - the bundled attack_flow_viewer.html (open a bundle directly, no conversion step)
"""
import json, sys, argparse

CONF = {100: "certain", 90: "very-probable", 75: "probable", 50: "even-odds",
        30: "doubtful", 10: "very-doubtful", 0: "speculative"}

def short(sid):
    p = sid.split("--")
    return "n" + (p[1] if len(p) > 1 else sid).replace("-", "")[:10]

def esc(s):
    return (str(s) if s is not None else "").replace('"', "&quot;").replace("\n", " ").replace("<", "").replace(">", "")

def conf_label(c):
    if c is None:
        return ""
    return CONF.get(c, f"conf {c}")

def convert(bundle):
    objs = bundle.get("objects", [])
    actions, assets, conditions, operators, flow = {}, {}, {}, {}, None
    for o in objs:
        t = o.get("type")
        if t == "attack-action": actions[o["id"]] = o
        elif t == "attack-asset": assets[o["id"]] = o
        elif t == "attack-condition": conditions[o["id"]] = o
        elif t == "attack-operator": operators[o["id"]] = o
        elif t == "attack-flow": flow = o

    L = ["flowchart TD"]
    for i, a in actions.items():
        tid = a.get("technique_id", "")
        c = conf_label(a.get("confidence"))
        sub = f"<br/><small>{esc(tid)}{' · ' if tid and c else ''}{esc(c)}</small>" if (tid or c) else ""
        L.append(f'  {short(i)}["<b>{esc(a.get("name"))}</b>{sub}"]')
    for i, a in assets.items():
        L.append(f'  {short(i)}[/"{esc(a.get("name"))}"/]')
    for i, c in conditions.items():
        L.append(f'  {short(i)}{{"{esc(c.get("description") or c.get("name") or "condition")}"}}')
    for i, op in operators.items():
        L.append(f'  {short(i)}(("{esc(op.get("operator", "AND"))}"))')

    linkable = {**actions, **assets, **conditions, **operators}
    def edge(a, b, label=None):
        if b not in linkable: return
        L.append(f"  {short(a)} -->|{esc(label)}| {short(b)}" if label else f"  {short(a)} --> {short(b)}")
    for i, a in actions.items():
        for e in a.get("effect_refs", []): edge(i, e)
        for e in a.get("asset_refs", []): edge(i, e, "targets")
    for i, c in conditions.items():
        for e in c.get("on_true_refs", []): edge(i, e, "true")
        for e in c.get("on_false_refs", []): edge(i, e, "false")
    for i, op in operators.items():
        for e in op.get("effect_refs", []): edge(i, e)

    def cls(ids, name):
        if ids: L.append(f"  class {','.join(short(x) for x in ids)} {name};")
    L.append("  classDef action fill:#1f3a5f,stroke:#4a7fb5,color:#fff;")
    L.append("  classDef asset fill:#c8651b,stroke:#e8893b,color:#fff;")
    L.append("  classDef cond fill:#3a2f5f,stroke:#7b5fb5,color:#fff;")
    L.append("  classDef op fill:#3f3f3f,stroke:#888,color:#fff;")
    cls(actions, "action"); cls(assets, "asset"); cls(conditions, "cond"); cls(operators, "op")

    # diagnostics to stderr
    connected = set()
    for a in actions.values():
        for e in a.get("asset_refs", []): connected.add(e)
    orphans = [a for a in assets if a not in connected]
    if orphans:
        sys.stderr.write(f"warning: {len(orphans)} asset(s) not linked to any action "
                         f"(generator did not emit asset_refs)\n")
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("-o", "--output")
    ap.add_argument("--md", action="store_true", help="wrap in a ```mermaid fence")
    a = ap.parse_args()
    b = json.load(open(a.bundle))
    m = convert(b)
    if a.md:
        m = "```mermaid\n" + m + "\n```"
    if a.output:
        open(a.output, "w").write(m)
        sys.stderr.write(f"wrote {a.output}\n")
    else:
        try:
            print(m)
        except BrokenPipeError:
            pass

if __name__ == "__main__":
    main()
