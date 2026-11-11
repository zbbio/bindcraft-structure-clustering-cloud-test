import re
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from output_guard import new_outputs




plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 11,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 11,
    "axes.linewidth": 0.9,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def parse_cluster_file(txt_path: Path) -> pd.DataFrame:
    text = txt_path.read_text(encoding="utf-8", errors="ignore")
    rows = []
    current_cluster = None
    current_size = None

    for line in text.splitlines():
        line_stripped = line.strip()

        m = re.match(r'^Cluster\s+(\d+)\s+\(size=(\d+)\)', line_stripped)
        if m:
            current_cluster = int(m.group(1))
            current_size = int(m.group(2))
            continue

        if line_stripped.startswith("Center:"):
            continue

        if ".pdb" in line_stripped:
            parts = line_stripped.split()
            pdb_id = parts[0]
            energy = None
            tm = None

            for p in parts[1:]:
                if p.startswith("energy="):
                    try:
                        energy = float(p.split("=")[1])
                    except Exception:
                        pass
                elif p.startswith("TM=") or p.startswith("TM_to_center="):
                    try:
                        tm = float(p.split("=")[1])
                    except Exception:
                        pass

            if energy is not None and current_cluster is not None:
                rows.append({
                    "id": pdb_id,
                    "cluster": f"Cluster {current_cluster}",
                    "cluster_num": current_cluster,
                    "cluster_size": current_size,
                    "binding_energy": energy,
                    "TM_to_center": tm,
                })

    if not rows:
        raise ValueError("No member rows were parsed. Please check clustering.txt.")
    return pd.DataFrame(rows)


def _clip_violin_to_upper_half(body, center_y: float) -> None:
    for path in body.get_paths():
        vertices = path.vertices
        vertices[:, 1] = np.maximum(vertices[:, 1], center_y)


def get_publication_palette(n: int):
    palette = [
        "#4E79A7",
        "#F28E2B",
        "#59A14F",
        "#E15759",
        "#9C755F",
        "#B07AA1",
        "#76B7B2",
        "#8C8C8C",
        "#B5BD2F",
        "#17BECF",
        "#7F3C8D",
        "#BCBD22",
    ]
    if n <= len(palette):
        return palette[:n]
    return [palette[i % len(palette)] for i in range(n)]


