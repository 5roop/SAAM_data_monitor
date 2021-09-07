import os
import numpy as np
import pandas as pd
import streamlit as st
import datetime
import gc

from utils import plot
from utils.acquire import download_coaching_sleep
from utils import all_loc_ids
from utils import all_plot_types

from auth import hashes, pass_to_hash

import logging
logging.basicConfig(
    filename='./app.log',
    # encoding='utf-8',
    level=logging.DEBUG,
    # format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%m'
                    )
logging.Logger.propagate = True



def detail_functions():
    plot_type = st.selectbox("Type of plot:", all_plot_types)
    col1, col2, col3 = st.beta_columns(3)
    today = datetime.datetime.now().date()
    with col1:
        loc_id = st.selectbox("Location ID:", all_loc_ids)
        base = st.radio(
        'Database:', ('prod', "dev"))
    with col2:
        start_date = st.date_input('Start date:', today - datetime.timedelta(days=1))
        start_time = st.time_input('time (UTC):', datetime.time(12), key='start_time')
        start_date = datetime.datetime(
            start_date.year,
            start_date.month,
            start_date.day,
            start_time.hour,
            start_time.minute,
            start_time.second)
    with col3:
        end_date = st.date_input('End date:', today)
        suggested_end_time = datetime.datetime(
            today.year,
            today.month,
            today.day,
            datetime.datetime.utcnow().hour)
        end_time = st.time_input('time (UTC):', suggested_end_time.time(), key='end_time')
        end_date = datetime.datetime(
            end_date.year,
            end_date.month,
            end_date.day,
            end_time.hour,
            #end_time.minute,
            #end_time.second
            )
    freq = None
    clips = False
    if plot_type == 'check data presence':
        freq = st.selectbox("Choose how long time intervals shoud be:", 
            ["5min", "15min", "2h", "3h", "6h", "1d"], index=2)
        clips = True
    plot_button = st.button('Plot!')
    if plot_button:
        element = st.text('Coming up!')
        p = plot.make_figure(loc_id, start_date, end_date, base, plot_type, freq=freq, clip=True)
        element.empty()
        st.pyplot(p)
    else:
        pass

def plot_week():
    today = datetime.datetime.now().date()
    today = datetime.datetime(
        today.year, today.month, today.day, 12)
    c1, c2, c3 = st.beta_columns(3)
    with c1:
        loc_id = st.selectbox("Location ID:", all_loc_ids)
    with c2:
        base = st.radio('Database:', ('prod', "dev"))
    start_date = today - datetime.timedelta(6)
    timerange = [start_date + datetime.timedelta(i) for i in range(7)]
    with c3:
        plot_button = st.button('Plot!')
    if plot_button:
        element = st.text('Coming up!')
        for start_date, end_date in zip(timerange[0:-1], timerange[1:]):
            p = plot.make_figure(loc_id, start_date, end_date, base, 'plot bed sensor data')
            element.empty()
            st.pyplot(p)
            try:
                coachings = download_coaching_sleep(loc_id, start_date, end_date)
                if coachings:
                    datetimes = [datetime.datetime.fromtimestamp(item["Timestamp"]) for item in coachings]
                    coaching_actions = [item['CoachingAction'] for item in coachings]
                    for d, t in zip(datetimes, coaching_actions):
                        st.write(f"""Coaching action for {d.strftime('%Y-%m-%d at %H:%M')}: {t.replace("_", " ")}""")
                else:
                    st.write("No coaching found for this location and date.")
            except Exception as e:
                st.write(f"Coaching querying raised an exception: {e}")
            del p
            gc.collect()
def data_presence():
    today = datetime.datetime.utcnow()
    suggested_end_time = datetime.datetime(
        today.year,
        today.month,
        today.day,
        datetime.datetime.utcnow().hour)
    start = suggested_end_time - datetime.timedelta(days=5)
    c1, c2, c3 = st.beta_columns(3)
    with c1:
        prefix = st.radio("Which locations would you like to visualize?", ('AT', "BG", "SI"))
    with c2:
        base = st.radio('Database:', ('prod', "dev"))
    loc_ids = [l for l in all_loc_ids if l.startswith(prefix)]
    with c3:
        plot_button = st.button('Plot!')
    if plot_button:
        element = st.text('Coming up!')
        for loc_id in loc_ids:
            p = plot.make_figure(loc_id, start, today, base, 'check data presence', freq="3h", clip=False)
            element.empty()
            st.pyplot(p)
            del p
            gc.collect()

