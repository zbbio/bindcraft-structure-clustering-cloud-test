import argparse
from output_guard import new_outputs
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde


plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.family": "Arial",
    "font.size": 14,
    "axes.labelsize": 14,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "axes.linewidth": 0.9,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def parse_cluster_file(txt_path: str) -> pd.DataFrame:
    text = Path(txt_path).read_text(encoding="utf-8", errors="ignore")
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
            length = None

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
                elif p.startswith("len="):
                    try:
                        length = int(p.split("=")[1])
                    except Exception:
                        pass

            if energy is not None and current_cluster is not None:
                rows.append({
                    "id": pdb_id,
                    "cluster": f"Cluster {current_cluster}",
                    "cluster_num": current_cluster,
                    "cluster_size": current_size,
                    "length": length,
                    "binding_energy": energy,
                    "TM_to_center": tm,
                })

    if not rows:
        raise ValueError("No member rows were parsed. Please check the input file format.")

    return pd.DataFrame(rows)


def parse_energy_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    energy_col = None
    for candidate in ["Average_dG", "Average_Binder_Energy_Score", "binding_energy"]:
        if candidate in df.columns:
            energy_col = candidate
            break

    if energy_col is None:
        raise ValueError(
            "CSV input must contain one of these columns: "
            "Average_dG, Average_Binder_Energy_Score, binding_energy."
        )

    out = df.copy()
    out = out.rename(columns={energy_col: "binding_energy"})
    out["binding_energy"] = pd.to_numeric(out["binding_energy"], errors="coerce")
    out = out.dropna(subset=["binding_energy"]).copy()

    if out.empty:
        raise ValueError("No valid binding energy values were found in the CSV.")

    out["cluster"] = "All designs"
    out["cluster_num"] = 1
    out["cluster_size"] = len(out)

    if "Design" in out.columns:
        out["id"] = out["Design"]
    elif "design" in out.columns:
        out["id"] = out["design"]
    else:
        out["id"] = [f"design_{i + 1}" for i in range(len(out))]

    if "Length" not in out.columns:
        out["length"] = np.nan

    if "TM_to_center" not in out.columns:
        out["TM_to_center"] = np.nan

    return out[["id", "cluster", "cluster_num", "cluster_size", "length", "binding_energy", "TM_to_center"]]


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


