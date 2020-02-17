import argparse
from typing import Tuple, Dict

import numpy as np
import pandas as pd

all_columns: Tuple[str, ...] = (
    "SERIAL", "SHIFT_WT", "NON_RESPONSE_WT", "MINS_WT", "TRAFFIC_WT", "UNSAMP_TRAFFIC_WT",
    "IMBAL_WT", "FINAL_WT", "STAY", "STAYK", "FARE", "FAREK", "SPEND", "EXPENDITURE", "DVEXPEND", "FLOW", "PURPOSE",
    "RESIDENCE", "COUNTRYVISIT", "SPENDIMPREASON", "PORTROUTE",
    "SPENDK", "VISIT_WT", "VISIT_WTK", "STAY_WT", "STAY_WTK", "EXPENDITURE_WT", "EXPENDITURE_WTK",
    "NIGHTS1", "NIGHTS2", "NIGHTS3", "NIGHTS4", "NIGHTS5", "NIGHTS6", "NIGHTS7", "NIGHTS8",
    "STAY1K", "STAY2K", "STAY3K", "STAY4K", "STAY5K", "STAY6K", "STAY7K", "STAY8K", "SPEND1",
    "SPEND2", "SPEND3", "SPEND4", "SPEND5", "SPEND6", "SPEND7", "SPEND8", "DIRECTLEG", "OVLEG",
    "UKLEG"
)

fare_columns: Tuple[str, ...] = (
    "SERIAL", "SPEND", "SPENDIMPREASON", "FARE", "FAREK"
)

expenditure_columns: Tuple[str, ...] = (
    "SERIAL", "EXPENDITURE"
)

unsamp_pv_columns: Tuple[str, ...] = (
    "SERIAL", "UNSAMP_REGION_GRP_PV", "DVPORTCODE"
)

intermediate_columns: Tuple[str, ...] = (
    "SERIAL", "UK_OS_PV", "STAYIMPCTRYLEVEL1_PV", "DUR1_PV", "PUR1_PV", "PUR2_PV",
    "STAYIMPCTRYLEVEL2_PV", "STAYIMPCTRYLEVEL3_PV", "DUR2_PV", "PUR3_PV",
    "SPEND_IMP_ELIGIBLE_PV", "SPEND_IMP_FLAG_PV", "SPENDK", "STAY",
    'INTDATE',
    'DVFARE',
    'FARE',
    'FARES_IMP_ELIGIBLE_PV',
    'FARES_IMP_FLAG_PV',
    'FAREK',
    'FAGE_PV',
    'BABYFARE',
    'CHILDFARE',
    'APD_PV',
    'DVPACKAGE',
    'DISCNT_F2_PV',
    'QMFARE_PV',
    'DVPACKCOST',
    'DISCNT_PACKAGE_COST_PV',
    'DVPERSONS',
    'DVEXPEND',
    'BEFAF',
    'SPENDIMPREASON',
    'DUTY_FREE_PV',
    'PACKAGE'
)

# columns_to_extract = all_columns
# columns_to_extract = expenditure_columns
columns_to_extract = unsamp_pv_columns
Stats = Dict[str, Tuple]


def get_datasets(sas_survey_output: str, py_survey_output: str) -> (pd.DataFrame, pd.DataFrame):
    sas_survey_df = pd.read_csv(sas_survey_output, engine='python', na_values=' ')
    py_survey_df = pd.read_csv(py_survey_output, engine='python', na_values=' ')

    # sas_survey_df.replace(to_replace=-1, value=np.nan, inplace=True)
    # py_survey_df.replace(to_replace=-1, value=np.nan, inplace=True)

    py_survey_df.columns = py_survey_df.columns.str.upper()
    sas_survey_df.columns = sas_survey_df.columns.str.upper()

    py_survey_df = py_survey_df[list(columns_to_extract)]
    sas_survey_df = sas_survey_df[list(columns_to_extract)]

    return sas_survey_df, py_survey_df


