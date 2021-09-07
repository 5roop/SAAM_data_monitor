import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "serif"

from utils import acquire as ac 
from utils import DATA_COLLECTIONS
import datetime 
import diskcache as dc

cache = dc.Cache("cache/")

# def memoize(f):
#     global cache
#     def inner(*args, **kwargs):
#         key = f"{args}|{kwargs}"
#         is_future = args[2] > datetime.datetime.utcnow()
#         try:   
#             print("Using cached version.")
#             return cache[key]
#         except Exception:
#             res = f(*args, **kwargs)
#             if not is_future:
#                 cache[key] = res
#             return res
#     return inner
# @memoize

@cache.memoize()
def make_figure(loc_id, start_date, end_date, base, plot_type, **kwargs):
    if plot_type == 'plot bed sensor data':
        return plot_bed(loc_id, start_date, end_date, base, **kwargs)
    if plot_type == 'check data presence':
        return plot_status(loc_id, start_date, end_date, base, **kwargs)
    if plot_type == "plot clip sensor data":
        return plot_clip(loc_id, start_date, end_date, base, **kwargs)
    if plot_type == 'plot cooking':
        return plot_cooking(loc_id, start_date, end_date, base, **kwargs)
    if plot_type == 'plot walking':
        return plot_clip_mobility(loc_id, start_date, end_date, base, **kwargs)


def plot_bed(loc_id, start, end, base, **kwargs):
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
    ax.set_xlim((start, end))
    end = end + datetime.timedelta(hours=2)
    # Sensor raw data acquisition

    if not kwargs.get("skip_mags", False):
        payload = list()
        for collection in DATA_COLLECTIONS:
            payload += ac.download(loc_id, {"$regex":"sens_bed_accel_"}, start, end, base=base, collection=collection)
        # payload = ac.download(loc_id, {"$regex":"sens_bed_accel_"}, start, end, base=base)
        # payload += ac.download(loc_id, {"$regex":"sens_bed_accel_"}, start, end, base=base, )
        for suffix in ["egw", "amb", "app"]:
            cur_payload = [item for item in payload if item["SourceId"]==f'sens_bed_accel_{suffix}']
            if cur_payload == []:
                print(f"No data for {suffix}.")
                continue
            t, m = ac.magnitude_response_to_data(cur_payload)
            ax.plot(pd.to_datetime(t, unit="ms"), m, label=suffix)
    # Peak plotting:
    extended_start = start - datetime.timedelta(days=1)
    extended_end = end + datetime.timedelta(days=1)
    pks = ac.download(loc_id, "feat_bed_accel_magnitude_peaks", extended_start, extended_end, collection="CoachingAdditionalDataSources", base=base)
    if pks:
        ls, ss = ac.peak_handler(pks)
        ax.vlines(pd.to_datetime(ls, unit="s"), 0, 2, label="Large peaks", colors="r", linestyles="dashed", zorder=1)
        ax.vlines(pd.to_datetime(ss, unit="s"), 0.5, 1.5, label="Small peaks", colors="g", linestyles="dotted", zorder=1)
    else:
        ax.text(start, 0.7, "No peak data available")
        ax.set_ylim((0,2))
    sleep_state = ac.download(loc_id, "feat_sleep_state", extended_start, extended_end, collection="CoachingAdditionalDataSources", base=base)
    if sleep_state:
        outs, ins, sleeps = ac.state_handler(sleep_state)
        for i, item in enumerate(outs):
            item = pd.to_datetime([*item], unit="s")
            if i==0:
                ax.hlines(0.5, item[0], item[1],
                      lw=10, colors="k", label="Out of bed")
            else:
                ax.hlines(0.5, item[0], item[1],
                      lw=10, colors="k")
        for i, item in enumerate(ins):
            item = pd.to_datetime([*item], unit="s")
            if i==0:
                ax.hlines(0.5, item[0], item[1],
                      lw=10, colors="r", label="In bed")
            else:
                ax.hlines(0.5, item[0], item[1],
                      lw=10, colors="r",)
        for i, item in enumerate(sleeps):
            item = pd.to_datetime([*item], unit="s")
            if i==0:
                ax.hlines(0.5, item[0], item[1],
                      lw=10, colors="tab:orange", label="Sleeping")
            else:
                ax.hlines(0.5, item[0], item[1],
                      lw=10, colors="tab:orange",)
    else:
        ax.text(start, 0.5, "No sleep state available")
    
    ax.legend()
    ax.set_title(f"{loc_id} bed sensor data, {base} database")
    ax.set_ylabel("Magnitude (g)")
    ax.set_xlabel("Datetime (UTC)")
    fig.autofmt_xdate()
    return fig





