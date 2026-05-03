from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


INPUT = Path("results/taskset_summary.csv")
OUT_DIR = Path("results/plots")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    df["target_utilization"] = pd.to_numeric(df["target_utilization"], errors="coerce")
    df["dm_schedulable"] = df["dm_schedulable"].astype(bool)
    df["edf_schedulable"] = df["edf_schedulable"].astype(bool)

    df = df[df["status"].eq("ok")]
    df = df.dropna(subset=["target_utilization"])

    return df


def plot_schedulability_by_util(df: pd.DataFrame) -> None:
    grouped = (
        df.groupby(["distribution", "target_utilization"])
        .agg(
            tasksets=("taskset_name", "count"),
            dm_success=("dm_schedulable", "mean"),
            edf_success=("edf_schedulable", "mean"),
        )
        .reset_index()
        .sort_values(["distribution", "target_utilization"])
    )

    for distribution, part in grouped.groupby("distribution"):
        plt.figure(figsize=(9, 5))

        offset = 0.005

        x_dm = part["target_utilization"] - offset
        x_edf = part["target_utilization"] + offset

        y_dm = part["dm_success"] * 100
        y_edf = part["edf_success"] * 100

        plt.plot(
            x_dm,
            y_dm,
            marker="o",
            linestyle="--",
            linewidth=2,
            label="DM",
        )

        plt.plot(
            x_edf,
            y_edf,
            marker="s",
            linestyle="-",
            linewidth=2,
            label="EDF",
        )

        diff = y_edf - y_dm
        for x, y, d in zip(part["target_utilization"], y_edf, diff):
            if abs(d) >= 0.5:
                plt.text(
                    x,
                    min(y + 2, 102),
                    f"+{d:.0f}%",
                    ha="center",
                    fontsize=9,
                )

        plt.title(f"Schedulability vs Utilization ({distribution})")
        plt.xlabel("Target utilization")
        plt.ylabel("Schedulable task sets (%)")
        plt.ylim(0, 105)
        plt.xticks(sorted(part["target_utilization"].unique()))
        plt.grid(True, alpha=0.4)
        plt.legend()
        plt.tight_layout()

        filename = OUT_DIR / f"schedulability_{distribution}.png"
        plt.savefig(filename, dpi=200)
        plt.close()


def plot_total_schedulability(df: pd.DataFrame) -> None:
    grouped = (
        df.groupby("distribution")
        .agg(
            tasksets=("taskset_name", "count"),
            dm_success=("dm_schedulable", "mean"),
            edf_success=("edf_schedulable", "mean"),
        )
        .reset_index()
        .sort_values("distribution")
    )

    x = list(range(len(grouped)))
    width = 0.35

    plt.figure(figsize=(9, 5))

    dm_vals = grouped["dm_success"] * 100
    edf_vals = grouped["edf_success"] * 100

    plt.bar(
        [i - width / 2 for i in x],
        dm_vals,
        width,
        label="DM",
    )

    plt.bar(
        [i + width / 2 for i in x],
        edf_vals,
        width,
        label="EDF",
    )

    for i, value in enumerate(dm_vals):
        plt.text(i - width / 2, value + 1, f"{value:.1f}%", ha="center", fontsize=9)

    for i, value in enumerate(edf_vals):
        plt.text(i + width / 2, value + 1, f"{value:.1f}%", ha="center", fontsize=9)

    plt.xticks(x, grouped["distribution"], rotation=20, ha="right")
    plt.ylabel("Schedulable task sets (%)")
    plt.title("Overall schedulability by distribution")
    plt.ylim(0, 110)
    plt.grid(axis="y", alpha=0.4)
    plt.legend()
    plt.tight_layout()

    plt.savefig(OUT_DIR / "overall_schedulability.png", dpi=200)
    plt.close()


def plot_wcrt_comparison(df: pd.DataFrame) -> None:
    valid = df.dropna(subset=["dm_max_wcrt", "edf_max_wcrt"]).copy()

    if valid.empty:
        return

    valid["dm_max_wcrt"] = pd.to_numeric(valid["dm_max_wcrt"], errors="coerce")
    valid["edf_max_wcrt"] = pd.to_numeric(valid["edf_max_wcrt"], errors="coerce")
    valid = valid.dropna(subset=["dm_max_wcrt", "edf_max_wcrt"])

    plt.figure(figsize=(7, 7))

    plt.scatter(
        valid["dm_max_wcrt"],
        valid["edf_max_wcrt"],
        alpha=0.45,
        s=30,
    )

    max_value = max(valid["dm_max_wcrt"].max(), valid["edf_max_wcrt"].max())

    plt.plot(
        [0, max_value],
        [0, max_value],
        linestyle="--",
        linewidth=2,
        label="DM = EDF",
    )

    plt.xlabel("DM max WCRT")
    plt.ylabel("EDF max WCRT")
    plt.title("DM vs EDF maximum WCRT")
    plt.grid(True, alpha=0.4)
    plt.legend()
    plt.tight_layout()

    plt.savefig(OUT_DIR / "wcrt_dm_vs_edf.png", dpi=200)
    plt.close()


def plot_schedulability_difference(df: pd.DataFrame) -> None:
    grouped = (
        df.groupby(["distribution", "target_utilization"])
        .agg(
            dm_success=("dm_schedulable", "mean"),
            edf_success=("edf_schedulable", "mean"),
        )
        .reset_index()
        .sort_values(["distribution", "target_utilization"])
    )

    for distribution, part in grouped.groupby("distribution"):
        plt.figure(figsize=(9, 5))

        diff = (part["edf_success"] - part["dm_success"]) * 100

        plt.bar(part["target_utilization"], diff, width=0.04)

        plt.axhline(0, linestyle="--", linewidth=1)
        plt.title(f"EDF schedulability advantage ({distribution})")
        plt.xlabel("Target utilization")
        plt.ylabel("EDF - DM schedulability (%)")
        plt.xticks(sorted(part["target_utilization"].unique()))
        plt.grid(axis="y", alpha=0.4)
        plt.tight_layout()

        filename = OUT_DIR / f"edf_advantage_{distribution}.png"
        plt.savefig(filename, dpi=200)
        plt.close()


def print_summary(df: pd.DataFrame) -> None:
    summary = (
        df.groupby("distribution")
        .agg(
            tasksets=("taskset_name", "count"),
            dm_schedulable=("dm_schedulable", "sum"),
            edf_schedulable=("edf_schedulable", "sum"),
            dm_rate=("dm_schedulable", "mean"),
            edf_rate=("edf_schedulable", "mean"),
        )
        .reset_index()
    )

    summary["dm_rate"] = summary["dm_rate"] * 100
    summary["edf_rate"] = summary["edf_rate"] * 100

    print("\nSchedulability summary:")
    print(summary.to_string(index=False))

    print("\nSanity checks:")
    print("Total rows:", len(df))
    print("DM true / EDF false:", ((df["dm_schedulable"]) & (~df["edf_schedulable"])).sum())
    print("EDF true / DM false:", ((df["edf_schedulable"]) & (~df["dm_schedulable"])).sum())

    if "warnings" in df.columns:
        warnings = df["warnings"].fillna("").astype(str).ne("").sum()
        print("Rows with warnings:", warnings)

    if "status" in df.columns:
        failed = df["status"].ne("ok").sum()
        print("Failed rows:", failed)


def main() -> None:
    df = load_data(INPUT)

    print_summary(df)

    plot_schedulability_by_util(df)
    plot_total_schedulability(df)
    plot_wcrt_comparison(df)
    plot_schedulability_difference(df)

    print(f"\nPlots saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()