def plot_day():
    today = datetime.datetime.utcnow()
    today = datetime.datetime(today.year, today.month, today.day, today.hour)
    start = today - datetime.timedelta(days=1)
    c1, c2, c3 = st.beta_columns(3)
    with c1:
        prefix = st.radio("Which locations would you like to visualize?", ('AT', "BG", "SI"))
    with c2:
        base = st.radio('Database:', ('prod', "dev"))
    loc_ids = [l for l in all_loc_ids if l.startswith(prefix)]
    with c3:
        plot_button = st.button('Plot!')
    if plot_button:
        element = st.text('Coming up!')
        for loc_id in loc_ids:
            p = plot.make_figure(loc_id, start, today, base, 'plot bed sensor data')
            element.empty()
            st.pyplot(p)
            del p
            try:
                coachings = download_coaching_sleep(loc_id, start, today + datetime.timedelta(days=1))
                if coachings:
                    datetimes = [datetime.datetime.fromtimestamp(item["Timestamp"]) for item in coachings]
                    coaching_actions = [item['CoachingAction'] for item in coachings]
                    for d, t in zip(datetimes, coaching_actions):
                        st.write(f"""Coaching action for {d.strftime('%Y-%m-%d at %H:%M')}: {t.replace("_", " ")}""")
                else:
                    st.write("No coaching found for this location and date.")
            except Exception as e:
                st.write(f"Coaching querying raised an exception: {e}")
            gc.collect()
def clear_cache():
    import diskcache as dc
    cache = dc.Cache("cache/")
    start_size = cache.count
    for key in cache.iterkeys():
        try:
            del cache[key]
        except:
            pass
    st.write(f"Cleaned cache. Before: {start_size}, now {cache.count}")

st.title('SAAM Data Plotter')

c1, c2 = st.beta_columns(2)
with c1:
    user = c1.text_input("Username:", value="").casefold()
with c2:
    pswd = c2.text_input("Password:", value="", type="password")
logged_in = (user.casefold() in hashes.keys()) and (pass_to_hash(pswd) == hashes[user.casefold()])

if logged_in:
    logging.info(f"Successful login from user {user}")
#     st.info("""~~Until database collections are sorted out you might find it impossible to find
#         raw sensor data (clip, bed) from January.~~

# Archival data can now be seamlessly plotted with the data on the currently active collections, thanks 
#         for your patience. -Peter""")
    import diskcache as dc
    cache = dc.Cache("cache/")
    if user == 'peter':
        c1, c2, c3 = st.beta_columns(3)
        with c1:
            but = st.button("Clear cache")
            if but:
                clear_cache()
        with c2:
            st.write(f"Current cache size: ", cache.size)
        with c3:
            st.write(f"Currenct cache count: ", cache.count)
    c1, c2 = st.empty(), st.empty()
    logging.debug(f"Successful login for {user}.")
    c1, c2 = st.beta_columns(2)
    with c1:
        st.write("""Select functionality.

For checking what data is available in the database, choose 'data presence'.
Time range is fixed to last week and time interval is fixed to 3 hours.

For examining bed sensor data all locations in the last 24h, choose 'last day'.

For examining bed data for a specific location in the last week, choose 'last week'. 

Check 'detailed' to see what else is possible.""")
    with c2:
        mode = st.radio("Functionality:", ("detailed", "data presence","last day", "last week", ))
    if mode == "data presence":
        data_presence()
    elif mode == "detailed":
        detail_functions()
    elif mode == "last week":
        plot_week()
    elif mode == "last day":
        plot_day()

else:
    if (user != "") and (pswd != ""):
        st.markdown("Username and password do not match.")
        logging.info(f"Unsuccessful login attempt from username {user} ")
