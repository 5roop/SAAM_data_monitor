import os
import gc
import time
import json
import datetime
import pandas as pd
import numpy as np
from pymongo import MongoClient
import diskcache as dc
import logging
cache = dc.Cache("cache/")


def _download(
    loc_id: str, 
    source_id: str,
    start_date: datetime.datetime, 
    end_date: datetime.datetime = None,
    collection: str = "SensorDataPackages",
    base = "prod"):
    """Queries the database for given location id, source id and in given datarange. 
    Returns the response form server as string."""

    if not end_date:
        end_date = datetime.datetime.utcnow()
    assert start_date < end_date, "Start_date should be less than end_date."

    db = _get_db(base)
    collection = db[collection]

    results = collection.find(
        {
        "LocationId": loc_id,
        "SourceId": source_id,
        "Data.Timestamp": {
            "$gt": start_date.timestamp() * 1e3,
            "$lt": end_date.timestamp() * 1e3,
                          }
        })

    return list(results)

def download(loc_id: str, 
            source_id: str,
            start_date: datetime.datetime, 
            end_date: datetime.datetime = None,
            collection: str = "SensorDataPackages",
            base = "prod"):
    global cache
    key = f"{start_date}|{end_date}|{loc_id}|{source_id}|{collection}|{base}"
    # print(key)
    logging.info(f"Caching key: {key}")
    try:
        return cache[key]
    except KeyError:
        print("Not cached! Key: ", key, end="\r")
        logging.info("Not cached! Downlading key: "+key)
        cached = _download(loc_id,source_id,start_date,end_date,collection=collection,base=base)
        cache[key] = cached
        return cached



def magnitude_response_to_data(response_list):
    """Aggregates the database response into time(utc, ms), x, y, z components."""
    import numpy as np
    timestamps = []
    xs = []
    ys = []
    zs = []
    for item in response_list:
        timestamp = item["Data"]["Timestamp"]
        timestep = item["Data"]["Timestep"] * 1000 # ms
        num_entries = len(item["Data"]["Measurements"])
        current_timestamps = np.linspace(timestamp-timestep, timestamp, num_entries, dtype=int)
        for i in item["Data"]["Measurements"]:
            xs.append(i.get("x", np.nan))
            ys.append(i.get("y", np.nan))
            zs.append(i.get("z", np.nan))
        for t in current_timestamps:
            timestamps.append(t)
    # Let's sort the lists together:
    if timestamps:
        timestamps, xs, ys, zs = (list(t) for t in zip(*sorted(zip(timestamps, xs, ys, zs))))
    def transform_to_magnitudes(t,x,y,z):
        import numpy as np
        x = np.array([i if i else np.nan for i in x])
        y = np.array([i if i else np.nan for i in y])
        z = np.array([i if i else np.nan for i in z])
        try:
            return t, (x**2 + y**2 + z**2)**0.5
        except Exception as e:
            breakpoint()

    return transform_to_magnitudes(timestamps, xs, ys, zs)

def peak_handler(payload):
    """Helper function for peaks. Payload is output from download function"""
    assert payload != [], "No data to process."
    Ls = []
    Ss = []
    measurements = [item["Data"]["Measurements"] for item in payload if item["Data"]["Measurements"] != [[]]]
    for outer in measurements:
        for middle in outer:
            for inner in middle:
                if inner[1] == "L":
                    Ls.append(inner[0])
                if inner[1] == "S":
                    Ss.append(inner[0])
    return Ls, Ss
def state_handler(payload):
    """Helper function for peaks. Payload is output from download function"""
    assert payload != [], "No data to process."
    outs = []
    ins  = []
    sleeps = []
    measurements = [item["Data"]["Measurements"] for item in payload if item["Data"]["Measurements"] != [[]]]
    for outer in measurements:
        for middle in outer:
            for inner in middle:
                if inner[-1] == "out_of_bed":
                    outs.append((inner[0], inner[1]))
                if inner[-1] == "in_bed":
                    ins.append((inner[0], inner[1]))
                if inner[-1] == "sleeping":
                    sleeps.append((inner[0], inner[1]))
    return outs, ins, sleeps