def get_differences(sas: pd.DataFrame, ips: pd.DataFrame) -> (pd.DataFrame, Stats):
    def is_equal(series_a, series_b):
        return (series_a == series_b) | ((series_a != series_a) & (series_b != series_b))

    s: Stats = {}
    for a in columns_to_extract:
        sas[a].fillna(0, inplace=True) if sas[a].dtype.kind in 'biufc' else sas[a].fillna("", inplace=True)
        ips[a].fillna(0, inplace=True) if ips[a].dtype.kind in 'biufc' else ips[a].fillna("", inplace=True)
        sas['SAS_' + a] = sas[a]
        sas['IPS_' + a] = ips[a]

        x = np.where(is_equal(sas['SAS_' + a], sas['IPS_' + a]), True, False)
        if x.all():
            continue

        sas[a + "_Match"] = np.where(is_equal(sas['SAS_' + a], sas['IPS_' + a]), True, False)

        match_cnt = sum(x is True for x in sas[a + '_Match'])
        unmatch_cnt = sum(x is False for x in sas[a + '_Match'])
        s[a] = (match_cnt, unmatch_cnt)

        sas[a + "_Diff"] = np.where(sas[a] == ips[a], 0, abs(sas[a] - ips[a])) \
            if sas[a].dtype.kind in 'biufc' \
            else np.where(is_equal(sas[a], ips[a]), "", False)

    sas.drop(list(columns_to_extract), axis=1, inplace=True)

    def get_match_columns():
        cols = []
        for item in columns_to_extract:
            if item + '_Match' in sas:
                cols.append(item + '_Match')
        return cols

    query = ' | '.join(map(lambda x: x + " == False", get_match_columns()))
    if query == '': # we are equal
        return None, s
    return sas.query(query).drop('index', 1), s


def compare_files(sas_output: str, ips_output: str, differences_file: str) -> None:
    df1, df2 = get_datasets(sas_output, ips_output)

    df1.sort_values(by=['SERIAL'], inplace=True)
    df2.sort_values(by=['SERIAL'], inplace=True)

    df1.reset_index(inplace=True)
    df2.reset_index(inplace=True)

    if df2.equals(df1):
        print("Files are equal")
        return

    if len(df1) != len(df2):
        print("Error: files have different row counts")
        return

    sas = df1.copy(deep=True)
    ips = df2.copy(deep=True)

    differences, stats = get_differences(sas, ips)

    if differences is None:
        print("Files are equal")
        return

    writer = pd.ExcelWriter(differences_file, engine='xlsxwriter')

    match = [x for x in differences.columns.values if x.endswith("_Match")]
    c = differences.style.apply(lambda x: ['background-color: yellow' if not v else '' for v in x], subset=match)

    match = [x for x in differences.columns.values if x.endswith("_Diff")]
    c = c.apply(lambda x: ['background-color: yellow' if v else '' for v in x], subset=match)

    df1.to_excel(writer, sheet_name='SAS', freeze_panes=(1, 1), index=False)
    df2.to_excel(writer, sheet_name='IPS', freeze_panes=(1, 1), index=False)

    c.to_excel(writer, sheet_name='Differences', freeze_panes=(1, 1), index=False)

    def get_col_widths(dataframe):
        idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))]) + 8
        return [idx_max] + [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in
                            dataframe.columns]

    sas_worksheet = writer.sheets['SAS']
    sas_worksheet.set_zoom(120)
    for i, width in enumerate(get_col_widths(df1)):
        sas_worksheet.set_column(i, i, width)

    ips_worksheet = writer.sheets['IPS']
    ips_worksheet.set_zoom(120)
    for i, width in enumerate(get_col_widths(df2)):
        ips_worksheet.set_column(i, i, width)

    worksheet = writer.sheets['Differences']
    worksheet.activate()
    worksheet.set_zoom(120)
    for i, width in enumerate(get_col_widths(differences)):
        worksheet.set_column(i, i, width)

    writer.save()

    total = len(df1.index)
    total_unmatched = len(differences)
    total_perc = (total_unmatched / total) * 100.0

    print_stats(differences_file, stats, total, total_perc, total_unmatched)


def print_stats(diff_file: str, stats: Stats, total: int, total_perc: float, total_unmatched: int) -> None:
    print()
    print("Total Items: %5d, Total Unmatched rows: %4d (%3.2f%%), Differences -> %s"
          % (total, total_unmatched, total_perc, diff_file))
    print()
    print("Summary of Unmatched Items:")
    print()
    for key, value in stats.items():
        if value[1] > 0:
            perc = (value[1] / total) * 100.0
            print("%25s: % 4d/%5d, % 3.2f%%" % (key, value[1], total, perc))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="compare", description="Compare SAS and IPS files")
    parser.add_argument("-s", "--sfile", dest="sas_output", required=True,
                        help="SAS file to compare IPS file against")
    parser.add_argument("-i", "--ifile", dest="ips_output", required=True,
                        help="IPS file to compare SAS file against")
    parser.add_argument("-o", "--ofile", dest="differences_file", default="differences.xlsx",
                        help="file to store differences in")

    args = parser.parse_args()

    compare_files(args.sas_output, args.ips_output, args.differences_file)
