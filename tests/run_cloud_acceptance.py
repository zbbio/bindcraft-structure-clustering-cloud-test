"""Execute and verify this private repository's CA-only technical acceptance test."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.agents/skills/bindcraft-structure-clustering'
FIXTURES = ROOT / 'tests/fixtures'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--tmalign', type=Path, default=ROOT / '.tools/TMalign')
    args = parser.parse_args()
    output = (args.output or ROOT / 'results' / datetime.now(timezone.utc).strftime('run_%Y%m%d_%H%M%S_%f')).resolve()
    output.mkdir(parents=True, exist_ok=False)
    selection, figures = output / 'selection', output / 'visualization'
    selection.mkdir()
    figures.mkdir()
    result = output / 'clustering'
    protected = {str(p.relative_to(ROOT)): sha(p) for parent in [SKILL, FIXTURES]
                 for p in parent.rglob('*') if p.is_file()}
    env = dict(os.environ, MPLBACKEND='Agg', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    report = {'status': 'RUNNING', 'output': str(output), 'python': sys.executable,
              'fixture_type': 'CA-only coordinate subsets of nine supplied tutorial structures',
              'threshold': 0.5, 'chain': 'B', 'workers': 1,
              'test_only_min_n': 1, 'test_only_total': 6,
              'commands': []}

    def save():
        (output / 'commands.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    def cli(name, *params):
        command = list(map(str, [sys.executable, SKILL / 'scripts' / name, *params]))
        print('RUN', name, flush=True)
        completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                   text=True, encoding='utf-8', timeout=300)
        report['commands'].append({'argv': command, 'cwd': str(ROOT),
                                   'environment_overrides': {k: env[k] for k in ['MPLBACKEND', 'PYTHONUTF8', 'PYTHONDONTWRITEBYTECODE']},
                                   'exit_status': completed.returncode,
                                   'stdout': completed.stdout, 'stderr': completed.stderr})
        save()
        print(completed.stdout, flush=True)
        if completed.returncode:
            raise RuntimeError(f'{name} failed with exit status {completed.returncode}; see commands.json')
        return completed

    try:
        save()
        cli('tmalign_clustering.py', '--pdb-dir', FIXTURES / 'pdb', '--metrics', FIXTURES / 'metrics.csv',
            '--tmalign', args.tmalign.resolve(), '--output', result,
            '--chain', 'B', '--threshold', '0.5', '--workers', '1')
        cli('suggest_quota.py', '--centers', result / 'centers.csv', '--min-n', '1', '--total', '6',
            '--output', selection / 'plan.csv')
        cli('select_representatives.py', '--clustering', result / 'clustering.txt',
            '--matrix', result / 'global_tm_matrix.csv', '--plan', selection / 'plan.csv',
            '--output', selection / 'selected.csv')
        cli('plot_all_clusters.py', result / 'clustering.txt', '--min-n', '1',
            '--out-csv', figures / '01_all_parsed.csv', '--out-png', figures / '01_all_clusters.png')
        cli('plot_main_clusters.py', result / 'clustering.txt', '--min-n', '1',
            '--out-csv', figures / '02_main_parsed.csv', '--out-png', figures / '02_main_clusters.png')
        overlay = cli('plot_selected_overlay.py', '--clustering', result / 'clustering.txt',
                      '--selected', selection / 'selected.csv', '--min-n', '1',
                      '--output', figures / '03_main_selected.png')

        matrix = pd.read_csv(result / 'global_tm_matrix.csv', index_col=0)
        reference = pd.read_csv(FIXTURES / 'expected_tm_matrix.csv', index_col=0)
        members = pd.read_csv(result / 'clusters.csv')
        centers = pd.read_csv(result / 'centers.csv')
        plan = pd.read_csv(selection / 'plan.csv')
        selected = pd.read_csv(selection / 'selected.csv')
        assert matrix.shape == (9, 9)
        assert set(matrix.index) == set(matrix.columns) == set(members.member)
        values = matrix.loc[matrix.index, matrix.index].to_numpy()
        assert np.isfinite(values).all() and np.allclose(values, values.T)
        assert np.allclose(np.diag(values), 1)
        delta = float(np.max(np.abs(values - reference.loc[matrix.index, matrix.index].to_numpy())))
        assert delta <= 0.0002, f'Recompiled TMalign differs from the labelled reference by {delta}'
        assert len(members) == members.member.nunique() == 9
        assert sorted(centers.cluster_size.tolist()) == [3, 3, 3]
        assert members.groupby('cluster_id').size().to_dict() == centers.set_index('cluster_id').cluster_size.to_dict()
        for center in centers.itertuples():
            group = members[members.cluster_id == center.cluster_id]
            assert (matrix.loc[center.center, group.member] >= 0.5).all()
        assert plan.recommended_n_for_MD.sum() == 6
        assert selected.pdb.is_unique and len(selected) == 6
        assert set(selected.pdb) <= set(members.member)
        assert set(centers.center) <= set(selected.pdb)
        assert selected.groupby('cluster_id').size().to_dict() == plan.set_index('cluster_id').recommended_n_for_MD.to_dict()
        for cid, group in selected.groupby('cluster_id'):
            ordered = group.sort_values('selection_rank').pdb.tolist()
            assert ordered[0] == centers.set_index('cluster_id').loc[cid, 'center']
            candidates = set(members[members.cluster_id == cid].member)
            anchors = [ordered[0]]
            for name in ordered[1:]:
                distances = {n: min(1 - matrix.loc[n, a] for a in anchors) for n in candidates - set(anchors)}
                assert np.isclose(distances[name], max(distances.values()), atol=1e-12)
                anchors.append(name)
        assert '名单 6，聚类匹配 6，展示范围匹配 6' in overlay.stdout
        images = []
        for file in sorted(figures.glob('*.png')):
            with Image.open(file) as im:
                size = im.size
                im.verify()
            assert min(size) > 1000 and file.stat().st_size > 1000
            images.append({'path': str(file), 'size': list(size), 'sha256': sha(file)})
        assert len(images) == 3
        assert all(sha(ROOT / name) == value for name, value in protected.items())
        report.update(status='PASS', structure_count=9, actual_pairs=36,
                      cluster_sizes=[3, 3, 3], selected_count=6, images=images,
                      max_reference_matrix_difference=delta,
                      skill_and_fixtures_unchanged=True,
                      limits='CA-only technical fixtures, not full-atom or new biological validation. Execution location must be reported by the actual runner; this script alone does not prove cloud execution.')
        save()
        (output / 'summary.json').write_text(json.dumps({k: v for k, v in report.items() if k != 'commands'}, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PASS:', output / 'summary.json', flush=True)
    except BaseException as error:
        report.update(status='FAIL', error=repr(error))
        save()
        raise


if __name__ == '__main__':
    main()
