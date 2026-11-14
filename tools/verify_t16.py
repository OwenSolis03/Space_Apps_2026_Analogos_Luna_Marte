"""Independent verification script for T16 (plan_t16_missing_data.md §9.3)."""
import collections
import json
import sys


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "app/public/data/analogs_universe.json"
    print(f"Loading {path}...")
    with open(path, encoding="utf-8") as f:
        u = json.load(f)

    P = u["mission_presets"]
    pol = u["metadata"].get("scoring_policy", {})
    zero = pol.get("earth_missing_score", 0.0)

    def msi(a, w, dims):
        num = den = 0.0
        for d, wd in w.items():
            if wd <= 0 or (dims is not None and d not in dims):
                continue
            s = a["sub_scores"].get(d)
            if s is None:
                if dims is None:
                    continue
                s = zero
            num += wd * s
            den += wd
        return num / den if den else None

    bad = 0
    for body in ("Mars", "Moon"):
        T = [t for t in u["targets"] if t["body"] == body]
        for p, spec in P.items():
            st = collections.Counter(t.get("preset_status", {}).get(p, {}).get("status", "?") for t in T)
            ranked = [t for t in T if t.get("preset_status", {}).get(p, {}).get("status") == "ok"]
            tops = [
                max(
                    t["analogs"],
                    key=lambda a: a["msi_by_preset"][p] if a["msi_by_preset"][p] is not None else -1,
                )
                for t in ranked
            ]
            ant = sum(1 for a in tops if a["country"] == "Antarctica")
            key = max(spec["weights"], key=spec["weights"].get)
            nul = sum(1 for a in tops if key in (a.get("earth_missing_dims") or []))
            print(f"{body:4} {p:24} status={dict(st)} ranked={len(ranked)} top1_antarctica={ant} top1_missing_{key}={nul}")
            for t in ranked:
                for a in t["analogs"]:
                    ref = a["msi_by_preset"][p]
                    got = msi(a, spec["weights"], set(t.get("available_dims", [])) or None)
                    if ref is not None and got is not None and abs(ref - got) > 0.002:
                        bad += 1
    print("hard check 12 violations:", bad)
    if bad > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