def plot_status(loc_id, start_date, end_date, base, **kwargs):
    from .acquire import check_source_presence#_2 as check_source_presence
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
    if "freq" not in kwargs.keys():
        freq = "1h"
    else:
        freq = kwargs["freq"]
    feature_list = ["sens_bed_accel_amb",
                    "sens_bed_accel_egw",
                    #"sens_bed_accel_app"
                    "sens_uwb_activity",
                    "sens_amb_1_temp",
                    "_power_",
                    *[f"sens_belt_accel_{i}" for i in [
                                                        'amb', 
                                                        'app',
                                                        'egw']],
                    ]
    for i, source_id in enumerate(feature_list):
        timerange, is_data = check_source_presence(
                        loc_id, 
                        source_id,
                        start_date, 
                        end_date, 
                        base = base,
                        freq = freq)
        jitter_factor = 0.05 # This shifts the points a bit to prevent overlap
        jitter = i * jitter_factor
        ax.scatter(timerange[:len(is_data)],
                    is_data + jitter, 
                    label=source_id.replace("_", " "),
                    alpha=1,
                    s = 4,
                    )
        #breakpoint()
    ax.legend(loc="center right",  ncol=2)
    # ax.set_ylim((-0.1, 1.1))
    ax.set_xlim((start_date, end_date))
    ax.set_ylabel(f"Data present in {freq} intervals?")
    ax.set_yticks([0,1], )
    ax.set_yticklabels(["False", "True"])
    ax.set_ylim([-0.2, 1.5])
    ax.set_title(f"{loc_id}, sensor data on {base} database")
    fig.autofmt_xdate()
    return fig

def plot_status_mobility(loc_id, start_date, end_date, base, **kwargs):
    from .acquire import check_source_presence#_2 as check_source_presence
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
    if "freq" not in kwargs.keys():
        freq = "1h"
    else:
        freq = kwargs["freq"]
    feature_list = [#"sens_bed_accel_amb",
                    #"sens_bed_accel_egw",
                    #"sens_bed_accel_app"
                    #"sens_uwb_activity",
                    #"sens_amb_1_temp",
                    #"_power_",
                    *[f"sens_belt_accel_{i}" for i in [
                                                        'amb', 
                                                        'app',
                                                        'egw']],
                    ]
    for i, source_id in enumerate(feature_list):
        timerange, is_data = check_source_presence(
                        loc_id, 
                        source_id,
                        start_date, 
                        end_date, 
                        base = base,
                        freq = freq)
        jitter_factor = 0.05 # This shifts the points a bit to prevent overlap
        jitter = i * jitter_factor
        ax.scatter(timerange[:len(is_data)],
                    is_data + jitter, 
                    label=source_id.replace("_", " "),
                    alpha=1,
                    s = 4,
                    )
        #breakpoint()
    ax.legend(loc="center right",  ncol=2)
    # ax.set_ylim((-0.1, 1.1))
    ax.set_xlim((start_date, end_date))
    ax.set_ylabel(f"Data present in {freq} intervals?")
    ax.set_yticks([0,1], )
    ax.set_yticklabels(["False", "True"])
    ax.set_ylim([-0.2, 1.5])
    ax.set_title(f"{loc_id}, sensor data on {base} database")
    fig.autofmt_xdate()
    return fig
