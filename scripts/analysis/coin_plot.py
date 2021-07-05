#!/usr/bin/env python3

import pdb
import argparse
import pandas as pd
import numpy as np
import scipy.stats as st

from pandas import read_csv
from pandas import DataFrame
from pandas import Grouper
from matplotlib import pyplot as plt

FUZZERS = ['AFLNet', 'AFLNet_Legion']


# FUZZERS = ['AFLNet_Legion']


def main(csv_file, put, runs, cut_off, step, out_file,
         message, legion_version, profuzzbench_version, profuzzbench_clean, excluded_fuzzer, excluded_run):

    excluded_fuzzer = excluded_fuzzer if excluded_fuzzer else []
    excluded_run = excluded_run if excluded_run else []
    excluded_pairs = list(zip(excluded_fuzzer, excluded_run))

    # Read the results
    df = read_csv(csv_file)

    # Calculate the mean of code coverage
    # Store in a list first for efficiency
    mean_list = []
    each_list = []
    max_list = []
    min_list = []
    median_list = []
    ci_list = []
    ci_low_list = []
    ci_high_list = []

    for subject in [put]:
        for fuzzer in FUZZERS:
            fuzzer = fuzzer.lower()
            for cov_type in ['b_abs', 'b_per', 'l_abs', 'l_per']:
                # get subject & fuzzer & cov_type-specific dataframe
                df1 = df[(df['subject'] == subject) &
                         (df['fuzzer'] == fuzzer) &
                         (df['cov_type'] == cov_type)]

                mean_list.append((subject, fuzzer, cov_type, 0, 0.0))
                max_list.append((subject, fuzzer, cov_type, 0, 0.0))
                min_list.append((subject, fuzzer, cov_type, 0, 0.0))
                median_list.append((subject, fuzzer, cov_type, 0, 0.0))
                ci_list.append((subject, fuzzer, cov_type, 0, (0.0, 0.0)))
                ci_low_list.append((subject, fuzzer, cov_type, 0, 0.0))
                ci_high_list.append((subject, fuzzer, cov_type, 0, 0.0))
                for run in range(1, runs + 1, 1):
                    if (fuzzer, str(run)) in excluded_pairs:
                        continue
                    each_list.append((subject, "{}_{}".format(fuzzer, run), cov_type, 0, 0.0))

                for time in range(1, cut_off + 1, step):
                    cov_total = 0
                    run_count = 0
                    cov_list = []

                    for run in range(1, runs + 1, 1):
                        if (fuzzer, str(run)) in excluded_pairs:
                            continue
                        cov_each = 0
                        # get run-specific data frame
                        df2 = df1[df1['run'] == run]

                        # get the starting time for this run
                        start = df2.iloc[0, 0]

                        # get all rows given a cutoff time
                        df3 = df2[df2['time'] <= start + time * 60]

                        # update total coverage and #runs
                        cov_total += df3.tail(1).iloc[0, 5]
                        cov_list.append(df3.tail(1).iloc[0, 5])

                        each_list.append((subject, "{}_{}".format(fuzzer, run), cov_type, time, df3.tail(1).iloc[0, 5]))

                        run_count += 1

                    # add a new row
                    mean_list.append((subject, fuzzer, cov_type, time, cov_total / run_count))
                    max_list.append((subject, fuzzer, cov_type, time, max(cov_list)))
                    min_list.append((subject, fuzzer, cov_type, time, min(cov_list)))
                    median_list.append((subject, fuzzer, cov_type, time, sorted(cov_list)[run_count//2]))

                    ci = st.t.interval(0.95, len(cov_list)-1, loc=np.mean(cov_list), scale=st.sem(cov_list))
                    ci_list.append((subject, fuzzer, cov_type, time, ci))
                    ci_low_list.append(np.mean(cov_list) - ci)
                    ci_high_list.append(np.mean(cov_list) + ci)

    # Convert the list to a dataframe
    mean_df = pd.DataFrame(mean_list, columns=['subject', 'fuzzer', 'cov_type', 'time', 'cov'])
    each_df = pd.DataFrame(each_list, columns=['subject', 'fuzzer', 'cov_type', 'time', 'cov'])
    max_df = pd.DataFrame(max_list, columns=['subject', 'fuzzer', 'cov_type', 'time', 'cov'])
    min_df = pd.DataFrame(min_list, columns=['subject', 'fuzzer', 'cov_type', 'time', 'cov'])
    median_df = pd.DataFrame(median_list, columns=['subject', 'fuzzer', 'cov_type', 'time', 'cov'])
    ci_df = pd.DataFrame(ci_list, columns=['subject', 'fuzzer', 'cov_type', 'time', 'cov'])
    ci_low_df = pd.DataFrame(ci_low_list, columns=['subject', 'fuzzer', 'cov_type', 'time', 'cov'])
    ci_high_df = pd.DataFrame(ci_high_list, columns=['subject', 'fuzzer', 'cov_type', 'time', 'cov'])

    fig, axes = plt.subplots(2, 2, figsize=(20, 10))
    title = "Code coverage analysis: {}\n{}\n{}\n{}\n{}".format(
        subject, message, legion_version[:-1], profuzzbench_version, profuzzbench_clean)
    fig.suptitle(title)

    for data_frame in [ci_df, mean_df]:
        legends = [[], [], [], []]
        alpha = 0.2 if data_frame is each_df else 1
        if data_frame is max_df or data_frame is min_df:
            line_style = ':'
        elif data_frame is median_df:
            line_style = '--'
        else:
            line_style = '-'
        for key, grp in data_frame.groupby(['fuzzer', 'cov_type']):
            colour = 'C3' if 'legion' in key[0] else 'C0'
            alpha = 0.2
            if key[1] == 'b_abs':
                if data_frame is ci_df:
                    low = [ci[0] for ci in grp['cov']]
                    high = [ci[1] for ci in grp['cov']]
                    axes[0, 0].fill_between(grp['time'], low, high,
                                            color=colour, alpha=alpha)
                else:
                    axes[0, 0].plot(grp['time'],
                                    grp['cov'],
                                    color=colour,
                                    linestyle=line_style)
                legends[0].append(key[0])
                # axes[0, 0].set_title('Edge coverage over time (#edges)')
                axes[0, 0].set_xlabel('Time (in min)')
                axes[0, 0].set_ylabel('#edges')
            if key[1] == 'b_per':
                if data_frame is ci_df:
                    # pdb.set_trace()
                    low = [ci[0] for ci in grp['cov']]
                    high = [ci[1] for ci in grp['cov']]
                    axes[1, 0].fill_between(grp['time'], low, high,
                                            color=colour, alpha=alpha)
                else:
                    axes[1, 0].plot(grp['time'],
                                    grp['cov'],
                                    color=colour,
                                    linestyle=line_style)
                legends[1].append(key[0])
                axes[1, 0].set_ylim([0, 100])
                axes[1, 0].set_xlabel('Time (in min)')
                axes[1, 0].set_ylabel('Edge coverage (%)')

            if key[1] == 'l_abs':
                if data_frame is ci_df:
                    # pdb.set_trace()
                    low = [ci[0] for ci in grp['cov']]
                    high = [ci[1] for ci in grp['cov']]
                    axes[0, 1].fill_between(grp['time'], low, high,
                                            color=colour, alpha=alpha)
                else:
                    axes[0, 1].plot(grp['time'],
                                    grp['cov'],
                                    color=colour,
                                    linestyle=line_style)
                legends[2].append(key[0])
                # axes[0, 0].set_title('Edge coverage over time (#edges)')
                axes[0, 1].set_xlabel('Time (in min)')
                axes[0, 1].set_ylabel('#lines')
            if key[1] == 'l_per':
                if data_frame is ci_df:
                    # pdb.set_trace()
                    low = [ci[0] for ci in grp['cov']]
                    high = [ci[1] for ci in grp['cov']]
                    axes[1, 1].fill_between(grp['time'], low, high,
                                            color=colour, alpha=alpha)
                else:
                    axes[1, 1].plot(grp['time'],
                                    grp['cov'],
                                    color=colour,
                                    linestyle=line_style)
                legends[3].append(key[0])
                axes[1, 1].set_ylim([0, 100])
                axes[1, 1].set_xlabel('Time (in min)')
                axes[1, 1].set_ylabel('Line coverage (%)')

    for i in range(0, 2):
        for j in range(0, 2):
            axes[j, i].legend(tuple(legends[2 * i + j]), loc='best')
            axes[j, i].grid()

    # Save to file
    plt.savefig(out_file)


# Parse the input arguments
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--csv_file', type=str, required=True, help="Full path to results.csv")
    parser.add_argument('-p', '--put', type=str, required=True, help="Name of the subject program")
    parser.add_argument('-r', '--runs', type=int, required=True, help="Number of runs in the experiment")
    parser.add_argument('-c', '--cut_off', type=int, required=True, help="Cut-off time in minutes")
    parser.add_argument('-s', '--step', type=int, required=True, help="Time step in minutes")
    parser.add_argument('-o', '--out_file', type=str, required=True, help="Output file")
    parser.add_argument('-m', '--message', type=str, required=True, help="the hyper-parameter setting")
    parser.add_argument('-lv', '--legion_version', type=str, required=True, help="the version of AFLNet_Legion")
    parser.add_argument('-pv', '--profuzzbench_version', type=str, required=True, help="the version of ProFuzzBench")
    parser.add_argument('-pc', '--profuzzbench_clean', type=str, required=True, help="If ProFuzzBench is clean")
    parser.add_argument('-ef', '--exclude_fuzzer', action='append', required=False, help="Exclude fuzzers")
    parser.add_argument('-er', '--exclude_run', action='append', required=False, help="Exclude runs")
    args = parser.parse_args()
    main(args.csv_file, args.put, args.runs, args.cut_off, args.step, args.out_file,
         args.message, args.legion_version, args.profuzzbench_version, args.profuzzbench_clean, args.exclude_fuzzer, args.exclude_run)
