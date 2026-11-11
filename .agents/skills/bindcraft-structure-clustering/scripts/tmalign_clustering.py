#!/usr/bin/env python3
"""按 B 链 TM-score 和 Average_dG 聚类 BindCraft 设计。"""
import argparse
import math
import os
import re
import subprocess
import sys
from itertools import combinations
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

NAME_COLUMNS = ('design_name', 'Design', 'Name', 'description', 'Description')


def normalize_name(name):
    return re.sub(r'[^A-Za-z0-9]+', '', Path(str(name)).stem).lower()


def pdb_key(name):
    stem = Path(str(name)).stem
    stem = re.sub(r'_chain[A-Za-z0-9]+$', '', stem)
    stem = re.sub(r'_model\d+$', '', stem)
    return re.sub(r'[^A-Za-z0-9]+', '', stem).lower()


def extract_chain(source, dest, chain):
    kept = ca = 0
    with source.open() as src, dest.open('w') as out:
        for line in src:
            rec = line[:6].strip()
            if rec in {'ATOM', 'HETATM', 'ANISOU', 'TER'}:
                if len(line) > 21 and line[21].strip() == chain:
                    out.write(line)
                    kept += 1
                    if rec == 'ATOM' and line[12:16].strip() == 'CA':
                        ca += 1
            elif rec in {'MODEL', 'ENDMDL', 'END'}:
                out.write(line)
    if not kept or not ca:
        raise ValueError(f'{source.name}: 链 {chain} 不存在或没有 ATOM CA 原子')


def align(task):
    p1, p2, executable = task
    try:
        p = subprocess.run([str(executable), str(p1), str(p2)], capture_output=True, text=True, check=True)
        scores = [float(line.split('=')[1].split()[0]) for line in p.stdout.splitlines() if 'TM-score=' in line]
        if len(scores) < 2 or not all(math.isfinite(x) for x in scores[:2]):
            raise ValueError('未找到两个有效 TM-score')
        return (p1.name, p2.name, sum(scores[:2]) / 2)
    except (OSError, subprocess.CalledProcessError, ValueError, IndexError) as exc:
        raise RuntimeError(f'TMalign 失败: {p1.name} / {p2.name}: {exc}') from exc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdb-dir', type=Path, required=True, help='复合物 PDB 目录')
    p.add_argument('--metrics', type=Path, required=True, help='含设计名和 Average_dG 的 CSV')
    p.add_argument('--tmalign', type=Path, required=True, help='TMalign 可执行文件')
    p.add_argument('--output', type=Path, required=True, help='全新输出目录，不可已存在')
    p.add_argument('--chain', default='B', help='binder 链 ID，默认 B')
    p.add_argument('--threshold', type=float, default=0.5, help='相似度阈值，默认 0.5')
    p.add_argument('--workers', type=int, default=1, help='并行进程数，默认 1')
    args = p.parse_args()
    if len(args.chain) != 1 or not args.chain.isalnum():
        raise ValueError('--chain 必须为一个字母或数字')
    if not math.isfinite(args.threshold) or not 0 <= args.threshold <= 1:
        raise ValueError('--threshold 必须在 0 到 1 之间')
    if args.workers < 1:
        raise ValueError('--workers 必须至少为 1')
    exe = args.tmalign.resolve()
    if not exe.is_file() or not os.access(exe, os.X_OK):
        raise ValueError(f'TMalign 不存在或不可执行: {exe}')
    if not args.pdb_dir.is_dir():
        raise ValueError(f'PDB 目录不存在: {args.pdb_dir}')
    pdbs = sorted(args.pdb_dir.glob('*.pdb'))
    if not pdbs:
        raise ValueError(f'PDB 目录中没有 .pdb 文件: {args.pdb_dir}')
    df = pd.read_csv(args.metrics)
    name_col = next((c for c in NAME_COLUMNS if c in df.columns), None)
    if not name_col or 'Average_dG' not in df.columns:
        raise ValueError('CSV 缺少设计名列或 Average_dG 列')
    table = {}
    for _, row in df.iterrows():
        key = normalize_name(row[name_col])
        # 与原脚本一致：名称归一化后重复时，使用最后一行。
        table[key] = row['Average_dG']
    energies = []
    for pdb in pdbs:
        key = pdb_key(pdb.name)
        if key not in table:
            raise ValueError(f'CSV 中找不到对应设计: {pdb.name}')
        try:
            energy = float(table[key])
        except (ValueError, TypeError):
            raise ValueError(f'{pdb.name} 对应的 Average_dG 不是有效数值')
        if not math.isfinite(energy):
            raise ValueError(f'{pdb.name} 对应的 Average_dG 不是有限数值')
        energies.append(energy)
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    chains = out / f'binder_chain_{args.chain}_pdbs'
    chains.mkdir()
    paths = [chains / f'{x.stem}_chain{args.chain}.pdb' for x in pdbs]
    for source, dest in tqdm(zip(pdbs, paths), total=len(pdbs), desc='提取链'):
        extract_chain(source, dest, args.chain)
    names = [x.name for x in paths]
    index = {name: i for i, name in enumerate(names)}
    matrix = np.eye(len(names), dtype=float)
    tasks = ((a, b, exe) for a, b in combinations(paths, 2))
    total = len(paths) * (len(paths)-1) // 2
    print(f'结构数: {len(paths)}; 两两比对数: {total}; 进程数: {args.workers}', flush=True)
    with Pool(args.workers) as pool:
        for a, b, score in tqdm(pool.imap(align, tasks), total=total, desc='TM-align'):
            i, j = index[a], index[b]
            matrix[i, j] = matrix[j, i] = score
    tm = pd.DataFrame(matrix, index=names, columns=names)
    tm.to_csv(out / 'global_tm_matrix.csv', encoding='utf-8-sig')
    remaining = sorted(range(len(paths)), key=lambda i: energies[i])
    clusters = []
    while remaining:
        center = remaining[0]
        members = [center] + [i for i in remaining[1:] if matrix[center, i] >= args.threshold]
        removed = set(members)
        remaining = [i for i in remaining if i not in removed]
        clusters.append((center, members))
        print(f'Cluster {len(clusters)} | size={len(members)}')
    rows, center_rows = [], []
    pair_dir = out / 'cluster_pairwise_tm_matrices'
    pair_dir.mkdir()
    with (out / 'clustering.txt').open('w', encoding='utf-8') as f:
        f.write(f'TM threshold = {args.threshold}\nClustering = energy-prioritized greedy assignment using precomputed global TM matrix\n\n')
        for cid, (center, members) in enumerate(clusters, 1):
            center_rows.append({'cluster_id':cid, 'center':names[center], 'cluster_size':len(members), 'center_energy':energies[center]})
            f.write(f'Cluster {cid} (size={len(members)})\n  Center: {names[center]} energy={energies[center]:.4f}\n')
            for i in members:
                score = matrix[center, i]
                rows.append({'cluster_id':cid, 'member':names[i], 'center':names[center], 'energy':energies[i], 'tm_to_center':score})
                f.write(f'    {names[i]}  energy={energies[i]:.4f}  TM={score:.4f}\n')
            f.write('\n')
            if len(members) >= 2:
                member_names = [names[i] for i in members]
                tm.loc[member_names, member_names].to_csv(pair_dir / f'cluster_{cid}_tm_matrix.csv', encoding='utf-8-sig')
    pd.DataFrame(rows).to_csv(out / 'clusters.csv', index=False)
    pd.DataFrame(center_rows).to_csv(out / 'centers.csv', index=False)
    print(f'完成：{len(clusters)} 个簇，结果目录: {out}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, pd.errors.ParserError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)
