import argparse
import sys

import numpy as np
import pandas as pd

# List of output columns for each calculation
columns_to_extract = ["SERIAL", "SHIFT_WT", "NON_RESPONSE_WT", "MINS_WT", "TRAFFIC_WT", "UNSAMP_TRAFFIC_WT",
                      "IMBAL_WT", "FINAL_WT", "STAY", "STAYK", "FARE", "FAREK", "SPEND", "SPENDIMPREASON",
                      "SPENDK", "VISIT_WT", "VISIT_WTK", "STAY_WT", "STAY_WTK", "EXPENDITURE_WT", "EXPENDITURE_WTK",
                      "NIGHTS1", "NIGHTS2", "NIGHTS3", "NIGHTS4", "NIGHTS5", "NIGHTS6", "NIGHTS7", "NIGHTS8",
                      "STAY1K", "STAY2K", "STAY3K", "STAY4K", "STAY5K", "STAY6K", "STAY7K", "STAY8K", "SPEND1",
                      "SPEND2", "SPEND3", "SPEND4", "SPEND5", "SPEND6", "SPEND7", "SPEND8", "DIRECTLEG", "OVLEG",
                      "UKLEG"]


def get_datasets(sas_survey_output, py_survey_output):
    sas_survey_df = pd.read_csv(sas_survey_output, engine='python', na_values=' ')
    py_survey_df = pd.read_csv(py_survey_output, engine='python', na_values=' ')

    # Columns to upper string
    py_survey_df.columns = py_survey_df.columns.str.upper()
    sas_survey_df.columns = sas_survey_df.columns.str.upper()

    # Extract columns
    py_survey_df = py_survey_df[columns_to_extract]
    sas_survey_df = sas_survey_df[columns_to_extract]

    # Export to csv
    return sas_survey_df, py_survey_df


def is_equal(a, b):
    return (a == b) | ((a != a) & (b != b))


def get_differences(sas_output, ips_output):
    sas_output.replace("", np.nan, inplace=True)
    ips_output.replace("", np.nan, inplace=True)

    for a in columns_to_extract:
        sas_output['SAS_' + a] = sas_output[a]
        sas_output['IPS_' + a] = ips_output[a]
        sas_output[a + "_Match"] = np.where(is_equal(sas_output[a], ips_output[a]), True, False)

        if sas_output[a].dtypes == "float64":
            sas_output[a + "_Diff"] = np.where(is_equal(sas_output[a], ips_output[a]), 0,
                                           (sas_output[a] - ips_output[a]))
        else:
            sas_output[a + "_Diff"] = np.where(is_equal(sas_output[a], ips_output[a]), "", "False")

        del sas_output[a]

    query = ' | '.join(map(lambda x: x + '_Match' + " == False", columns_to_extract))
    out = sas_output.query(query)

    # for a in columns_to_extract:
    #     del out[a + "_Match"]

    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="compare", description="Compare SAS and IPS files and write difference to CSV file")
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

    differences = get_differences(df1, df2)

    def highlight_max(s):
        is_max = s == False
        return ['background-color: yellow' if v else '' for v in is_max]

    match = []
    l = list(differences.columns.values)
    for a in l:
        if a.endswith("_Match"):
            match.append(a)
    differences.style.\
        apply(highlight_max, subset=match).\
        to_excel(differences_file, engine='xlsxwriter', index=False, freeze_panes=(1, 9999))

    # differences.to_excel(differences_file, engine='xlsxwriter', freeze_panes=(1, 9999), index=False)
    print("All done. Differences are in " + differences_file)
