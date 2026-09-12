import json
import math
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLUSTERS = ROOT / "clusters.json"
EXTRACTED = ROOT / "extracted"
MERGED = ROOT / "merged"

STOP = {
    "a","an","and","are","as","at","be","been","being","but","by","can","could","do","does","for","from",
    "had","has","have","how","if","in","into","is","it","its","may","not","of","on","only","or","should",
    "that","the","their","then","there","these","they","this","to","was","what","when","where","which",
    "who","will","with","would","system","memory","memories","answer","answers","user","users","result","results",
}


def clean(text):
    text = str(text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def tokens(text):
    return [w for w in re.findall(r"[a-z0-9]+", clean(text).lower()) if len(w) > 2 and w not in STOP]


def unresolved(row):
    q = re.sub(r"\W+", "", clean(row.get("q")).lower())
    a = re.sub(r"\W+", "", clean(row.get("a")).lower())
    return not a or a == q


def vectorize(answers):
    docs = [tokens(a) for a in answers]
    df = Counter()
    for doc in docs:
        df.update(set(doc))
    n = max(1, len(docs))
    vectors = []
    for doc in docs:
        tf = Counter(doc)
        vec = {t: c * (math.log((n + 1) / (df[t] + 1)) + 1) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1
        vectors.append({t: v / norm for t, v in vec.items()})
    return vectors


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0) for k, v in a.items())


def polarity(text):
    s = clean(text).lower()
    tags = set()
    patterns = {
        "none": r"\b(none|never|nothing|no match|empty|discard|drop|excluded?|disabled?)\b",
        "all": r"\b(all|always|every|whole|raw|unfiltered)\b",
        "hybrid": r"\b(hybrid|both|multi[- ]stage|combination|together)\b",
        "conditional": r"\b(if|when|conditional|depending|threshold|policy|permission|consent|budget)\b",
        "retain": r"\b(retain|keep|append|version|lineage|tombstone|history)\b",
        "overwrite": r"\b(overwrite|replace|update in place|delete|remove)\b",
        "semantic": r"\b(vector|embedding|semantic)\b",
        "lexical": r"\b(lexical|keyword|bm25|exact match)\b",
        "structured": r"\b(graph|structured|filter|metadata|relation|sql)\b",
        "ask": r"\b(ask|clarif|confirm|query the user)\b",
        "abstain": r"\b(abstain|unknown|insufficient|withhold|fail closed)\b",
        "automatic": r"\b(automatic|automatically|inline|synchronous|background)\b",
        "manual": r"\b(manual|explicit|user-designated|opt[- ]in)\b",
    }
    for tag, pat in patterns.items():
        if re.search(pat, s):
            tags.add(tag)
    return tags


def similarity(i, j, rows, vecs):
    p1, p2 = polarity(rows[i]["a"]), polarity(rows[j]["a"])
    conflict_pairs = [("all", "none"), ("retain", "overwrite"), ("ask", "automatic"), ("manual", "automatic")]
    if any((a in p1 and b in p2) or (b in p1 and a in p2) for a, b in conflict_pairs):
        return -0.25
    bonus = 0.10 * len(p1 & p2)
    return cosine(vecs[i], vecs[j]) + min(0.25, bonus)


def cluster_rows(rows):
    if not rows:
        return []
    resolved = [r for r in rows if not unresolved(r)]
    unanswered = [r for r in rows if unresolved(r)]
    groups = []
    if resolved:
        vecs = vectorize([r["a"] for r in resolved])
        for i, row in enumerate(resolved):
            best_g, best_score = None, -1
            for gi, group in enumerate(groups):
                score = max(similarity(i, j, resolved, vecs) for j in group)
                if score > best_score:
                    best_g, best_score = gi, score
            if best_g is not None and best_score >= 0.20:
                groups[best_g].append(i)
            else:
                groups.append([i])
        while len(groups) > 4:
            best = None
            for a in range(len(groups)):
                for b in range(a + 1, len(groups)):
                    score = max(similarity(i, j, resolved, vecs) for i in groups[a] for j in groups[b])
                    if best is None or score > best[0]:
                        best = (score, a, b)
            _, a, b = best
            groups[a].extend(groups[b])
            del groups[b]
        groups = [[resolved[i] for i in g] for g in groups]
    if unanswered:
        groups.append(unanswered)
    while len(groups) > 5:
        groups[-2].extend(groups[-1])
        groups.pop()
    return groups


def strip_citation(text):
    text = re.sub(r"\s*\([^)]*(?:\.\w+|:\d+)[^)]*\)\.?$", "", clean(text))
    return text.strip(" .")


def answer_summary(group):
    if all(unresolved(r) for r in group):
        return "The source poses the decision but does not commit to an answer."
    candidates = [strip_citation(r["a"]) for r in group if not unresolved(r)]
    candidates.sort(key=lambda s: (len(s), s.lower()))
    base = candidates[0] if candidates else "No explicit answer is supplied"
    if len(base) > 280:
        base = base[:277].rsplit(" ", 1)[0] + "..."
    return base[0].upper() + base[1:] if base else "No explicit answer is supplied."