def plot_clip(loc_id, start, end, base, **kwargs):
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)

    try:
        payload = list()
        for collection in DATA_COLLECTIONS:
            payload += ac.download(
                loc_id,
                {"$regex": "_accel_"},
                start,
                end + datetime.timedelta(hours=2),
                base=base,
                collection=collection)
        for placement in ["bed",
                          "belt",
                          "bracelet_right",
                          "bracelet_left",
                          "ankle",
                          "bracelet_right "]:
            for suffix in ["egw", "amb", "app"]:
                founds = [item for item in payload if item["SourceId"] == f"sens_{placement}_accel_{suffix}"]
                if founds == []:
                    continue
                t, m = ac.magnitude_response_to_data(founds)
                ax.plot(
                    pd.to_datetime(t, unit="ms"),
                    m,
                    label = f"{placement} {suffix}",
                    alpha = 0.8)
        ax.legend()
    except Exception as e:
        ax.text(start, 1, f"Accelerometry querying raised {e}")
        ax.text(start, 0.7, f"Got exception: {e}")
        ax.set_ylim((0, 1.5))
    ax.set_xlim((start, end))
    ax.set_title(f"{loc_id} clip sensor data, {base} database")
    ax.set_ylabel("Magnitude (g)")

    ax.set_xlabel("Datetime (UTC)")
    fig.autofmt_xdate()
    return fig

def plot_clip_mobility(loc_id, start, end, base, **kwargs):
    fig, [ax, ax2] = plt.subplots(figsize=(8, 5), dpi=100, nrows=2, sharex=True)

    try:
        payload = list()
        for collection in DATA_COLLECTIONS:
            payload += ac.download(
                loc_id,
                {"$regex": "_accel_"},
                start,
                end + datetime.timedelta(hours=2, minutes=5),
                base=base,
                collection=collection)
        for placement in ["belt",
                          "bracelet_right",
                          "bracelet_left",
                          "ankle",
                          "bracelet_right "]:
            for suffix in ["egw", "amb", "app"]:
                founds = [item for item in payload if item["SourceId"] == f"sens_{placement}_accel_{suffix}"]
                if founds == []:
                    continue
                t, m = ac.magnitude_response_to_data(founds)
                ax.plot(
                    pd.to_datetime(t, unit="ms"),
                    m,
                    label = f"{placement} {suffix}",
                    alpha = 0.8)
        ax.legend()
        ax.set_xlim((start, end))
    except Exception as e:
        if len(t) == 0:
            ax.text(start, 1, f"No raw magnitude data to plot")
            ax.set_title("No raw magnitude data to plot")
        else:
            ax.text(start, 1, f"Accelerometry querying raised {e}")
            ax.text(start, 0.7, f"Got exception: {e}")
        ax.set_ylim((0, 1.5))
    
    ax.set_title(f"{loc_id} clip sensor data, {base} database\nmobility instructed")
    ax.set_ylabel("Magnitude (g)")
    ax.set_xlabel("Datetime (UTC)")
    ax2.set_ylabel("feat_mobility_activity")
    try:
        payload = ac.download_coaching_walking(loc_id,
            start, end + datetime.timedelta(hours=2),  base = base
            )
        ts = [item["Data"]["Timestamp"] for item in payload]
        states = [item["Data"]["Measurements"][0] for item in payload]
        ax2.scatter(pd.to_datetime(ts, unit="ms",),
            states,
            s=4)
        ax2.set_xlabel(f"UTC datetime")
    except Exception as e:
        #breakpoint()
        if len(ts) == 0:
            ax2.set_xlabel(f"No walking classifier data found!")
            ax2.set_title(f"No data found.")
        else:
            ax2.set_xlabel(f"Walking classifier states querying raised {e}")
            ax2.set_title(f"Got exception: {e}")
        

    fig.autofmt_xdate()
    return fig