def main():
    parser = argparse.ArgumentParser(description='主要簇与已选结构叠加图，使用本次输入和全新输出。')
    parser.add_argument('--clustering', type=Path, required=True)
    parser.add_argument('--selected', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--min-n', type=int, default=5)
    args = parser.parse_args()
    if args.min_n < 1:
        raise ValueError('--min-n 至少为 1')
    df = parse_cluster_file(args.clustering)
    selected_csv = args.selected
    selected_df = pd.read_csv(selected_csv)
    selected_col = "design" if "design" in selected_df.columns else "pdb"
    selected_ids = set(selected_df[selected_col].astype(str))
    if len(selected_ids) != len(selected_df):
        raise ValueError('名单存在重复名称')
    unmatched = selected_ids - set(df['id'])
    if unmatched:
        raise ValueError(f'名单有 {len(unmatched)} 个名称未匹配当前聚类: {sorted(unmatched)}')

    counts = df.groupby("cluster_num").size()
    keep = counts[counts >= args.min_n].index.tolist()
    plot_df = df[df["cluster_num"].isin(keep)].copy()
    if plot_df.empty:
        raise ValueError(f'没有成员数至少为 {args.min_n} 的簇')
    displayed_selected = selected_ids & set(plot_df['id'])
    print(f'名单 {len(selected_ids)}，聚类匹配 {len(selected_ids)}，展示范围匹配 {len(displayed_selected)}')

    stats = (
        plot_df.groupby(["cluster_num", "cluster"])
        .agg(n=("binding_energy", "size"), median_energy=("binding_energy", "median"))
        .reset_index()
        .sort_values(["n", "cluster_num"], ascending=[False, True])
    )

    ordered_clusters = stats["cluster_num"].tolist()
    ordered_labels = stats["cluster"].tolist()
    plot_df = plot_df[plot_df["cluster_num"].isin(ordered_clusters)].copy()

    grouped_values = []
    grouped_frames = []
    for c in ordered_clusters:
        sub = plot_df.loc[plot_df["cluster_num"] == c].copy().reset_index(drop=True)
        grouped_frames.append(sub)
        grouped_values.append(sub["binding_energy"].to_numpy())

    base_positions = np.arange(len(ordered_clusters), 0, -1, dtype=float)
    cloud_positions = base_positions + 0.23
    box_positions = base_positions + 0.05

    fig_height = max(4.8, 0.72 * len(ordered_clusters) + 0.8)
    fig, ax = plt.subplots(figsize=(8.8, fig_height))
    colors = get_publication_palette(len(ordered_clusters))

    # Cloud only: match the reference KDE raincloud style.
    for values, color, pos in zip(grouped_values, colors, cloud_positions):
        # A single value or constant values have no estimable density.
        if len(values) < 2 or np.ptp(values) == 0:
            continue
        try:
            kde = gaussian_kde(values, bw_method="scott")
        except (ValueError, np.linalg.LinAlgError):
            continue
        x_range = np.linspace(values.min() - 5, values.max() + 5, 300)
        density = kde(x_range)
        density = density / density.max() * 0.32
        ax.fill_between(x_range, pos, pos + density, color=color,
                        alpha=0.55, edgecolor="none")

    # Retain the original violinplot vertical autoscaling while changing the cloud.
    cloud_half_widths = [0.13 if len(x) > 1 and np.ptp(x) > 0 else 0.0 for x in grouped_values]
    ax.dataLim.intervaly = (min(pos - width for pos, width in zip(cloud_positions, cloud_half_widths)),
                            max(pos + width for pos, width in zip(cloud_positions, cloud_half_widths)))

    rng = np.random.default_rng(42)
    selected_x = []
    selected_y = []

    for sub, values, base_y, box_y, color in zip(grouped_frames, grouped_values, base_positions, box_positions, colors):
        jitter = rng.uniform(-0.32, -0.09, size=len(values))
        y = base_y + jitter
        sub["plot_y"] = y

        ax.scatter(
            sub["binding_energy"],
            sub["plot_y"],
            s=11,
            alpha=0.75,
            linewidths=0,
            color=color,
            zorder=3,
        )

        ax.boxplot(
            [values],
            vert=False,
            positions=[box_y],
            widths=0.10,
            patch_artist=True,
            manage_ticks=False,
            showfliers=False,
            boxprops=dict(facecolor="white", edgecolor="black", linewidth=1.0),
            medianprops=dict(color="black", linewidth=1.2),
            whiskerprops=dict(color="black", linewidth=1.0),
            capprops=dict(color="black", linewidth=1.0),
            zorder=4,
        )

        selected_rows = sub[sub["id"].isin(selected_ids)]
        selected_x.extend(selected_rows["binding_energy"].tolist())
        selected_y.extend(selected_rows["plot_y"].tolist())

    ax.scatter(
        selected_x,
        selected_y,
        s=64,
        facecolors="none",
        edgecolors="#d62728",
        linewidths=1.6,
        zorder=6,
        label=f"Selected structures ({len(displayed_selected)})",
    )

    ytick_labels = [
        f"{label} (n={int(stats.loc[stats['cluster_num'] == c, 'n'].iloc[0])})"
        for c, label in zip(ordered_clusters, ordered_labels)
    ]

    ax.set_yticks(base_positions)
    ax.set_yticklabels(ytick_labels)
    ax.set_xlabel("Binding energy")
    ax.set_ylabel("Cluster")
    ax.set_title("Raincloud plot of binding energy by cluster", fontsize=13, pad=10)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)
    ax.tick_params(axis="both", which="both", direction="out")
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.7, alpha=0.5)
    ax.grid(axis="y", visible=False)

    x_min = plot_df["binding_energy"].min()
    x_max = plot_df["binding_energy"].max()
    x_pad = max(3.0, 0.05 * (x_max - x_min))
    ax.set_xlim(x_min - x_pad, x_max + x_pad)

    ax.legend(loc="lower right", frameon=False, fontsize=10, handletextpad=0.6)

    plt.tight_layout()
    with new_outputs(args.output):
        fig.savefig(args.output, dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Selected CSV: {selected_csv}")
    print(f"[OK] Overlay PNG: {args.output}")


if __name__ == "__main__":
    main()
