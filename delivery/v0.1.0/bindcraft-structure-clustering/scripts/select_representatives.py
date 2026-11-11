from __future__ import annotations

import math
import argparse
import re
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd




def parse_clustering_txt(path: Path) -> List[dict]:
    clusters: List[dict] = []
    current = None

    cluster_pat = re.compile(r'^Cluster\s+(\d+)\s+\(size=(\d+)\)')
    center_pat = re.compile(r'^\s*Center:\s+(\S+)\s+energy=([-+]?\d*\.?\d+)')
    member_pat = re.compile(
        r'^\s+(\S+)\s+energy=([-+]?\d*\.?\d+)\s+TM=([-+]?\d*\.?\d+|nan)',
        re.IGNORECASE,
    )

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')

            m = cluster_pat.match(line)
            if m:
                if current is not None:
                    clusters.append(current)
                current = {
                    'cluster_id': int(m.group(1)),
                    'cluster_size': int(m.group(2)),
                    'center': None,
                    'center_energy': None,
                    'members': [],
                }
                continue

            if current is None:
                continue

            m = center_pat.match(line)
            if m:
                current['center'] = m.group(1)
                current['center_energy'] = float(m.group(2))
                continue

            m = member_pat.match(line)
            if m:
                tm = m.group(3)
                current['members'].append(
                    {
                        'pdb': m.group(1),
                        'energy': float(m.group(2)),
                        'tm_to_center': np.nan if str(tm).lower() == 'nan' else float(tm),
                    }
                )

    if current is not None:
        clusters.append(current)

    return clusters


def write_csv_with_fallback(df: pd.DataFrame, out_path: Path) -> Path:
    df.to_csv(out_path, index=False, encoding='utf-8-sig', mode='x')
    return out_path


def constrained_kennard_stone(
    member_names: List[str],
    tm_df: pd.DataFrame,
    center_name: str,
    n_select: int,
) -> List[dict]:
    if n_select <= 0:
        return []
    if center_name not in member_names:
        raise ValueError(f'Center {center_name} not found in cluster members')

    if n_select == 1:
        return [
            {
                'pdb': center_name,
                'distance_to_selected_set_at_selection': np.nan,
                'selected_against': 'center_fixed_anchor',
            }
        ]

    names = list(member_names)
    selected = [center_name]
    selected_meta = [
        {
            'pdb': center_name,
            'distance_to_selected_set_at_selection': np.nan,
            'selected_against': 'center_fixed_anchor',
        }
    ]
    remaining = [n for n in names if n != center_name]

    while remaining and len(selected) < n_select:
        best_name = None
        best_score = -math.inf
        best_against = None

        for cand in remaining:
            distances = []
            for s in selected:
                tm = tm_df.loc[cand, s]
                if pd.isna(tm):
                    dist = -math.inf
                else:
                    dist = 1.0 - float(tm)
                distances.append((s, dist))

            min_dist = min(dist for _, dist in distances)
            against = ';'.join(
                s for s, dist in distances if abs(dist - min_dist) <= 1e-12
            )
            if min_dist > best_score:
                best_score = min_dist
                best_name = cand
                best_against = against

        if best_name is None:
            break

        selected.append(best_name)
        selected_meta.append(
            {
                'pdb': best_name,
                'distance_to_selected_set_at_selection': best_score,
                'selected_against': best_against,
            }
        )
        remaining.remove(best_name)

    return selected_meta


