import json

with open('data/proj_map.json', 'r') as f:
    proj_map = json.load(f)

by_proj = {}
for k, proj in proj_map.items():
    if proj['parallels'] is None:
        print(f"Skipping {k} as it does not have parallels")

    if proj['convergence'] is None:
        print(f"Skipping {k} as it does not have convergence")

    proj_str = json.dumps(proj)  # Ensure proj is JSON serializable
    if proj_str not in by_proj:
        by_proj[proj_str] = []
    by_proj[proj_str].append(k)

for proj_str, keys in by_proj.items():
    if len(keys) == 1:
        print(f"Unique projection for {keys[0]}: {proj_str}")
