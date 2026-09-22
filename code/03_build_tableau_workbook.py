#!/usr/bin/env python3
"""Build the packaged Tableau workbook used by the proposal."""

from __future__ import annotations

import csv
import html
import re
import shutil
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "ai_use_cases.csv"
OUTPUT = ROOT / "proposal" / "prototypes.twbx"

BUILD_LEVELS = [
    "Purchased from a vendor",
    "Vendor and in-house",
    "Built in-house",
]
BUILD_RECODE = {
    "Vendor": "Purchased from a vendor",
    "Vendor and in-house": "Vendor and in-house",
    "In-house": "Built in-house",
}
BUILD_COLORS = {
    "Purchased from a vendor": "#eb6834",
    "Vendor and in-house": "#c9c7c0",
    "Built in-house": "#2a78d6",
}

TOPIC_RECODE = {"Administrative functions": "Admin Functions"}
VENDOR_ALIASES = [
    (r"microsoft|azure|copilot", "Microsoft"),
    (r"google|gemini", "Google"),
    (r"amazon|aws", "Amazon Web Services"),
    (r"openai|chatgpt", "OpenAI"),
    (r"anthropic|claude", "Anthropic"),
    (r"palantir", "Palantir"),
    (r"deloitte", "Deloitte"),
    (r"ibm", "IBM"),
    (r"servicenow", "ServiceNow"),
    (r"thomson reuters|westlaw", "Thomson Reuters"),
    (r"lexisnexis", "LexisNexis"),
    (r"esri", "Esri"),
    (r"accenture", "Accenture"),
    (r"booz allen", "Booz Allen Hamilton"),
    (r"leidos", "Leidos"),
    (r"saic", "SAIC"),
    (r"guidehouse", "Guidehouse"),
    (r"adobe", "Adobe"),
    (r"salesforce", "Salesforce"),
    (r"oracle", "Oracle"),
    (r"nvidia", "NVIDIA"),
    (r"axon", "Axon"),
    (r"sas\b", "SAS"),
    (r"databricks", "Databricks"),
    (r"snowflake", "Snowflake"),
]


