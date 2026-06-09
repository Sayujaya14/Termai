"""Self-contained HTML reports with embedded charts (base64) and Jinja templates."""

from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPORTS_TEMPLATE_DIR = BASE_DIR / "templates" / "reports"


def png_bytes_to_data_uri(png_bytes: bytes) -> str:
    """Encode PNG bytes as an inline data URI for use in <img src=\"...\">."""
    encoded = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def png_file_to_data_uri(path: str | Path) -> str:
    """Read a PNG file and return a data URI."""
    with open(path, "rb") as f:
        return png_bytes_to_data_uri(f.read())


def img_tag_from_png(path: str | Path, *, alt: str = "") -> str:
    """Build an <img> tag with an embedded PNG (opens standalone in any browser)."""
    uri = png_file_to_data_uri(path)
    if alt:
        return f'<img src="{uri}" alt="{alt}">'
    return f'<img src="{uri}">'


def fig_to_data_uri(fig) -> str:
    """Save a matplotlib figure to an inline PNG data URI and close the figure."""
    import matplotlib.pyplot as plt

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    buf.seek(0)
    uri = png_bytes_to_data_uri(buf.read())
    plt.close(fig)
    return uri


def _save_fig(fig, path: Path) -> str:
    """Embed figure in HTML and optionally save PNG alongside the report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=120)
    uri = fig_to_data_uri(fig)
    return uri


def _load_report_css() -> str:
    css_path = REPORTS_TEMPLATE_DIR / "eda_report.css"
    return css_path.read_text(encoding="utf-8")


def _clean_table_html(html: str) -> str:
    """Normalize pandas HTML tables for the report theme."""
    html = html.replace('class="dataframe stats-table"', 'class="stats-table"')
    html = html.replace('class="stats-table stats-table"', 'class="stats-table"')
    html = html.replace('class="dataframe"', 'class="stats-table"')
    html = html.replace(' border="1"', "")
    html = html.replace(' border="0"', "")
    return html


def _df_to_table_html(df, *, index: bool = True) -> str:
    import pandas as pd

    html = df.to_html(
        classes="stats-table",
        border=0,
        na_rep="—",
        index=index,
        float_format=lambda x: f"{x:,.3f}" if pd.notna(x) else "—",
    )
    return _clean_table_html(html)


def _build_overview_html(df, numeric_cols, categorical_cols) -> str:
    """Column inventory + separate numeric / categorical summaries (no mixed NaN grid)."""
    import pandas as pd

    parts: list[str] = []

    # Column-level summary (every column)
    inventory = []
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        inventory.append({
            "Column": col,
            "Type": str(df[col].dtype),
            "Non-null": f"{df[col].notna().sum():,}",
            "Missing": f"{n_missing:,}" if n_missing else "0",
            "Unique": f"{df[col].nunique():,}",
        })
    inv_df = pd.DataFrame(inventory)
    parts.append('<h3 class="overview-sub">Column summary</h3>')
    parts.append(_df_to_table_html(inv_df, index=False))

    if numeric_cols:
        num_stats = df[numeric_cols].describe().T
        num_stats = num_stats.round(3)
        parts.append('<h3 class="overview-sub">Numeric statistics</h3>')
        parts.append(_df_to_table_html(num_stats, index=True))

    if categorical_cols:
        cat_stats = df[categorical_cols].describe().T
        parts.append('<h3 class="overview-sub">Categorical &amp; text columns</h3>')
        parts.append(_df_to_table_html(cat_stats, index=True))

    if not numeric_cols and not categorical_cols:
        parts.append('<p class="empty-note">No columns to summarize.</p>')

    return "\n".join(parts)


def _styled_table_html(html: str) -> str:
    return _clean_table_html(html)


def _missing_values_html(df) -> str:
    import pandas as pd

    counts = df.isna().sum()
    counts = counts[counts > 0].sort_values(ascending=False)
    if counts.empty:
        return ""

    total = len(df)
    rows = []
    for col, n in counts.items():
        pct = 100.0 * n / total
        rows.append(
            f'<div class="missing-row">'
            f'<span class="missing-label">{col}</span>'
            f'<div class="missing-track"><div class="missing-fill" style="width:{pct:.1f}%"></div></div>'
            f'<span class="missing-pct">{pct:.1f}%</span>'
            f"</div>"
        )
    return '<div class="missing-bar-wrap">' + "".join(rows) + "</div>"


def _generate_insights(df, numeric_cols, categorical_cols) -> list[str]:
    import pandas as pd

    insights: list[str] = []
    n, p = df.shape
    insights.append(f"Dataset contains {n:,} rows and {p} columns.")

    missing = int(df.isna().sum().sum())
    if missing:
        cols_with_missing = int((df.isna().sum() > 0).sum())
        insights.append(
            f"{missing:,} missing cells across {cols_with_missing} column(s)."
        )
    else:
        insights.append("No missing values in any column.")

    if len(numeric_cols) > 0:
        insights.append(f"{len(numeric_cols)} numeric column(s) analyzed for distributions.")
    if len(categorical_cols) > 0:
        insights.append(f"{len(categorical_cols)} categorical column(s) summarized.")

    if len(numeric_cols) > 1:
        corr = df[numeric_cols].corr()
        # strongest off-diagonal correlation
        best_pair = None
        best_val = 0.0
        for i, a in enumerate(numeric_cols):
            for b in numeric_cols[i + 1 :]:
                val = corr.loc[a, b]
                if pd.isna(val):
                    continue
                if abs(val) > abs(best_val):
                    best_val = val
                    best_pair = (a, b)
        if best_pair:
            insights.append(
                f"Strongest correlation: {best_pair[0]} vs {best_pair[1]} "
                f"(r = {best_val:.2f})."
            )

    dupes = int(df.duplicated().sum())
    if dupes:
        insights.append(f"{dupes:,} duplicate row(s) detected.")

    return insights


def _top_correlation_pairs(
    df, numeric_cols: list, *, max_pairs: int = 3
) -> list[tuple[str, str, float]]:
    """Return the strongest numeric column pairs by absolute Pearson correlation."""
    import pandas as pd

    if len(numeric_cols) < 2:
        return []

    corr = df[numeric_cols].corr()
    pairs: list[tuple[str, str, float]] = []
    for i, a in enumerate(numeric_cols):
        for b in numeric_cols[i + 1 :]:
            val = corr.loc[a, b]
            if pd.notna(val):
                pairs.append((a, b, float(val)))

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    return pairs[:max_pairs]


def _chart_uri(fig, png_path: Path, *, save_pngs: bool) -> str:
    if save_pngs:
        return _save_fig(fig, png_path)
    return fig_to_data_uri(fig)


def render_eda_report_html(
    *,
    title: str,
    dataset_name: str,
    generated_at: str,
    row_count: int,
    col_count: int,
    numeric_count: int,
    categorical_count: int,
    insights: list[str],
    overview_html: str,
    missing_html: str,
    distribution_charts: list[dict],
    categorical_charts: list[dict],
    pie_charts: list[dict],
    relationship_charts: list[dict],
    correlation_chart: str | None,
) -> str:
    """Render the EDA Jinja template to a full HTML string."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader(str(REPORTS_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("eda_report.html")
    return template.render(
        css=_load_report_css(),
        title=title,
        dataset_name=dataset_name,
        generated_at=generated_at,
        row_count=f"{row_count:,}",
        col_count=str(col_count),
        numeric_count=str(numeric_count),
        categorical_count=str(categorical_count),
        insights=insights,
        overview_html=overview_html,
        missing_html=missing_html,
        distribution_charts=distribution_charts,
        categorical_charts=categorical_charts,
        pie_charts=pie_charts,
        relationship_charts=relationship_charts,
        correlation_chart=correlation_chart,
    )


