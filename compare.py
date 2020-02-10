import argparse
from typing import Tuple, Dict

import numpy as np
import pandas as pd

columns_to_extract: Tuple[str, ...] = (
    "SERIAL", "SHIFT_WT", "NON_RESPONSE_WT", "MINS_WT", "TRAFFIC_WT", "UNSAMP_TRAFFIC_WT",
    "IMBAL_WT", "FINAL_WT", "STAY", "STAYK", "FARE", "FAREK", "SPEND", "SPENDIMPREASON",
    "SPENDK", "VISIT_WT", "VISIT_WTK", "STAY_WT", "STAY_WTK", "EXPENDITURE_WT", "EXPENDITURE_WTK",
    "NIGHTS1", "NIGHTS2", "NIGHTS3", "NIGHTS4", "NIGHTS5", "NIGHTS6", "NIGHTS7", "NIGHTS8",
    "STAY1K", "STAY2K", "STAY3K", "STAY4K", "STAY5K", "STAY6K", "STAY7K", "STAY8K", "SPEND1",
    "SPEND2", "SPEND3", "SPEND4", "SPEND5", "SPEND6", "SPEND7", "SPEND8", "DIRECTLEG", "OVLEG",
    "UKLEG"
)

Stats = Dict[str, Tuple]


def get_datasets(sas_survey_output: str, py_survey_output: str) -> (pd.DataFrame, pd.DataFrame):
    sas_survey_df = pd.read_csv(sas_survey_output, engine='python', na_values=' ')
    py_survey_df = pd.read_csv(py_survey_output, engine='python', na_values=' ')

    py_survey_df.columns = py_survey_df.columns.str.upper()
    sas_survey_df.columns = sas_survey_df.columns.str.upper()

    py_survey_df = py_survey_df[list(columns_to_extract)]
    sas_survey_df = sas_survey_df[list(columns_to_extract)]

    return sas_survey_df, py_survey_df


def get_differences(sas: pd.DataFrame, ips: pd.DataFrame) -> (pd.DataFrame, Stats):
    sas.sort_values(by=['SERIAL'], inplace=True)
    ips.sort_values(by=['SERIAL'], inplace=True)

    sas.reset_index(inplace=True)
    ips.reset_index(inplace=True)

    def is_equal(series_a, series_b):
        return (series_a == series_b) | ((series_a != series_a) & (series_b != series_b))

    s: Stats = {}
    for a in columns_to_extract:
        sas[a].fillna(0, inplace=True) if sas[a].dtype.kind in 'biufc' else sas[a].fillna("", inplace=True)
        ips[a].fillna(0, inplace=True) if ips[a].dtype.kind in 'biufc' else ips[a].fillna("", inplace=True)
        sas['SAS_' + a] = sas[a]
        sas['IPS_' + a] = ips[a]

        sas[a + "_Match"] = np.where(is_equal(sas['SAS_' + a], sas['IPS_' + a]), True, False)

        match_cnt = sum(x is True for x in sas[a + '_Match'])
        unmatch_cnt = sum(x is False for x in sas[a + '_Match'])
        s[a] = (match_cnt, unmatch_cnt)

        sas[a + "_Diff"] = np.where(sas[a] == ips[a], 0, abs(sas[a] - ips[a])) \
            if sas[a].dtype.kind in 'biufc' \
            else np.where(is_equal(sas[a], ips[a]), "", False)

    sas.drop(list(columns_to_extract), axis=1, inplace=True)
    query = ' | '.join(map(lambda x: x + '_Match' + " == False", columns_to_extract))
    return sas.query(query).drop('index', 1), s


def compare_files(sas_output: str, ips_output: str, differences_file: str) -> None:
    df1, df2 = get_datasets(sas_output, ips_output)
    if df2.equals(df1):
        print("Files are equal")
        return
    if len(df1) != len(df2):
        print("Error: files have different row counts")
        return

    differences, stats = get_differences(df1, df2)

    match = [x for x in differences.columns.values if x.endswith("_Match")]
    c = differences.style.apply(lambda x: ['background-color: yellow' if not v else '' for v in x], subset=match)

    match = [x for x in differences.columns.values if x.endswith("_Diff")]
    c = c.apply(lambda x: ['background-color: yellow' if v else '' for v in x], subset=match)

    c.to_excel(differences_file, sheet_name="Differences", engine='xlsxwriter', index=False, freeze_panes=(1, 1))

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
            print("%20s: % 4d/%5d, % 3.2f%%" % (key, value[1], total, perc))


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
