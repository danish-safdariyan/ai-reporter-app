"""
AI-Powered Reporter: World Bank API + Shiny UI + AI report.
Compiles LAB_your_good_api_query, LAB_cursor_shiny_app, LAB_ai_reporter.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Optional

import pandas as pd
from shiny import App, reactive, render, ui

from query import get_api_key_status, run_query
from ai_report import generate_report

# Default choices (G7 + common indicators)
DEFAULT_COUNTRIES = [
    ("USA", "United States"),
    ("CAN", "Canada"),
    ("GBR", "United Kingdom"),
    ("FRA", "France"),
    ("DEU", "Germany"),
    ("ITA", "Italy"),
    ("JPN", "Japan"),
]
INDICATOR_CHOICES = {
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "SP.POP.TOTL": "Population, total",
    "NE.EXP.GNFS.ZS": "Exports of goods and services (% of GDP)",
}

TABLE_PREVIEW_ROWS = 50


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h4("Query parameters"),
        ui.input_select(
            "countries",
            "Countries",
            choices={code: label for code, label in DEFAULT_COUNTRIES},
            selected=[c[0] for c in DEFAULT_COUNTRIES],
            multiple=True,
        ),
        ui.input_select(
            "indicator",
            "Indicator",
            choices=INDICATOR_CHOICES,
            selected="NY.GDP.PCAP.CD",
        ),
        ui.input_numeric("start_year", "Start year", value=2010, min=1960, max=2030),
        ui.input_numeric("end_year", "End year", value=2024, min=1960, max=2030),
        ui.input_numeric("per_page", "Per page (API)", value=20000, min=1, max=20000),
        ui.tags.hr(),
        ui.input_action_button("run_query_btn", "Run Query", class_="btn-primary"),
        width=300,
    ),
    ui.h2("AI-Powered Reporter"),
    ui.p(
        "Query the World Bank API, view data in the table and chart, then generate an AI summary. "
        "Choose parameters and click **Run Query**, then **Generate AI Report**."
    ),
    ui.tags.hr(),
    ui.h4("Status"),
    ui.output_ui("status"),
    ui.tags.hr(),
    ui.h4("Summary"),
    ui.output_ui("summary"),
    ui.tags.hr(),
    ui.h4("Data (first 50 rows)"),
    ui.output_data_frame("table"),
    ui.tags.hr(),
    ui.output_ui("download_ui"),
    ui.tags.hr(),
    ui.h4("Time series (line chart)"),
    ui.output_plot("line_plot"),
    ui.tags.hr(),
    ui.h4("AI Report"),
    ui.output_ui("ai_report_ui"),
    ui.output_ui("ai_report_text"),
)


def server(input: reactive.Inputs, output: reactive.Outputs, session: reactive.Session) -> None:
    result_df: reactive.Value[Optional[pd.DataFrame]] = reactive.Value(None)
    result_error: reactive.Value[Optional[str]] = reactive.Value(None)
    ai_report: reactive.Value[Optional[str]] = reactive.Value(None)
    ai_report_loading: reactive.Value[bool] = reactive.Value(False)

    @reactive.Effect
    @reactive.event(input.run_query_btn)
    def _on_run_query() -> None:
        result_df.set(None)
        result_error.set(None)
        ai_report.set(None)
        countries_raw = input.countries()
        countries_list = list(countries_raw) if isinstance(countries_raw, (list, tuple)) else [countries_raw] if countries_raw else []
        indicator_val = input.indicator() or ""
        start = int(input.start_year()) if input.start_year() is not None else 2010
        end = int(input.end_year()) if input.end_year() is not None else 2024
        per_page = int(input.per_page()) if input.per_page() is not None else 20000

        if start > end:
            result_error.set("Validation: Start year must be less than or equal to end year.")
            return
        if not countries_list:
            result_error.set("Validation: Select at least one country.")
            return
        if not indicator_val.strip():
            result_error.set("Validation: Select an indicator.")
            return

        try:
            df = run_query(
                countries=countries_list,
                indicator=indicator_val,
                start_year=start,
                end_year=end,
                per_page=per_page,
                use_cache=True,
            )
            if df.empty:
                result_error.set("No results found for the selected parameters.")
            else:
                result_df.set(df)
        except Exception as e:
            result_error.set(str(e))

    @reactive.Effect
    @reactive.event(input.generate_ai_btn)
    def _on_generate_ai() -> None:
        df = result_df.get()
        if df is None or df.empty:
            ai_report.set("Run a query first to generate an AI report.")
            return
        ai_report_loading.set(True)
        ai_report.set(None)
        try:
            indicator_id = input.indicator() or "NY.GDP.PCAP.CD"
            indicator_name = INDICATOR_CHOICES.get(indicator_id, indicator_id)
            report = generate_report(df, indicator_name)
            ai_report.set(report)
        except Exception as e:
            ai_report.set(f"Error: {e}")
        finally:
            ai_report_loading.set(False)

    @output
    @render.ui
    def status() -> ui.TagList:
        key_ok, key_msg = get_api_key_status()
        items = [ui.p(ui.tags.strong("API key: "), key_msg)]
        err = result_error.get()
        if err:
            items.append(ui.div(ui.tags.strong("Error: "), err, class_="text-danger"))
        elif result_df.get() is not None:
            items.append(ui.div("Query completed successfully.", class_="text-success"))
        return ui.TagList(items)

    @output
    @render.ui
    def summary() -> ui.TagList:
        df = result_df.get()
        if df is None and result_error.get() is None:
            return ui.p("Run a query to see the summary.")
        if df is None:
            return ui.TagList()
        n, cols = len(df), list(df.columns)
        params = (
            f"Countries: {', '.join(df['country_id'].drop_duplicates().astype(str).tolist()[:10])}"
            + (f" … ({df['country_id'].nunique()} total)" if df["country_id"].nunique() > 10 else "")
        )
        return ui.TagList(
            ui.p(ui.tags.strong("Rows: "), str(n)),
            ui.p(ui.tags.strong("Columns: "), ", ".join(cols)),
            ui.p(ui.tags.strong("Parameters: "), params),
        )

    @output
    @render.data_frame
    def table():
        df = result_df.get()
        if df is None or df.empty:
            return pd.DataFrame()
        return render.DataGrid(df.head(TABLE_PREVIEW_ROWS), height="400px", width="100%")

    @output
    @render.ui
    def download_ui() -> ui.TagList:
        df = result_df.get()
        if df is None or df.empty:
            return ui.p("No data to download. Run a query first.")
        return ui.download_button("download_csv", "Download CSV (full result)", class_="btn-primary")

    @output
    @render.download(filename=lambda: "world_bank_indicators.csv")
    def download_csv():
        df = result_df.get()
        if df is not None and not df.empty:
            yield df.to_csv(index=False)

    @output
    @render.plot
    def line_plot():
        df = result_df.get()
        if df is None or df.empty or "year" not in df.columns or "value" not in df.columns:
            return None
        plot_df = df.dropna(subset=["year", "value"])
        if plot_df.empty:
            return None
        try:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 5))
            for country in plot_df["country_name"].unique():
                sub = plot_df[plot_df["country_name"] == country].sort_values("year")
                ax.plot(sub["year"], sub["value"], label=country, marker="o", markersize=3)
            ax.set_xlabel("Year")
            ax.set_ylabel("Value")
            ax.set_title("Time series by country")
            ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            return fig
        except Exception:
            return None

    @output
    @render.ui
    def ai_report_ui() -> ui.TagList:
        df = result_df.get()
        if df is None or df.empty:
            return ui.p("Run a query first, then click **Generate AI Report**.")
        loading = ai_report_loading.get()
        if loading:
            return ui.p("Generating report…")
        return ui.input_action_button("generate_ai_btn", "Generate AI Report", class_="btn-primary")

    @output
    @render.ui
    def ai_report_text() -> ui.TagList:
        report = ai_report.get()
        if report is None:
            return ui.TagList()
        return ui.div(ui.pre(report), style="white-space: pre-wrap; background: #f5f5f5; padding: 1em; border-radius: 6px;")


with suppress(ImportError):
    from dotenv import load_dotenv
    load_dotenv()

app = App(app_ui, server)
