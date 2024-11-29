from collections import Counter
from math import floor, ceil
import pandas as pd
import pm4py
from pm4py.algo.transformation.log_to_interval_tree import algorithm as log_to_interval_tree
import os

def print_templates(templates, prefix ="", head=None, fh=None):
    handler = fh.write if fh else print
    handler(f"{prefix} templates:\n")
    for template in list(templates)[:head]:
        handler(f"{template[4]}:{template[3]}  ({template[1]}: {template[2]})\n")
    handler(f"\n")

def export_log_to_csv(records, event_log, convert_to_csv=False):
    if convert_to_csv:
        converted_log = pd.DataFrame(records,
                                     columns=["timestamp", "resource", "req_id", "msg", "pid", "function", "line"])
        converted_log.to_csv(event_log, index=False)

def get_event_log(log):
    # extracts csv into pandas dataframe
    csv_df = pd.read_csv(log, sep=',')
    csv_df.pid = csv_df.pid.astype(str)
    csv_df.req_id = csv_df.req_id.astype(str)

    csv_df['case_id'] = csv_df[['pid', 'req_id']].agg(','.join, axis=1)
    csv_df['case_id'] = csv_df['case_id'].astype(str)
    assert csv_df['case_id'].apply(type).eq(str).all(), "Not all case_id values are strings"

    event_log = pm4py.format_dataframe(csv_df, case_id='case_id', activity_key='msg', timestamp_key='timestamp')
    pm4py.write_xes(event_log, log.replace('csv', 'xes'))

    return csv_df, event_log

def convert_to_interval_tree(event_log, used_templates, interval_step=1, print_head=None):
    # Calculate intervals range for first revision
    it = log_to_interval_tree.apply(event_log)
    start_interval = floor(it.begin()) - 5
    end_interval = ceil(it.end()) + 1

    intervals = range(start_interval + interval_step, end_interval, interval_step)

    # setting columns as intervals
    interval_columns = [f"{i}" for i in intervals]

    #setting rows as the target template name
    df_keys = list(set([record[-1] for record in used_templates]))

    # create DF
    df = pd.DataFrame(0, index=df_keys, columns=interval_columns)

    # fill the DF
    for i in intervals:
        intersecting_events = it[i - interval_step:i]
        counter = Counter((x.data["target_event"]["concept:name"]) for x in intersecting_events)
        for target, count in counter.items():
            df.at[target, f"{i}"] = count

    if print_head:
        print(df.head(print_head))
    return df, intervals

def extract_actions_from_paths(paths, event_log, dir, export=True, prefix=""):
    actions = set()
    for efr in paths:
        filtered_db = pm4py.filtering.filter_between(event_log, *efr)
        actions.update(filtered_db['msg'].unique())

    if export:
        export_effected_paths(paths, event_log, dir, prefix)
    return actions


def export_effected_paths(paths, event_log, dir, prefix):
    filtered_db = pm4py.filtering.filter_eventually_follows_relation(event_log, paths)
    event_log = pm4py.format_dataframe(filtered_db, case_id='case_id', activity_key='msg', timestamp_key='timestamp')
    file = f"{dir}\\{prefix}paths.xes"
    pm4py.write_xes(event_log, file)


def get_test_case_directory(home_directory:str, default_folder:str=None, auto_detect:bool =False) -> [str, str]:
    """
    Detects the base path for test case folder to run with
    :return: test case container folder and specific test case folder
    """

    # Select TEST-CASE folder source
    base = f"{home_directory}"
    if not auto_detect:
        # Use a specific test case run
        log_testcases_folder = os.path.join(base, default_folder)
    else:
        # Search the most recent test case in the TC folder
        all_testcases_folder = [os.path.join(base, d) for d in os.listdir(base) ]
        log_testcases_folder = max(all_testcases_folder, key=os.path.getmtime)

    return log_testcases_folder