def plot_raincloud(
    df: pd.DataFrame,
    out_png: str,
    min_n: int = 1,
    order_by: str = "size",
    max_clusters: int | None = None,
    connect_means: bool = False,
):
    counts = df.groupby("cluster_num").size()
    keep = counts[counts >= min_n].index.tolist()
    plot_df = df[df["cluster_num"].isin(keep)].copy()

    if plot_df.empty:
        raise ValueError(f"No clusters satisfy min_n >= {min_n}.")

    stats = (
        plot_df.groupby(["cluster_num", "cluster"])
        .agg(
            n=("binding_energy", "size"),
            median_energy=("binding_energy", "median"),
            mean_energy=("binding_energy", "mean"),
        )
        .reset_index()
    )

    if order_by == "size":
        stats = stats.sort_values(["n", "cluster_num"], ascending=[False, True])
    elif order_by == "median":
        stats = stats.sort_values(["median_energy", "cluster_num"], ascending=[True, True])
    else:
        stats = stats.sort_values(["cluster_num"], ascending=[True])

    if max_clusters is not None:
        stats = stats.head(max_clusters)

    ordered_clusters = stats["cluster_num"].tolist()
    plot_df = plot_df[plot_df["cluster_num"].isin(ordered_clusters)].copy()

    grouped = [
        plot_df.loc[plot_df["cluster_num"] == c, "binding_energy"].to_numpy()
        for c in ordered_clusters
    ]

    base_positions = np.arange(len(ordered_clusters), 0, -1, dtype=float)
    cloud_positions = base_positions + 0.23
    box_positions = base_positions + 0.05

    fig_height = max(3.0, 0.45 * len(ordered_clusters) + 0.5)
    fig, ax = plt.subplots(figsize=(7, fig_height))
    colors = get_publication_palette(len(ordered_clusters))

    # Cloud only: match the reference KDE raincloud style.
    for values, color, pos in zip(grouped, colors, cloud_positions):
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
    cloud_half_widths = [0.13 if len(x) > 1 and np.ptp(x) > 0 else 0.0 for x in grouped]
    ax.dataLim.intervaly = (min(pos - width for pos, width in zip(cloud_positions, cloud_half_widths)),
                            max(pos + width for pos, width in zip(cloud_positions, cloud_half_widths)))

    rng = np.random.default_rng(42)
    mean_x = []
    mean_y = []

    for values, base_y, box_y, color in zip(grouped, base_positions, box_positions, colors):
        jitter = rng.uniform(-0.32, -0.09, size=len(values))
        y = base_y + jitter
        ax.scatter(values, y, s=11, alpha=0.75, linewidths=0, color=color, zorder=3)

        ax.boxplot(
            [values],
            vert=False,
            positions=[box_y],
            widths=0.10,
            patch_artist=True,
            manage_ticks=False,
            showfliers=False,
            boxprops=dict(facecolor="white", edgecolor="black", linewidth=0.7),
            medianprops=dict(color="black", linewidth=0.8),
            whiskerprops=dict(color="black", linewidth=0.7),
            capprops=dict(color="black", linewidth=0.7),
            zorder=4,
        )

        mean_x.append(values.mean())
        mean_y.append(box_y)

    if connect_means:
        ax.plot(mean_x, mean_y, marker="o", linewidth=1.5, color="black", zorder=5)

    ytick_labels = [
        f"C{int(c)} (n={int(stats.loc[stats['cluster_num'] == c, 'n'].iloc[0])})"
        for c in ordered_clusters
    ]

    ax.set_yticks(base_positions)
    ax.set_yticklabels(ytick_labels)
    ax.set_xlabel("Rosetta dG_separated (REU)")
    ax.set_ylabel("Cluster")
    ax.set_title("Raincloud plot of binding energy by cluster", fontsize=14, pad=10)

    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)
    ax.tick_params(axis="both", which="both", direction="out")
    ax.grid(axis="x", color="#505050", linewidth=0.7, alpha=0.5, linestyle="--")

    x_min = plot_df["binding_energy"].min()
    x_max = plot_df["binding_energy"].max()
    x_pad = max(3.0, 0.05 * (x_max - x_min))
    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_xticks([-100, -90, -80, -70, -60, -50, -40])

    plt.tight_layout()
    fig.savefig(out_png, dpi=600, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Parse tm-score clustering text or CSV and plot raincloud.")
    parser.add_argument("input_txt", help="Input clustering text file or CSV")
    parser.add_argument("--out-csv", default="binding_energy_long.csv", help="Output CSV")
    parser.add_argument("--out-png", default="binding_energy_raincloud.png", help="Output PNG")
    parser.add_argument("--min-n", type=int, default=5, help="Minimum cluster size")
    parser.add_argument(
        "--order-by",
        choices=["size", "median", "cluster"],
        default="size",
        help="Cluster ordering",
    )
    parser.add_argument("--max-clusters", type=int, default=None)
    parser.add_argument("--connect-means", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input_txt)
    if input_path.suffix.lower() == ".csv":
        df = parse_energy_csv(args.input_txt)
    else:
        df = parse_cluster_file(args.input_txt)
    with new_outputs(args.out_csv, args.out_png):
        df.to_csv(args.out_csv, index=False)
        plot_raincloud(
            df=df,
            out_png=args.out_png,
            min_n=args.min_n,
            order_by=args.order_by,
            max_clusters=args.max_clusters,
            connect_means=args.connect_means,
        )

    print(f"[OK] CSV: {args.out_csv}")
    print(f"[OK] PNG: {args.out_png}")



if __name__ == "__main__":
    main()
