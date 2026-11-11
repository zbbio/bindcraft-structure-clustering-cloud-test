"""Suggest a bounded square-root proportional quota; no structures are selected."""
import argparse
import math
from pathlib import Path

import pandas as pd


def allocate(sizes, total):
    """At least one center each; bounded largest-deficit allocation, ID ties.

    Target share = total * sqrt(size) / sum(sqrt(size)). Start with its floor
    bounded by [1,size], then add/remove by largest deviation from target.
    """
    if not sizes or any(not isinstance(n, int) or n < 1 for n in sizes.values()):
        raise ValueError('Eligible cluster sizes must be positive integers')
    if not isinstance(total, int) or not len(sizes) <= total <= sum(sizes.values()):
        raise ValueError(f'Total must be between {len(sizes)} and {sum(sizes.values())}; choose another total or cluster scope')
    weights = {cid: math.sqrt(n) for cid, n in sizes.items()}
    denom = math.fsum(weights.values())
    ideals = {cid: total*w/denom for cid,w in weights.items()}
    quota = {cid: min(sizes[cid], max(1, math.floor(ideals[cid]))) for cid in sizes}
    while sum(quota.values()) < total:
        eligible = [cid for cid in sizes if quota[cid] < sizes[cid]]
        cid = min(eligible, key=lambda c: (-(ideals[c]-quota[c]), c))
        quota[cid] += 1
    while sum(quota.values()) > total:
        eligible = [cid for cid in sizes if quota[cid] > 1]
        cid = min(eligible, key=lambda c: (-(quota[c]-ideals[c]), c))
        quota[cid] -= 1
    return quota


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--centers', type=Path, required=True)
    parser.add_argument('--total', type=int, default=100)
    parser.add_argument('--min-n', type=int, default=5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.min_n < 1 or args.total < 1:
        raise ValueError('total and min-n must be positive')
    df = pd.read_csv(args.centers)
    if not {'cluster_id','cluster_size'}.issubset(df.columns) or df.empty:
        raise ValueError('centers CSV needs cluster_id and cluster_size rows')
    sizes = {}
    for row in df.itertuples(index=False):
        cid, size = float(row.cluster_id), float(row.cluster_size)
        if not all(math.isfinite(x) and x.is_integer() and x > 0 for x in (cid,size)):
            raise ValueError('cluster_id and cluster_size must be positive integers')
        cid, size = int(cid), int(size)
        if cid in sizes:
            raise ValueError(f'Duplicate cluster_id {cid}')
        sizes[cid] = size
    eligible = {cid:n for cid,n in sizes.items() if n >= args.min_n}
    if not eligible:
        raise ValueError(f'No clusters satisfy min_n={args.min_n}; choose another scope explicitly')
    quota = allocate(eligible, args.total)
    rows = [{'cluster_id':cid,'recommended_n_for_MD':quota.get(cid,0)} for cid in sorted(sizes)]
    pd.DataFrame(rows).to_csv(args.output,index=False,encoding='utf-8-sig',mode='x')
    print(f'Suggested quota: {args.total} structures across {len(eligible)} clusters; min_n={args.min_n}')
    print(f'Output: {args.output}; review quotas before selection. No structure selection performed.')


if __name__ == '__main__':
    main()