def check_source_presence(
    loc_id: str, 
    source_id: str,
    start_date, #datetime.datetime object
    end_date, 
    base = "prod",
    freq = "1h"):
    """Creates a pandas.date_range, for each period in it
    it queryies given base and all sensor data collections 
    for {"$regex": source_id},
    returns timerange, is_data (= list of bool)."""


    assert start_date < end_date, "Start_date should be less than end_gate."
        
    db = _get_db(base)

    timerange = pd.date_range(
                    start = start_date,
                    end   = end_date,
                    freq  = freq)
    
    is_data = np.full(len(timerange), False, dtype=bool)

    for collection_name in db.list_collection_names():
        if "SensorDataPackages" not in collection_name:
            continue
        collection = db[collection_name]
        has_any = collection.find_one({
                    "LocationId": loc_id,
                    "SourceId": {"$regex": source_id},
                    "Data.Timestamp": {"$gt": start_date.timestamp()*1000,
                                       "$lt": end_date.timestamp()*1000
                                      }})
        if has_any == None:
            # print(f"Collection {collection_name} has no data")
            continue
       #  print(f"Checking collection {collection_name} for feature {source_id} for {loc_id}.")
       
        def _check(loc_id, source_id, s, e, collection_name, base):
            collection = db[collection_name]
            res = collection.find_one({
            "LocationId": loc_id,
            "SourceId": {"$regex": source_id},
            "Data.Timestamp": {"$gt": s.timestamp()*1000,
                               "$lt": e.timestamp()*1000
                              }})

            if res:
                return True
            else:
                return False
        for i, s, e in zip([i for i in range(len(timerange)-1)], timerange[0:-1], timerange[1:]):
            if _check(loc_id, source_id, s, e, collection_name, base):
                is_data[i] = is_data[i] or True
    gc.collect()
    return timerange, is_data[:-1]

# def check_source_presence_2(
#     loc_id: str, 
#     source_id: str,
#     start_date, #datetime.datetime object
#     end_date, 
#     base = "prod",
#     freq = "15min"):
#     """Creates a pandas.date_range, for each period in it
#     it queryies given base and all sensor data collections 
#     for {"$regex": source_id},
#     returns timerange, is_data (= list of bool)."""


#     assert start_date < end_date, "Start_date should be less than end_gate."

#     db = _get_db(base)


#     timerange = pd.date_range(
#                     start = start_date,
#                     end   = end_date,
#                     freq  = freq)
    
#     is_data = np.full(len(timerange)-1, False, dtype=bool)

#     for collection_name in db.collection_names():
#     # for collection_name in ["SensorDataPackages"]:
#         if "SensorDataPackages" not in collection_name:
#             continue
#         collection = db[collection_name]
#         has_any = collection.find_one({
#                     "LocationId": loc_id,
#                     "SourceId": {"$regex": source_id},
#                     "Data.Timestamp": {"$gt": start_date.timestamp()*1000,
#                                        "$lt": end_date.timestamp()*1000
#                                       }})
#         if not has_any:
#             print(f"Collection {collection_name} has no data")
#             continue
#         print(f"Checking collection {collection_name} for feature {source_id} for {loc_id}.")

#         def _find(s, e):
#             found =  collection.find_one({
#                                     "LocationId": loc_id,
#                                     "SourceId": {"$regex": source_id},
#                                     "Data.Timestamp": {"$gt": s.timestamp()*1000,
#                                                        "$lt": e.timestamp()*1000
#                               }})
#             return True if found else False
#         def check(ts):
#             ts = ts.copy()
#             N = len(ts)
#             if N == 2:
#                 return [_find(ts[0], ts[-1])]
#             else:
#                 if not _find(ts[0], ts[-1]):
#                     return [False] * (N - 1)
#                 else:
#                     return check(ts[0:N//2+1].copy()) + check(ts[N//2:].copy())
#         data = check(timerange) 
#         data = np.array(data, dtype=bool)
#         for i, item in enumerate(data):
#             is_data[i] |= item
        
#     gc.collect()
#     return timerange, is_data


def download_coaching_sleep(
    loc_id: str, 
    start_date: datetime.datetime, 
    end_date: datetime.datetime = None,
    collection: str = "CoachingActionEntries",
    base = "prod"):
    """Queries the database for given location id, source id and in given datarange. 
    Returns the response form server as string."""

    return _download_coaching(loc_id, start_date, end_date, collection=collection, base=base, pipeline_name="sleep_quality")

def download_coaching_cooking(
    loc_id: str, 
    start_date: datetime.datetime, 
    end_date: datetime.datetime = None,
    collection: str = "CoachingActionEntries",
    base = "prod"):
    """Queries the database for given location id, source id and in given datarange. 
    Returns the response form server as string."""
    return _download_coaching(loc_id, start_date, end_date, collection=collection, base=base, pipeline_name="activity_cooking")
def download_coaching_walking(
    loc_id: str, 
    start_date: datetime.datetime, 
    end_date: datetime.datetime = None,
    base = "prod"):
    """Queries the database for given location id, source id and in given datarange. 
    Returns the response form server as string."""
    if not end_date:
        end_date = datetime.datetime.utcnow()
    assert start_date < end_date, "Start_date should be less than end_date."

    db = _get_db(base)
    rez = db["CoachingAdditionalDataSources"].find({
    'SourceId': 'feat_mobility_activity',
    'LocationId': loc_id,
    "Data.Timestamp": {"$gt": start_date.timestamp() * 1e3, 
                        "$lt": end_date.timestamp() * 1e3},
                        })
    return list(rez)

