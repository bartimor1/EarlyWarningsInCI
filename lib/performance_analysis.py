# record for the
import statistics
from collections import defaultdict
from dataclasses import make_dataclass
from datetime import datetime
from math import ceil

import pandas as pd
import re
from .visualization import display_performance_graph
import pm4py


class performance2():
    def __init__(self, mean=0, maximum=0, minimum=100000, median=0, sum=0):
        self.mean = mean
        self.maximum = maximum
        self.minimum = minimum
        self.freq = []
        self.median = median
        self.sum = sum
        self.duration = []
        self.median_duration = []
        self.num_of_variants = 0  # in how many variants the EF occur

    def __repr__(self):
        return (f"mean: {self.mean}, max: {self.maximum}, min: {self.minimum}, median:{self.median}, "
                f"freq: {self.freq}, duration:{self.duration}")

    def __str__(self):
        return (f"mean: {self.mean}, max: {self.maximum}, min: {self.minimum}, median:{self.median}, "
                f"freq: {self.freq}, duration:{self.duration}")


def extract_ef_performance(efg, event_log):
    processed_ef_pairs = defaultdict(performance2)
    variants_dfg = defaultdict(list)
    variants = pm4py.get_variants_as_tuples(event_log, activity_key='concept:name', case_id_key='case:concept:name',
                                            timestamp_key='time:timestamp')

    # for each variant in the process we will check which EFR belong to it.
    # once we found that a certain EFR belongs to a variant, we will calculate its duration
    # in the variant and keep the path from the start activity to the end activity
    for idx, variant in enumerate(variants):
        filtered_by_var_df = pm4py.filter_variants(event_log, [variant], activity_key='concept:name',
                                                   case_id_key='case:concept:name', timestamp_key='time:timestamp')
        perf_dfg, start_act, end_act = pm4py.discovery.discover_performance_dfg(filtered_by_var_df,
                                                                                activity_key='concept:name',
                                                                                case_id_key='case:concept:name',
                                                                                timestamp_key='time:timestamp')


        for pair_ef in efg:
            start = 0
            end = 0

            #check both start activity and end activity in the varaint
            if any([pair_ef[0] not in variant, pair_ef[1] not in variant]):
                continue

            while True:
                v_duration = 0
                v_max_duration = 0
                v_min_duration = 0
                v_median_duration = 0

                try:
                    #search for the start activity from the last location and the end activity from last location +1
                    start, end = variant.index(pair_ef[0], end), variant.index(pair_ef[1], end + 1)
                except Exception as e:
                    break

                if end <= start:
                    try:  # find if there is another instance of the relation end
                        end = variant.index(pair_ef[1], start + 1)
                    except Exception as e:
                        continue

                path = variant[start:end + 1]

                variants_dfg[pair_ef].append((perf_dfg, start_act, end_act, path, start, end, variant))

                for i in range(len(path) - 1):
                    df = (path[i], path[i + 1])
                    v_median_duration += perf_dfg[df]['median']
                    v_duration += perf_dfg[df]['mean']
                    v_max_duration += perf_dfg[df]['max']
                    v_min_duration += perf_dfg[df]['min']

                v_freq = variants[variant]
                processed_ef_pairs[pair_ef].freq.append(v_freq)
                processed_ef_pairs[pair_ef].duration.append(v_duration)
                processed_ef_pairs[pair_ef].median_duration.append(v_median_duration)

                if processed_ef_pairs[pair_ef].maximum < v_max_duration:
                    processed_ef_pairs[pair_ef].maximum = v_max_duration
                if processed_ef_pairs[pair_ef].minimum > v_min_duration:
                    processed_ef_pairs[pair_ef].minimum = v_min_duration

    for pair in processed_ef_pairs:
        if processed_ef_pairs[pair].duration and processed_ef_pairs[pair].freq:
            processed_ef_pairs[pair].mean = sum([dur * freq for dur, freq in zip(processed_ef_pairs[pair].duration,
                                                                                 processed_ef_pairs[pair].freq)]) / sum(processed_ef_pairs[pair].freq)
        processed_ef_pairs[pair].median = sum(processed_ef_pairs[pair].median_duration) / len(
            processed_ef_pairs[pair].median_duration)

    return processed_ef_pairs, variants_dfg


def calc_output_rate(look_on_actions, intervals, df, event_log, suffix=""):
    df_output_rate = pd.DataFrame(0,index=list(look_on_actions), columns=[f"absolute freq {suffix}",
                                                                      f"max queue {suffix}",
                                                                      f"median queue {suffix}",
                                                                      f"TP rate {suffix}",
                                                                      f"max occurrences in case {suffix}"])
    for e_act in look_on_actions:
        # get end activity queue in first df
        queue = df.loc[e_act, :].values.flatten().tolist()

        # calculate total freq
        act_occur = event_log.loc[event_log['msg']==e_act]
        total_freq = len(act_occur)
        df_output_rate.loc[e_act, f"absolute freq {suffix}"] = total_freq

        # calculate max queue size for period
        max_v = max(queue)
        df_output_rate.loc[e_act, f"max queue {suffix}"] = max_v  if any(queue) else 0

        # calculate median queue size for period without zero
        df_output_rate.loc[e_act, f"median queue {suffix}"] = float(statistics.median(
            sorted(list(filter(lambda num: num != 0, queue))))) if any(queue) else 0

        # calculate total cases and normalized TP
        num_of_cases = len(act_occur.groupby(['case_id']).size())
        tp_rate = num_of_cases/len(intervals)
        norm_factor = total_freq/num_of_cases if num_of_cases else 1
        df_output_rate.loc[e_act, f"TP rate {suffix}"] = float("{:.5f}".format(tp_rate/norm_factor))

    return df_output_rate