def build_eda_report(
    df,
    output_path: str | Path,
    *,
    dataset_name: str | None = None,
    title: str = "Exploratory Data Analysis",
    save_pngs: bool = True,
    max_categorical_cols: int = 6,
    max_pie_cols: int = 4,
    max_scatter_pairs: int = 3,
) -> str:
    """
    Build a self-contained EDA HTML report from a pandas DataFrame.

    Charts are embedded as base64. Optionally saves PNG copies next to the report.
    Returns the absolute path to the written HTML file.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    output_path = Path(output_path).resolve()
    workspace = output_path.parent
    dataset_name = dataset_name or output_path.stem

    sns.set_theme(style="whitegrid", palette="muted", font_scale=0.95)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()

    overview_html = _build_overview_html(df, numeric_cols, categorical_cols)
    missing_html = _missing_values_html(df)
    insights = _generate_insights(df, numeric_cols, categorical_cols)

    distribution_charts: list[dict] = []
    for col in numeric_cols:
        fig, ax = plt.subplots(figsize=(5, 3.5))
        sns.histplot(df[col].dropna(), kde=True, ax=ax, color="#0d9488")
        ax.set_title(f"Distribution of {col}")
        ax.set_xlabel(col)
        png_path = workspace / f"{col}_distribution.png"
        if save_pngs:
            uri = _save_fig(fig, png_path)
        else:
            uri = fig_to_data_uri(fig)
        distribution_charts.append({"label": col, "uri": uri})

    categorical_charts: list[dict] = []
    for col in categorical_cols[:max_categorical_cols]:
        counts = df[col].astype(str).value_counts().head(10)
        if counts.empty:
            continue
        fig, ax = plt.subplots(figsize=(5, 3.5))
        counts.plot(kind="barh", ax=ax, color="#6366f1")
        ax.set_title(f"Top values — {col}")
        ax.set_xlabel("Count")
        ax.invert_yaxis()
        fig.tight_layout()
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in col)
        png_path = workspace / f"{safe}_value_counts.png"
        if save_pngs:
            uri = _save_fig(fig, png_path)
        else:
            uri = fig_to_data_uri(fig)
        categorical_charts.append({"label": col, "uri": uri})

    pie_charts: list[dict] = []
    for col in categorical_cols:
        if len(pie_charts) >= max_pie_cols:
            break
        n_unique = df[col].nunique(dropna=True)
        if n_unique < 2 or n_unique > 8:
            continue
        counts = df[col].astype(str).value_counts()
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.pie(
            counts.values,
            labels=counts.index,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 8},
        )
        ax.set_title(f"Composition — {col}")
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in col)
        png_path = workspace / f"{safe}_pie.png"
        uri = _chart_uri(fig, png_path, save_pngs=save_pngs)
        pie_charts.append({"label": col, "uri": uri})

    relationship_charts: list[dict] = []
    for col_a, col_b, corr_val in _top_correlation_pairs(
        df, numeric_cols, max_pairs=max_scatter_pairs
    ):
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.scatterplot(data=df, x=col_a, y=col_b, ax=ax, alpha=0.55, color="#0d9488")
        ax.set_title(f"{col_a} vs {col_b}")
        ax.set_xlabel(col_a)
        ax.set_ylabel(col_b)
        fig.text(0.99, 0.01, f"r = {corr_val:.2f}", ha="right", va="bottom", fontsize=9)
        fig.tight_layout()
        safe_a = "".join(c if c.isalnum() or c in "-_" else "_" for c in col_a)
        safe_b = "".join(c if c.isalnum() or c in "-_" else "_" for c in col_b)
        png_path = workspace / f"scatter_{safe_a}_vs_{safe_b}.png"
        uri = _chart_uri(fig, png_path, save_pngs=save_pngs)
        relationship_charts.append({
            "label": f"{col_a} vs {col_b} (r = {corr_val:.2f})",
            "uri": uri,
        })

    # Numeric vs categorical: box plot for low-cardinality categories
    if numeric_cols and categorical_cols:
        for cat_col in categorical_cols:
            if len(relationship_charts) >= max_scatter_pairs + 2:
                break
            if df[cat_col].nunique(dropna=True) > 8:
                continue
            num_col = numeric_cols[0]
            fig, ax = plt.subplots(figsize=(5, 4))
            sns.boxplot(data=df, x=cat_col, y=num_col, ax=ax, color="#a5b4fc")
            ax.set_title(f"{num_col} by {cat_col}")
            ax.tick_params(axis="x", rotation=30)
            fig.tight_layout()
            safe_cat = "".join(c if c.isalnum() or c in "-_" else "_" for c in cat_col)
            png_path = workspace / f"box_{num_col}_by_{safe_cat}.png"
            uri = _chart_uri(fig, png_path, save_pngs=save_pngs)
            relationship_charts.append({
                "label": f"{num_col} by {cat_col}",
                "uri": uri,
            })
            break

    correlation_chart = None
    if len(numeric_cols) > 1:
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(
            df[numeric_cols].corr(),
            annot=True,
            fmt=".2f",
            cmap="RdYlGn",
            center=0,
            ax=ax,
            linewidths=0.5,
        )
        ax.set_title("Correlation heatmap")
        png_path = workspace / "correlation_heatmap.png"
        if save_pngs:
            correlation_chart = _save_fig(fig, png_path)
        else:
            correlation_chart = fig_to_data_uri(fig)

    html = render_eda_report_html(
        title=title,
        dataset_name=dataset_name,
        generated_at=datetime.now().strftime("%b %d, %Y %H:%M"),
        row_count=len(df),
        col_count=len(df.columns),
        numeric_count=len(numeric_cols),
        categorical_count=len(categorical_cols),
        insights=insights,
        overview_html=overview_html,
        missing_html=missing_html,
        distribution_charts=distribution_charts,
        categorical_charts=categorical_charts,
        pie_charts=pie_charts,
        relationship_charts=relationship_charts,
        correlation_chart=correlation_chart,
    )

    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