def read_source() -> list[dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def make_buy_rows(records: list[dict[str, str]]) -> list[dict[str, object]]:
    selected = []
    for row in records:
        if row["year"] != "2025" or row["stage"] not in {"Pilot", "Deployed"}:
            continue
        build = BUILD_RECODE.get(row["build"])
        if build:
            selected.append({**row, "build_clean": build})

    def summarize(rows, panel, group_key, min_n):
        totals = Counter(r[group_key] for r in rows if r[group_key])
        counts = Counter((r[group_key], r["build_clean"]) for r in rows if r[group_key])
        result = []
        for group, total in totals.items():
            if total < min_n:
                continue
            for build in BUILD_LEVELS:
                n = counts[(group, build)]
                result.append({
                    "panel": panel,
                    "group": group,
                    "build": build,
                    "n": n,
                    "total": total,
                    "share": n / total,
                })
        return result

    overall_rows = [{**r, "all": "All agencies"} for r in selected]
    by_type_rows = [r for r in selected if r["classification"] and r["classification"] != "Other"]
    summary = (
        summarize(overall_rows, "All", "all", 0)
        + summarize(by_type_rows, "By type of AI", "classification", 30)
        + summarize(selected, "By agency (20+ cases)", "agency", 20)
    )

    panel_order = {"All": 1, "By type of AI": 2, "By agency (20+ cases)": 3}
    for panel in panel_order:
        panel_groups = sorted(
            {r["group"] for r in summary if r["panel"] == panel},
            key=lambda group: next(
                r["share"]
                for r in summary
                if r["panel"] == panel and r["group"] == group and r["build"] == BUILD_LEVELS[0]
            ),
            reverse=True,
        )
        order = {group: i + 1 for i, group in enumerate(panel_groups)}
        for row in summary:
            if row["panel"] != panel:
                continue
            row["panel_order"] = panel_order[panel]
            row["row_order"] = order[row["group"]]
            row["row_label"] = f'{row["group"]}  ({row["total"]:,})'
            row["category_order"] = BUILD_LEVELS.index(row["build"]) + 1

    out = []
    for row in summary:
        out.append({
            "chart": "Make or Buy",
            "panel": row["panel"],
            "panel_order": row["panel_order"],
            "row_label": row["row_label"],
            "row_order": row["row_order"],
            "column_label": "",
            "column_order": "",
            "category": row["build"],
            "category_order": row["category_order"],
            "count": row["n"],
            "share": row["share"],
            "secondary": row["total"],
            "mark_label": f'{row["share"]:.0%}' if row["share"] >= 0.09 else "",
        })
    return out


def topic_rows(records: list[dict[str, str]]) -> list[dict[str, object]]:
    cleaned = []
    for row in records:
        if row["year"] != "2025" or not row["topic_area"]:
            continue
        topic = TOPIC_RECODE.get(row["topic_area"], row["topic_area"])
        if topic.startswith("Other"):
            topic = "Other"
        cleaned.append((row["agency"], topic))

    agency_totals = Counter(agency for agency, _ in cleaned)
    eligible = [(agency, topic) for agency, topic in cleaned if agency_totals[agency] >= 50]
    topic_totals = Counter(topic for _, topic in eligible)
    top_ten = {topic for topic, _ in topic_totals.most_common(10) if topic != "Other"}
    regrouped = [(agency, topic if topic in top_ten else "Other") for agency, topic in eligible]
    counts = Counter(regrouped)
    grouped_totals = Counter(agency for agency, _ in regrouped)

    topic_order = [topic for topic, _ in Counter(t for _, t in regrouped if t != "Other").most_common()]
    topic_order.append("Other")
    agencies = sorted(grouped_totals, key=lambda a: grouped_totals[a])

    out = []
    for agency_index, agency in enumerate(agencies, 1):
        for topic_index, topic in enumerate(topic_order, 1):
            n = counts[(agency, topic)]
            out.append({
                "chart": "Agency Topics",
                "panel": "",
                "panel_order": "",
                "row_label": f"{agency} ({grouped_totals[agency]:,})",
                "row_order": agency_index,
                "column_label": topic,
                "column_order": topic_index,
                "category": "",
                "category_order": "",
                "count": n,
                "share": n / grouped_totals[agency],
                "secondary": grouped_totals[agency],
                "mark_label": str(n) if n else "",
            })
    return out


def canonical_vendor(part: str) -> str | None:
    for pattern, vendor in VENDOR_ALIASES:
        if re.search(pattern, part):
            return vendor
    return None


def vendor_rows(records: list[dict[str, str]]) -> list[dict[str, object]]:
    unique = set()
    for row in records:
        if row["year"] != "2025" or not row["vendor_name"]:
            continue
        parts = re.split(r";|,|/|\band\b|\n", row["vendor_name"].lower())
        for part in parts:
            vendor = canonical_vendor(" ".join(part.split()))
            if vendor:
                unique.add((row["record_id"], row["agency"], vendor))

    cases = Counter(vendor for _, _, vendor in unique)
    agencies = defaultdict(set)
    for _, agency, vendor in unique:
        agencies[vendor].add(agency)
    leaders = sorted(cases, key=lambda v: (-cases[v], v))[:15]

    out = []
    for index, vendor in enumerate(leaders, 1):
        agency_n = len(agencies[vendor])
        out.append({
            "chart": "Vendor Concentration",
            "panel": "",
            "panel_order": "",
            "row_label": vendor,
            "row_order": index,
            "column_label": "",
            "column_order": "",
            "category": "",
            "category_order": "",
            "count": cases[vendor],
            "share": "",
            "secondary": agency_n,
            "mark_label": f"{cases[vendor]} cases · {agency_n} {'agency' if agency_n == 1 else 'agencies'}",
        })
    return out


FIELDS = [
    ("chart", "string", "dimension", "nominal"),
    ("panel", "string", "dimension", "nominal"),
    ("panel_order", "integer", "dimension", "ordinal"),
    ("row_label", "string", "dimension", "nominal"),
    ("row_order", "integer", "dimension", "ordinal"),
    ("column_label", "string", "dimension", "nominal"),
    ("column_order", "integer", "dimension", "ordinal"),
    ("category", "string", "dimension", "nominal"),
    ("category_order", "integer", "dimension", "ordinal"),
    ("count", "integer", "measure", "quantitative"),
    ("share", "real", "measure", "quantitative"),
    ("secondary", "integer", "measure", "quantitative"),
    ("mark_label", "string", "dimension", "nominal"),
]


def field_xml(name, datatype, role, field_type):
    aggregation = "Sum" if role == "measure" else "Count"
    return f"<column aggregation='{aggregation}' datatype='{datatype}' name='[{name}]' role='{role}' type='{field_type}' />"


def instance_xml(name, datatype, role, field_type):
    if role == "measure":
        derivation = "Sum"
        prefix = "sum"
        suffix = "qk"
    else:
        derivation = "None"
        prefix = "none"
        suffix = "ok" if field_type == "ordinal" else "nk"
    return (
        f"<column-instance column='[{name}]' derivation='{derivation}' "
        f"name='[{prefix}:{name}:{suffix}]' pivot='key' type='{field_type}' />"
    )


def datasource_dependencies() -> str:
    definitions = "\n".join("            " + field_xml(*field) for field in FIELDS)
    instances = "\n".join("            " + instance_xml(*field) for field in FIELDS)
    return f"""<datasource-dependencies datasource='prototype'>
{definitions}
{instances}
          </datasource-dependencies>"""


def title_xml(title: str, subtitle: str) -> str:
    return f"""<layout-options>
        <title>
          <formatted-text>
            <run bold='true' font-family='Avenir Next' fontsize='15'>{html.escape(title)}</run>
            <run font-family='Avenir Next' fontsize='10'>&#10;{html.escape(subtitle)}</run>
          </formatted-text>
        </title>
      </layout-options>"""


def filter_xml(value: str) -> str:
    return f"""<filter class='categorical' column='[prototype].[none:chart:nk]'>
            <groupfilter function='member' level='[none:chart:nk]' member='&quot;{html.escape(value)}&quot;' />
          </filter>"""


def common_style(extra: str = "") -> str:
    return f"""<style>
          <style-rule element='axis'>
            <format attr='font-family' value='Avenir Next' />
            <format attr='font-size' value='9' />
            <format attr='color' value='#52514e' />
            <format attr='title' field='[prototype].[sum:share:qk]' scope='cols' value='' />
          </style-rule>
          <style-rule element='label'>
            <format attr='font-family' value='Avenir Next' />
            <format attr='font-size' value='9' />
            <format attr='color' value='#0b0b0b' />
            <format attr='display' field='[prototype].[none:panel_order:ok]' value='false' />
            <format attr='display' field='[prototype].[none:row_order:ok]' value='false' />
            <format attr='display' field='[prototype].[none:column_order:ok]' value='false' />
          </style-rule>
          <style-rule element='header'>
            <format attr='font-family' value='Avenir Next' />
            <format attr='font-size' value='9' />
            <format attr='color' value='#0b0b0b' />
            <format attr='border-style' scope='rows' value='none' />
            <format attr='border-style' scope='cols' value='none' />
          </style-rule>
          <style-rule element='pane'>
            <format attr='fill-color' value='#fcfcfb' />
            <format attr='border-style' scope='rows' value='none' />
            <format attr='border-style' scope='cols' value='none' />
          </style-rule>
          <style-rule element='worksheet'>
            <format attr='fill-color' value='#fcfcfb' />
            <format attr='font-family' value='Avenir Next' />
            <format attr='display-field-labels' scope='rows' value='false' />
            <format attr='display-field-labels' scope='cols' value='false' />
          </style-rule>
          {extra}
        </style>"""


def make_buy_sheet() -> str:
    palette = "".join(
        f"<map to='{BUILD_COLORS[level]}'><bucket>&quot;{level}&quot;</bucket></map>"
        for level in BUILD_LEVELS
    )
    extra = f"""<style-rule element='mark'>
            <encoding attr='color' field='[prototype].[none:category:nk]' type='palette'>{palette}</encoding>
          </style-rule>
          <style-rule element='cell'>
            <format attr='text-format' field='[prototype].[sum:share:qk]' value='p0%' />
          </style-rule>"""
    return f"""<worksheet name='1. Who Builds Federal AI'>
      {title_xml('Two-thirds of federal AI in pilot or use involves vendors, and agencies differ sharply', 'Share of 2025 pilot and deployed AI use cases, by who developed the system. Number of use cases in parentheses.')}
      <table>
        <view>
          <datasources><datasource caption='Proposal prototype data' name='prototype' /></datasources>
          {datasource_dependencies()}
          {filter_xml('Make or Buy')}
          <slices><column>[prototype].[none:chart:nk]</column></slices>
          <aggregation value='true' />
        </view>
        {common_style(extra)}
        <panes><pane><view><breakdown value='auto' /></view><mark class='Bar' />
          <encodings>
            <color column='[prototype].[none:category:nk]' />
            <text column='[prototype].[none:mark_label:nk]' />
            <lod column='[prototype].[sum:count:qk]' />
          </encodings>
          <customized-tooltip><formatted-text>
            <run bold='true'>&lt;[prototype].[none:row_label:nk]&gt;&#10;</run>
            <run>&lt;[prototype].[none:category:nk]&gt;: </run><run bold='true'>&lt;[prototype].[sum:count:qk]&gt;</run>
          </formatted-text></customized-tooltip>
          <style><style-rule element='mark'><format attr='mark-labels-show' value='true' /><format attr='mark-labels-cull' value='false' /></style-rule><style-rule element='datalabel'><format attr='font-family' value='Avenir Next' /><format attr='font-size' value='9' /></style-rule></style>
        </pane></panes>
        <rows>([prototype].[none:panel_order:ok] / ([prototype].[none:panel:nk] / ([prototype].[none:row_order:ok] / [prototype].[none:row_label:nk])))</rows>
        <cols>[prototype].[sum:share:qk]</cols>
      </table>
    </worksheet>"""


def topic_sheet() -> str:
    extra = """<style-rule element='mark'>
            <encoding attr='color' field='[prototype].[sum:share:qk]' max='1.0' min='0.0' type='custom-interpolated'>
              <color-palette custom='true' name='' type='ordered-sequential'><color>#fff4ed</color><color>#f7b38f</color><color>#eb6834</color><color>#9f2f0d</color></color-palette>
            </encoding>
          </style-rule>
          <style-rule element='cell'><format attr='text-format' field='[prototype].[sum:share:qk]' value='p0%' /></style-rule>"""
    return f"""<worksheet name='2. Agency Topic Heatmap'>
      {title_xml('Most agencies concentrate their AI in one or two kinds of work', "2025 AI use cases by agency and OMB topic area. Cell = number of use cases; color = share of that agency's cases.")}
      <table>
        <view>
          <datasources><datasource caption='Proposal prototype data' name='prototype' /></datasources>
          {datasource_dependencies()}
          {filter_xml('Agency Topics')}
          <slices><column>[prototype].[none:chart:nk]</column></slices>
          <aggregation value='true' />
        </view>
        {common_style(extra)}
        <panes><pane><view><breakdown value='auto' /></view><mark class='Square' />
          <encodings>
            <color column='[prototype].[sum:share:qk]' />
            <text column='[prototype].[none:mark_label:nk]' />
            <tooltip column='[prototype].[sum:share:qk]' />
          </encodings>
          <customized-tooltip><formatted-text>
            <run bold='true'>&lt;[prototype].[none:row_label:nk]&gt;&#10;</run>
            <run>&lt;[prototype].[none:column_label:nk]&gt;: </run><run bold='true'>&lt;[prototype].[sum:count:qk]&gt;</run><run> use cases&#10;</run>
            <run>Share of agency portfolio: </run><run bold='true'>&lt;[prototype].[sum:share:qk]&gt;</run>
          </formatted-text></customized-tooltip>
          <style><style-rule element='mark'><format attr='mark-labels-show' value='true' /><format attr='mark-labels-cull' value='false' /><format attr='mark-labels-mode' value='line' /></style-rule><style-rule element='datalabel'><format attr='font-family' value='Avenir Next' /><format attr='font-size' value='8' /></style-rule></style>
        </pane></panes>
        <rows>([prototype].[none:row_order:ok] / [prototype].[none:row_label:nk])</rows>
        <cols>([prototype].[none:column_order:ok] / [prototype].[none:column_label:nk])</cols>
      </table>
    </worksheet>"""


def vendor_sheet() -> str:
    extra = """<style-rule element='mark'><encoding attr='color' field='[prototype].[sum:count:qk]' type='palette'><map to='#eb6834'><bucket>&quot;SUM(count)&quot;</bucket></map></encoding></style-rule>
          <style-rule element='cell'><format attr='text-format' field='[prototype].[sum:count:qk]' value='N' /></style-rule>"""
    return f"""<worksheet name='3. Vendor Concentration'>
      {title_xml('One vendor appears in far more federal AI than any other', '2025 AI use cases naming each firm as a vendor, and the number of agencies using it. Top 15 firms.')}
      <table>
        <view>
          <datasources><datasource caption='Proposal prototype data' name='prototype' /></datasources>
          {datasource_dependencies()}
          {filter_xml('Vendor Concentration')}
          <slices><column>[prototype].[none:chart:nk]</column></slices>
          <aggregation value='true' />
        </view>
        {common_style(extra)}
        <panes><pane><view><breakdown value='auto' /></view><mark class='Circle' />
          <encodings>
            <size column='[prototype].[sum:secondary:qk]' />
            <text column='[prototype].[none:mark_label:nk]' />
          </encodings>
          <customized-tooltip><formatted-text>
            <run bold='true'>&lt;[prototype].[none:row_label:nk]&gt;&#10;</run>
            <run>Use cases: </run><run bold='true'>&lt;[prototype].[sum:count:qk]&gt;&#10;</run>
            <run>Agencies: </run><run bold='true'>&lt;[prototype].[sum:secondary:qk]&gt;</run>
          </formatted-text></customized-tooltip>
          <style><style-rule element='mark'><format attr='color' value='#eb6834' /><format attr='mark-labels-show' value='true' /><format attr='mark-labels-cull' value='false' /></style-rule><style-rule element='datalabel'><format attr='font-family' value='Avenir Next' /><format attr='font-size' value='9' /><format attr='color' value='#52514e' /></style-rule></style>
        </pane></panes>
        <rows>([prototype].[none:row_order:ok] / [prototype].[none:row_label:nk])</rows>
        <cols>[prototype].[sum:count:qk]</cols>
      </table>
    </worksheet>"""


def workbook_xml() -> str:
    relation_columns = "\n".join(
        f"            <column datatype='{datatype}' name='{name}' ordinal='{index}' />"
        for index, (name, datatype, _, _) in enumerate(FIELDS)
    )
    top_columns = "\n".join("      " + field_xml(*field) for field in FIELDS)
    windows = "\n".join(
        f"""    <window class='worksheet' name='{name}'>
      <cards><edge name='left'><strip size='190'><card type='pages' /><card type='filters' /><card type='marks' /></strip></edge><edge name='top'><strip size='31'><card type='columns' /></strip><strip size='31'><card type='rows' /></strip><strip size='52'><card type='title' /></strip></edge></cards>
    </window>"""
        for name in ["1. Who Builds Federal AI", "2. Agency Topic Heatmap", "3. Vendor Concentration"]
    )
    return f"""<?xml version='1.0' encoding='utf-8'?>
<!-- Generated from OMB Federal Agency AI Use Case Inventory 2025 -->
<workbook source-build='0.0.0 (0000.0.0.0)' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences><preference name='ui.encoding.shelf.height' value='24' /><preference name='ui.shelf.height' value='26' /></preferences>
  <style-theme name='smooth' />
  <datasources>
    <datasource caption='Proposal prototype data' inline='true' name='prototype' version='18.1'>
      <connection class='federated'>
        <named-connections><named-connection caption='Proposal prototype data' name='prototype_csv'><connection class='textscan' directory='Data/prototypes' filename='prototype_data.csv' password='' server='' /></named-connection></named-connections>
        <relation connection='prototype_csv' name='prototype_data.csv' table='[prototype_data#csv]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>
{relation_columns}
          </columns>
        </relation>
      </connection>
{top_columns}
      <aliases enabled='yes' />
    </datasource>
  </datasources>
  <worksheets>
    {make_buy_sheet()}
    {topic_sheet()}
    {vendor_sheet()}
  </worksheets>
  <windows source-height='900'>
{windows}
  </windows>
</workbook>
"""


def validate(rows: list[dict[str, object]]) -> None:
    make_buy = [r for r in rows if r["chart"] == "Make or Buy"]
    overall = [r for r in make_buy if r["panel"] == "All"]
    assert sum(int(r["count"]) for r in overall) == 1444
    assert round(next(float(r["share"]) for r in overall if r["category"] == BUILD_LEVELS[0]) * 100) == 38

    topics = [r for r in rows if r["chart"] == "Agency Topics"]
    nasa_science = next(r for r in topics if r["row_label"].startswith("NASA ") and r["column_label"] == "Science")
    assert int(nasa_science["count"]) == 387

    vendors = [r for r in rows if r["chart"] == "Vendor Concentration"]
    microsoft = next(r for r in vendors if r["row_label"] == "Microsoft")
    assert int(microsoft["count"]) == 133 and int(microsoft["secondary"]) == 21


def main() -> None:
    records = read_source()
    rows = make_buy_rows(records) + topic_rows(records) + vendor_rows(records)
    validate(rows)

    with tempfile.TemporaryDirectory(prefix="tableau_prototypes_") as temp:
        stage = Path(temp)
        data_dir = stage / "Data" / "prototypes"
        data_dir.mkdir(parents=True)
        csv_path = data_dir / "prototype_data.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[f[0] for f in FIELDS])
            writer.writeheader()
            writer.writerows(rows)

        (stage / "prototypes.twb").write_text(workbook_xml(), encoding="utf-8")
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        temp_zip = stage / "prototypes.zip"
        with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(stage / "prototypes.twb", "prototypes.twb")
            archive.write(csv_path, "Data/prototypes/prototype_data.csv")
        shutil.copy2(temp_zip, OUTPUT)

    print(f"Created {OUTPUT}")
    print(f"Rows packaged: {len(rows):,}")


if __name__ == "__main__":
    main()