def camp_name(group, summary, used):
    if all(unresolved(r) for r in group):
        name = "Decision left open"
    else:
        tags = Counter(t for r in group for t in polarity(r["a"]))
        preferred = [
            ("hybrid", "Hybrid or layered strategy"), ("manual", "Explicit admission"),
            ("automatic", "Automatic handling"), ("retain", "Retain with history"),
            ("overwrite", "Replace current state"), ("abstain", "Abstain or withhold"),
            ("ask", "Ask or confirm"), ("semantic", "Semantic retrieval"),
            ("lexical", "Lexical retrieval"), ("structured", "Structured constraints"),
            ("all", "Broad inclusion"), ("none", "Exclusion or empty result"),
            ("conditional", "Policy-dependent handling"),
        ]
        name = next((label for tag, label in preferred if tags[tag]), "")
        if not name:
            words = [w for w, _ in Counter(tokens(summary)).most_common(4)]
            name = " ".join(words).capitalize() or "Stated position"
    original = name
    suffix = 2
    while name in used:
        name = f"{original} {suffix}"
        suffix += 1
    used.add(name)
    return name


def assumptions(group):
    text = " ".join(clean(r.get("a")) for r in group).lower()
    parts = []
    if re.search(r"latency|synchronous|inline|real[- ]time", text): parts.append("the stated latency budget applies")
    if re.search(r"scale|large|million|volume|bounded|top[- ]?k", text): parts.append("the described scale and bounded context apply")
    if re.search(r"privacy|sensitive|consent|permission|third.party", text): parts.append("the stated privacy and consent boundary is enforceable")
    if re.search(r"graph|table|document|episode|claim|turn|message", text): parts.append("the described data unit and shape are stable")
    if re.search(r"fail|risk|cost|critical|safety", text): parts.append("the indicated failure cost governs")
    if not parts: parts.append("the source's described workload, data shape, and operating constraints apply")
    return "; ".join(parts[:3]) + "."


def shared_assumption(canonical, rows):
    if not rows:
        return "No source rows matched this cluster, so no shared assumption can be established."
    if all(unresolved(r) for r in rows):
        return "Every source treats the canonical question as an unresolved design choice rather than documenting an implemented position."
    subject = clean(canonical).rstrip("?")
    return f"Every camp assumes that the system must make or embody a determinate choice about: {subject[0].lower() + subject[1:]}."


def split_label(groups, total_sources):
    if not groups or total_sources == 0:
        return "CONTESTED (no majority)"
    counts = [len(set(r["src"] for r in g)) for g in groups]
    top = max(counts)
    if len(groups) == 1 and top == total_sources:
        return "UNANIMOUS (all agree)"
    if top > total_sources / 2:
        return f"MAJORITY-{top} ({top} of {total_sources} agree)"
    return "CONTESTED (no majority)"


def load_rows_for_cluster(member_set):
    selected = []
    # Intentionally open one JSONL source at a time and retain only matching rows.
    for path in sorted(EXTRACTED.glob("*")):
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if clean(row.get("q")) in member_set:
                    selected.append(row)
    return selected


def render(cluster, rows):
    sources = sorted(set(clean(r.get("src")) for r in rows if clean(r.get("src"))))
    hard_sources = set(clean(r.get("src")) for r in rows if r.get("hard") and clean(r.get("src")))
    groups = cluster_rows(rows)
    lines = [
        f'# {cluster["id"]}: {clean(cluster["canonical"])}',
        f'**Stage:** {clean(cluster["stage"])} · **Sources:** {len(sources)} · **Marked load-bearing by:** {len(hard_sources)}',
        '', '## Camps',
    ]
    if not groups:
        lines += ['', '### No matched source position', '- **Answer:** No extracted row matched this cluster’s member questions.', '- **Taken by:** none', '- **Assumes:** no source-specific setting can be inferred.']
    else:
        used = set()
        for group in groups:
            summary = answer_summary(group)
            name = camp_name(group, summary, used)
            taken = ", ".join(sorted(set(clean(r.get("src")) for r in group if clean(r.get("src"))))) or "none"
            lines += ['', f'### {name}', f'- **Answer:** {summary}', f'- **Taken by:** {taken}', f'- **Assumes:** {assumptions(group)}']
    lines += ['', '## Shared assumption', shared_assumption(clean(cluster["canonical"]), rows), '', '## Split', split_label(groups, len(sources)), '']
    return "\n".join(lines)


def main():
    with CLUSTERS.open("r", encoding="utf-8-sig") as fh:
        clusters = json.load(fh)["clusters"]
    MERGED.mkdir(exist_ok=True)
    for index, cluster in enumerate(clusters, 1):
        members = {clean(q) for q in cluster.get("members", [])}
        rows = load_rows_for_cluster(members)
        output = MERGED / f'{cluster["id"]}.md'
        output.write_text(render(cluster, rows), encoding="utf-8", newline="\n")
        print(f'[{index}/{len(clusters)}] {cluster["id"]}: {len(rows)} rows -> {output.name}', flush=True)


if __name__ == "__main__":
    main()
