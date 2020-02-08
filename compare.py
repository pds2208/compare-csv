import argparse
import sys

import numpy as np
import pandas as pd

columns_to_extract = [
    "SERIAL", "SHIFT_WT", "NON_RESPONSE_WT", "MINS_WT", "TRAFFIC_WT", "UNSAMP_TRAFFIC_WT",
    "IMBAL_WT", "FINAL_WT", "STAY", "STAYK", "FARE", "FAREK", "SPEND", "SPENDIMPREASON",
    "SPENDK", "VISIT_WT", "VISIT_WTK", "STAY_WT", "STAY_WTK", "EXPENDITURE_WT", "EXPENDITURE_WTK",
    "NIGHTS1", "NIGHTS2", "NIGHTS3", "NIGHTS4", "NIGHTS5", "NIGHTS6", "NIGHTS7", "NIGHTS8",
    "STAY1K", "STAY2K", "STAY3K", "STAY4K", "STAY5K", "STAY6K", "STAY7K", "STAY8K", "SPEND1",
    "SPEND2", "SPEND3", "SPEND4", "SPEND5", "SPEND6", "SPEND7", "SPEND8", "DIRECTLEG", "OVLEG",
    "UKLEG"
]


def get_datasets(sas_survey_output, py_survey_output):
    sas_survey_df = pd.read_csv(sas_survey_output, engine='python', na_values=' ')
    py_survey_df = pd.read_csv(py_survey_output, engine='python', na_values=' ')

    py_survey_df.columns = py_survey_df.columns.str.upper()
    sas_survey_df.columns = sas_survey_df.columns.str.upper()

    py_survey_df = py_survey_df[columns_to_extract]
    sas_survey_df = sas_survey_df[columns_to_extract]

    return sas_survey_df, py_survey_df


def is_equal(a, b):
    return (a == b) | ((a != a) & (b != b))


def get_differences(sas, ips):
    sas.fillna(0, inplace=True)
    ips.fillna(0, inplace=True)

    sas.sort_values(by=['SERIAL'], inplace=True)
    ips.sort_values(by=['SERIAL'], inplace=True)

    sas.reset_index(inplace=True)
    ips.reset_index(inplace=True)

    stats = {}
    for a in columns_to_extract:
        sas['SAS_' + a] = sas[a]
        sas['IPS_' + a] = ips[a]
        sas[a + "_Match"] = np.where(is_equal(sas[a], ips[a]), True, False)

        match_cnt = sum(x is True for x in sas[a + '_Match'])
        unmatch_cnt = sum(x is False for x in sas[a + '_Match'])
        stats[a] = (match_cnt, unmatch_cnt)

        if sas[a].dtypes == "float64":
            sas[a + "_Diff"] = (
                np.where(is_equal(sas[a], ips[a]), 0, abs(sas[a] - ips[a]))
            )
        else:
            sas[a + "_Diff"] = (
                np.where(is_equal(sas[a], ips[a]), "", "False")
            )

        del sas[a]

    query = ' | '.join(map(lambda x: x + '_Match' + " == False", columns_to_extract))
    return sas.query(query).drop('index', 1), stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="compare", description="Compare SAS and IPS files")
    parser.add_argument("-s", "--sfile", dest="sas_output", required=True,
                        help="SAS file to compare IPS file against")
    parser.add_argument("-i", "--ifile", dest="ips_output", required=True,
                        help="IPS file to compare SAS file against")
    parser.add_argument("-o", "--ofile", dest="differences_file", default="differences.xlsx",
                        help="file to store differences in")

    args = parser.parse_args()
    sas_output = args.sas_output
    ips_output = args.ips_output
    differences_file = args.differences_file

    df1, df2 = get_datasets(sas_output, ips_output)
    if df2.equals(df1):
        print("files are equal")
        sys.exit(0)

    differences, stats = get_differences(df1, df2)

    match = [x for x in differences.columns.values if x.endswith("_Match")]

    c = differences.style.apply(lambda x: ['background-color: yellow' if not v else '' for v in x], subset=match)
    c.to_excel(differences_file, sheet_name="Differences", engine='xlsxwriter', index=False, freeze_panes=(1, 1))

    print("All done. Differences are in " + differences_file)
    print("Unmatched items:")
    print()
    for key, value in stats.items():
        if value[1] > 0:
            perc = (value[1] / len(df1.index)) * 100.0
            print("%20s: % 4d/%5d, % 3.2f%%" % (key, value[1], len(df1.index), perc))
