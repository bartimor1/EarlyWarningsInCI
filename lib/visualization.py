import matplotlib.colors as colors
import numpy as np
import pandas as pd
import pm4py
import seaborn as sns
from IPython.core.display_functions import display
from graphviz import Digraph
from matplotlib import pyplot as plt
from IPython.display import Image

def visualize_efg_w_freq(efg):
    # Create a colormap using matplotlib
    cmap = plt.get_cmap('flare')
    norm = colors.Normalize(vmin=min(efg.values()), vmax=max(efg.values()))

    # Build edge data as a single string with all edges
    edges_str = '\n'.join(f'"{edge[0]}" -> "{edge[1]}" [label="{freq}", color="{colors.rgb2hex(cmap(norm(freq)))}"];'
                          for edge, freq in efg.items())

    # Create a Digraph object
    graph = Digraph(strict=True, body=edges_str.splitlines())
    graph.format = 'png'  # Set the output format to PNG
    Image('output_graph.png')

def visualize_efg_w_duration(ef_pairs):
    # Create a colormap using matplotlib
    cmap = plt.get_cmap('flare')
    norm = colors.Normalize(vmin=min(ef_pairs.values()), vmax=max(ef_pairs.values()))

    # Build edge data as a single string with all edges
    edges_str = '\n'.join(f'"{edge[0]}" -> "{edge[1]}" [label= f"{stat.mean:.2f}s"), color="{colors.rgb2hex(cmap(norm(stat.mean)))}"];'
                          for edge, stat in ef_pairs.items())

    # Create a Digraph object
    graph = Digraph(strict=True, body=edges_str.splitlines())
    graph.format = 'png'  # Set the output format to PNG
    graph.render('output_graph', view=False)

    Image('output_graph.png')

def display_performance_graph(efr, variants_dfg):
    for variant in variants_dfg[efr]:
        # display the first EFR variant performance graph, by mean aggregation
        pm4py.view_performance_dfg(*variants_dfg[efr][0][0:3], aggregation_measure ="mean")

def display_max_occurrences_in_case(msg_stats_v1, msg_stats_v2):


    msg_stats_v2_max = msg_stats_v2.copy()
    msg_stats_v1_max = msg_stats_v1.copy()
    indices = [index for index in msg_stats_v1_max.index if
               msg_stats_v2_max.loc[index, 'max'] == msg_stats_v1_max.loc[index, 'max']]
    msg_stats_v2_max.drop(indices, inplace=True)
    msg_stats_v1_max.drop(indices, inplace=True)

    msg_stats_v2_max.reset_index(drop=False, inplace=True, col_fill='msg')
    msg_stats_v1_max.reset_index(drop=False, inplace=True, col_fill='msg')
    df_freq_max = pd.concat([msg_stats_v1_max, msg_stats_v2_max])

    sns.set_theme(style="white", context="talk")

    plt.figure(figsize=(20, 10))
    ax = sns.barplot(data=df_freq_max, x='msg', y='max', hue='Version', palette="rocket")
    ax.axhline(0, color="k", clip_on=False)
    ax.bar_label(ax.containers[0], fontsize=10);
    ax.bar_label(ax.containers[1], fontsize=10);
    ax.set_ylabel("Max Occurrences in case", fontsize=24)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=90, horizontalalignment='center')

    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.show()