def find_diff(efr_perf_v1, efr_perf_v2, variants_v1, variants_v2, threshold=0.05, print_head=5, visualize=False):
    counter_degraded = 0
    counter_improved = 0
    counter = 0
    degradation_dict = {}
    improvement_dict = {}
    # Find common EFRs in the logs
    intersections = list(set(efr_perf_v1).intersection(efr_perf_v2))
    list_to_display = []
    # Compare common between EF dicts performance
    for efr in intersections:
        counter += 1
        # Note: We use round to avoid comparing small decimal numbers
        if ceil(efr_perf_v2[efr].mean) > ceil(efr_perf_v1[efr].mean * (1 + threshold)):
            counter_degraded += 1
            degradation_dict[efr] = {"v1": variants_v1[efr], "v2": variants_v2[efr],
                                     "diff": efr_perf_v2[efr].mean - efr_perf_v1[efr].mean,
                                     "v1_freq":  efr_perf_v1[efr].freq, "v2_freq": efr_perf_v2[efr].freq}
            list_to_display.append((efr, efr_perf_v2[efr].mean - efr_perf_v1[efr].mean,
                                    f"{efr_perf_v1[efr].mean:.3f}/{efr_perf_v2[efr].mean:.3f}",
                                    f"{sum(efr_perf_v1[efr].freq)}/{sum(efr_perf_v2[efr].freq)}"))
        elif efr_perf_v1[efr].mean * (1 - threshold) > efr_perf_v2[efr].mean:
            counter_improved += 1
            improvement_dict[efr] = {"v1": variants_v1[efr], "v2": variants_v2[efr],
                                     "diff": efr_perf_v2[efr].mean - efr_perf_v1[efr].mean,
                                     "v1_freq": efr_perf_v1[efr].freq, "v2_freq": efr_perf_v2[efr].freq}

    list_to_display.sort(key=lambda x: x[1], reverse=True)
    for efr, gap, duration, freq in list_to_display[:print_head]:
        print(f"==============Example for degradation of mean duration==============")
        print(f"{efr}:\nmean delay EF (before/after): {duration}")
        print(f"frequency EF (before/after): {freq}\n ")

        if visualize:
            print("V1:")
            display_performance_graph(efr, variants_v1)
            print("V2:")
            display_performance_graph(efr, variants_v2)

    print(
        f"{counter_degraded}/{counter} ({counter_degraded / counter * 100:.2f}%) EF relation had degradation of more than "
        f"{threshold} seconds in mean performance")
    print(
        f"{counter_improved}/{counter} ({counter_improved / counter * 100:.2f}%) EF relation has improved of more than "
        f"{threshold} seconds in mean performance")
    return degradation_dict, improvement_dict

def find_df_degradations_in_paths(degradation_dict, event_log_v1, event_log_v2, print_head=5, threshold=0.05):
    df_degraded = set()
    for pair_ef in dict(sorted(degradation_dict.items(), key=lambda item: item[1]["diff"], reverse=True)):
        filtered_df_b = pm4py.filter_eventually_follows_relation(event_log_v1, [pair_ef],
                                                                 activity_key='concept:name',
                                                                 case_id_key='case:concept:name',
                                                                 timestamp_key='time:timestamp')
        perf_dfg_b, start_act_b, end_act_b = pm4py.discovery.discover_performance_dfg(filtered_df_b,
                                                                                      activity_key='concept:name',
                                                                                      case_id_key='case:concept:name',
                                                                                      timestamp_key='time:timestamp')

        filtered_df_a = pm4py.filter_eventually_follows_relation(event_log_v2, [pair_ef],
                                                                 activity_key='concept:name',
                                                                 case_id_key='case:concept:name',
                                                                 timestamp_key='time:timestamp')
        perf_dfg_a, start_act_a, end_act_a = pm4py.discovery.discover_performance_dfg(filtered_df_a,
                                                                                      activity_key='concept:name',
                                                                                      case_id_key='case:concept:name',
                                                                                      timestamp_key='time:timestamp')

        df_intersections = list(set(perf_dfg_b.keys()).intersection(perf_dfg_a.keys()))
        for pair in df_intersections[:print_head]:
            # Note: We use round to avoid comparing small decimal numbers
            if round(perf_dfg_a[pair]['mean']) > round(perf_dfg_b[pair]['mean'] * (1 + threshold)):
                df_degraded.add((*pair, perf_dfg_a[pair]['mean'] - perf_dfg_b[pair]['mean']))
    print(f"top 10 sorted by diff:{sorted(df_degraded, key=lambda x: x[2], reverse=True)[:10]}")
    print(f"Overall {len(df_degraded)} were degraded")
    return df_degraded