def plot_cooking(loc_id, start, end, base, **kwargs):
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
    #import pdb; pdb.set_trace()
    def _parse_cooking_coaching(rezlist: list):
        """Returns timestamps, coaching actions and feat_activity_cooking_weekly_average
        from input that should be a list of database items. 
        Rezlist = download_coaching_cooking(loc_id, start, end)"""
        timestamps = [item.get("Timestamp") for item in rezlist]
        coaching_actions = [item.get("CoachingAction") for item in rezlist]
        completions = [item.get("Completion") for item in rezlist]
        facwa = [item.get("Parameters").get("feat_activity_cooking_weekly_average") for item in rezlist]
        #completions = [item if item else np.nan for item in completions]
        def assign_color(label):
            if not label:
                return "k"
            elif label == 2:
                return "r"
            elif label == 1:
                return "tab:orange"
            elif label == 0:
                return "green"
            else:
                raise ValueError(f"Got a weird completion: {label}")
        colors = [assign_color(item) for item in completions]
        return pd.to_datetime(timestamps, unit="s"), coaching_actions, facwa, completions, colors

    def _parse_cooking_data(data_list: list):
        datetimes = pd.to_datetime([item.get("Data").get('Timestamp') for item in data_list], unit="ms")
        try:
            values = [item.get("Data").get('Measurements')[0].get("dP") for item in data_list]
        except:
            values = [item.get("Data").get('Measurements')[0] for item in data_list]
        return datetimes, values 

    extended_start = start - datetime.timedelta(days=1)
    extended_end = end + datetime.timedelta(days=1)
    ax.set_xlim((start, end))


    # Deal with sensor data
    cooking_data_dict = ac.download_cooking_data(loc_id, start, end, base)


    for feature, data in cooking_data_dict.items():
        datetimes, values = _parse_cooking_data(data)
        if not values:
            continue
        ax.scatter(datetimes, values, label=feature)
        

    # Deal with coachings:
    rezlist = ac.download_coaching_cooking(loc_id, start, end, base=base)
    ts, cs, facwas, completions, colors = _parse_cooking_coaching(rezlist)
    del rezlist

    ax2 = ax.twinx()
    ax2.step(ts, facwas, label="cooking\nweekly average")
    
    
    for x, y, s, c, completion in zip(ts, facwas, cs, colors, completions):
        s = s.replace("_", " ")
        if s.startswith("negative"):
            s = "negative msg"
        if s.startswith("positive"):
            s = "positive msg"
        if completion is not None:
            if completion == 2:
                s += " (declined)"
            elif completion == 1:
                s += " (can not)"
            elif completion == 0:
                s += " (done)"

        ax2.text(x, y, s, color=c, rotation=60, horizontalalignment="center", verticalalignment="center")

    # for x, y, s in zip(ts, facwas, completions):
    #     if not s:
    #         continue
    #     if s == 0:
    #         s = "Done"
    #     if s == 1:
    #         s = "Can not"
    #     if s == 2:
    #         s = "Declined"
    #     ax2.text(x, y, f"Completion: {s}", color="red", rotation=60, horizontalalignment="center", verticalalignment="bottom")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1+lines2, labels1+labels2, ncol=2)
    ax.set_ylabel("Energy (W)")
    ax2.set_ylabel("Cooking weekly average")
    ax.set_title(f"{loc_id}, cooking, {base} base")
    ax.set_xlabel("Datetime (UTC)")
    fig.autofmt_xdate()
    return fig

def plot_sleep_coaching(loc_id, start, end, base="prod"):
    fig, ax = plt.subplots(figsize = (10, 5))
    ax.set_title(f"Sleep coaching evaluation,\n{loc_id}, {base} database")

    datadict = ac.process_data(loc_id, start, end, base=base)
    eff_key = 'fuse_sleep_efficiency'
    coach_key = 'coach_sleep_quality'
    
    # Plot fuse_sleep_efficiency:
    timestamps = datadict[eff_key]["timestamps_ms"]
    measurements = datadict[eff_key]["values"]
    timestamps = pd.to_datetime(timestamps, unit="ms", utc=True)
    #breakpoint()
    assert len(timestamps) == len(measurements), "Timestamps and values have different length"
    ax.scatter(timestamps, measurements, label=eff_key)
    ax.plot(timestamps, measurements, label=eff_key)
    ax.set_ylabel(eff_key)
    #breakpoint()
    ax.set_ylim((ax.get_ylim()[0], ax.get_ylim()[1]*1.3))
    
    # Plot coachings:
    timestamps = datadict[coach_key]["timestamps_ms"]
    measurements = datadict[coach_key]["values"]
    timestamps = pd.to_datetime(timestamps, unit="ms", utc=True)
    #breakpoint()
    def assign_colour(s):
        if s == "no_action":
            return "k"
        if "doctor" in s:
            return "r"
        if "go_to_bed" in s:
            return "b"
        if "get_up" in s:
            return "g"
        else:
            return "orange"
    for t, c in zip(timestamps, measurements):
        try:
            ax.text(t, 1, c.replace("_", " "), rotation=45, color=assign_colour(c), va="top")
        except:
            pass
    
    fig.autofmt_xdate()
    #plt.tight_layout()
    return fig