def main():
    parser = argparse.ArgumentParser(description='按当前配额选取固定中心的代表结构，不覆盖输出。')
    parser.add_argument('--clustering', type=Path, required=True)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'输出已存在: {args.output}')
    tm_df = pd.read_csv(args.matrix, index_col=0)
    plan_df = pd.read_csv(args.plan)
    clusters = parse_clustering_txt(args.clustering)

    required_columns = {'cluster_id', 'recommended_n_for_MD'}
    if not required_columns.issubset(plan_df.columns):
        raise ValueError(f'配额表缺少列: {sorted(required_columns - set(plan_df.columns))}')
    cluster_map = {cluster['cluster_id']: cluster for cluster in clusters}
    if len(cluster_map) != len(clusters) or not clusters:
        raise ValueError('聚类结果为空或存在重复的簇编号')
    plan_map = {}
    for row_number, row in plan_df.iterrows():
        values = []
        for col in ('cluster_id', 'recommended_n_for_MD'):
            try:
                value = float(row[col])
            except (ValueError, TypeError):
                raise ValueError(f'配额表第 {row_number + 2} 行 {col} 必须是整数')
            if not math.isfinite(value) or not value.is_integer():
                raise ValueError(f'配额表第 {row_number + 2} 行 {col} 必须是有限整数')
            values.append(int(value))
        cid, target = values
        if cid in plan_map:
            raise ValueError(f'配额表中簇 {cid} 重复')
        if cid not in cluster_map:
            raise ValueError(f'配额表中的簇 {cid} 不存在于聚类结果')
        if target < 0:
            raise ValueError(f'簇 {cid} 的配额不能为负数')
        cluster = cluster_map[cid]
        actual_size = len(cluster['members'])
        if actual_size != cluster['cluster_size']:
            raise ValueError(f'簇 {cid} 声明成员数与解析成员数不一致')
        if target > actual_size:
            raise ValueError(f'簇 {cid} 的配额 {target} 超过成员数 {actual_size}')
        plan_map[cid] = target
    if not plan_map or not sum(plan_map.values()):
        raise ValueError('配额表为空或所有配额均为 0')
    skipped = sorted(set(cluster_map) - set(plan_map))
    if skipped:
        print(f'提示：配额表未列出以下簇，将跳过：{skipped}')
    print(f'配额检查通过：{len(plan_map)} 个簇，计划选取 {sum(plan_map.values())} 个结构')

    rows = []
    for cluster in clusters:
        cid = cluster['cluster_id']
        if cid not in plan_map:
            continue

        target_n = plan_map[cid]
        members = cluster['members']
        member_names = [m['pdb'] for m in members]
        member_map: Dict[str, dict] = {m['pdb']: m for m in members}
        center_name = cluster['center']

        selected_records = constrained_kennard_stone(
            member_names=member_names,
            tm_df=tm_df,
            center_name=center_name,
            n_select=target_n,
        )

        if len(selected_records) != target_n:
            raise ValueError(
                f'簇 {cid} 计划选取 {target_n} 个，实际仅选出 {len(selected_records)} 个；请检查 TM-score 矩阵'
            )

        for rank, record in enumerate(selected_records, start=1):
            name = record['pdb']
            member = member_map[name]
            if name == center_name:
                reason = 'center_lowest_energy'
                note = (
                    'Cluster center in this greedy clustering workflow is defined as the '
                    'lowest-energy structure; keep it as the anchor representative.'
                )
            else:
                reason = 'kennard_stone_tm_distance'
                note = (
                    'Selected by constrained Kennard-Stone using exact within-cluster '
                    'pairwise TM distances (distance = 1 - TM-score), with the cluster '
                    'center fixed as the first selected representative.'
                )

            rows.append(
                {
                    'cluster_id': cid,
                    'cluster_size': cluster['cluster_size'],
                    'selection_rank': rank,
                    'pdb': name,
                    'energy': member['energy'],
                    'tm_to_center': member['tm_to_center'],
                    'distance_to_selected_set_at_selection': record['distance_to_selected_set_at_selection'],
                    'selected_against': record['selected_against'],
                    'selection_reason': reason,
                    'note': note,
                }
            )

    out_df = pd.DataFrame(rows)
    written_path = write_csv_with_fallback(out_df, args.output)
    print(f'Wrote {len(out_df)} rows to {written_path}')


if __name__ == '__main__':
    main()