@cache.memoize()
def _download_coaching(
    loc_id: str, 
    start_date: datetime.datetime, 
    end_date: datetime.datetime = None,
    collection: str = "CoachingActionEntries",
    base = "prod",
    pipeline_name = "sleep_quality"):
    """Queries the database for given location id, source id and in given datarange. 
    Returns the response form server as string."""

    if not end_date:
        end_date = datetime.datetime.utcnow()
    assert start_date < end_date, "Start_date should be less than end_date."

    db = _get_db(base)
    collection = db[collection]

    results = collection.find({
    "LocationId": loc_id,
    "PipelineName": pipeline_name,
    "Timestamp": {"$gt": start_date.timestamp(),
                       "$lt": end_date.timestamp()
                      }
                            })

    return list(results)



def download_additional_coaching(
        loc_id: str, 
        start_date: datetime.datetime, 
        end_date: datetime.datetime = None,
        collection: str = "CoachingAdditionalDataSources",
        base = "prod",
        regex = "sleep"):
        """Queries the database for given location id, source id and in given datarange. 
        Returns the response form server as string."""

        if not end_date:
            end_date = datetime.datetime.utcnow()
        assert start_date < end_date, "Start_date should be less than end_date."

        db = _get_db(base)
        collection = db[collection]

        results = collection.find({
        "LocationId": loc_id,
        "SourceId": {"$regex": regex},
        "Data.Timestamp": {"$gt": start_date.timestamp() * 1e3,
                           "$lt": end_date.timestamp() * 1e3
                          }
                                })

        return list(results)

def _get_db(base="prod"):
    from secrets import db_url
    client = MongoClient(db_url)
    db = client["saam"]
    return db

def download_cooking_data_original(loc_id, start, end, base,):
    """Downloads cooking sensor data in a dumb way, but
    runs 75% faster compared to the 'smart' solution.

    Returns dict with keys [oven, energy, microwave, stove] and
    values [rezult list from base across all collections]."""
    db = _get_db(base=base)

    res_dict = dict()
    target_features = ["oven", "energy", "microwave", "stove"]
    for target in target_features:
        results = list()
        for collection in db.collection_names():
            if "SensorData" not in collection:
                continue
            current_results = download(loc_id, {"$regex": target+"$"}, start, end, base=base, collection=collection)
            if current_results == []:
                continue
            results.extend(current_results)
        res_dict[target] = results
    return res_dict

def download_cooking_data(loc_id, start, end, base,):
    """Downloads cooking sensor data in a dumb way, but
    runs 75% faster compared to the 'smart' solution.

    Returns dict with keys [oven, energy, microwave, stove] and
    values [rezult list from base across all collections]."""
    db = _get_db(base=base)

    res_dict = dict()
    
    
    results = list()
    for collection in db.collection_names():
        if "SensorData" not in collection:
            continue
        current_results = download(loc_id, {"$regex": "_power_"}, start, end, base=base, collection=collection)
        if current_results == []:
            continue
        results.extend(current_results)
    target_features = ["oven", "energy", "microwave", "stove", "water_kettle"]
    #target_features = list(set(item["SourceId"] for item in results))
    #target_features = ["sens_power_f1_event_water_kettle"]
    for target in target_features:
        res_dict[target] = [item for item in results if target in item["SourceId"]]
    return res_dict

def process_data(loc_id, start, end, base="prod"):
    coachings = download_coaching_sleep(loc_id, 
                           start,
                           end,
                          )
    additional_coachings = download_additional_coaching(loc_id, 
                           start,
                           end,
                           collection = "CoachingAdditionalDataSources",
                           regex="sleep"
                                       )
    keys = list(coachings[0]["Parameters"].keys())
    datadict = dict()
    for key in keys:
        timestamps, measurements = [],[]
        for i in coachings:
            timestamps.append(i.get("Timestamp") * 1e3)
            measurements.append(i.get("Parameters").get(key))
        datadict[key] = {
            "timestamps_ms": timestamps,
            "values": measurements
        }
    
    additional_keys = [i["SourceId"] for i in additional_coachings]
    for key in additional_keys:
        if "sleep_state" in key:
            continue
        if key == 'app_sleep_diary_evening':
            continue
        subset = [i for i in additional_coachings if i["SourceId"] == key]
        timestamps = [i["Data"]["Timestamp"] for i in subset]
        measurements = [i["Data"]["Measurements"][0] for i in subset]
        
        datadict[key] = {
            "timestamps_ms": timestamps,
            "values": measurements
        }
    
    
    return datadict