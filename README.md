# damon

Data Monitor for [SAAM](https://saam2020.eu/) project.

This tool was created to visualize the data coming in during the SAAM project.

The credentials file has been removed for publishing, so in its current form the tools are not directly usable.

The project can be summed up with these main files:
```
app.py # Streamlit application
auth.py # Handles the user authentification
utils/
    acquire.py # Downloading, caching, preformatting
    plot.py # Plotting
```
When run, it allows the user to log in and chose functionality. Relevant data is downloaded from the SAAM database and cached where the `streamlit` app is running. 


# Features

The `streamlit` app can be run with 
```python
streamlit run app.py
```
The resulting browser window features the login window:
![picture of a browser window with a rudimentary login page](/images/login.png "Login Window")

After logging in the user can choose a few quick presets or input the start and end times and the datasources they want visualized.

![picture of possible choices after logging in](/images/spletna_detailed.png "User interface")

Possible choices are:
* Checking when datasources are available ![a plot showing when a certain type of data was available](/images/status_checker_1.png "Status checker") ![a plot showing when a certain type of data was available](/images/status_checker_2.png "Status checker")
* Sleep pipeline raw data and calculated features visualization ![a plot showing recorded magnitudes and found peaks and inferred state of sleeping](/images/sleep_1.png "Sleep pipeline visualization") ![a plot showing recorded magnitudes and found peaks and inferred state of sleeping](/images/bed_1.jpg "Sleep pipeline visualization")
* Raw magnitude from wearable MicroHub sensors visualization ![a plot showing recorded magnitudes from wearable sensors](/images/raw_magnitude.png "Raw MicroHub magnitudes")
* Power meter features ![a plot of detected events in PMC pipeline](/images/PMC_1.jpg "PMC events and cooking coachings")

The same plots can also be obtained with the funcitons in `utils` directory:
![picture showing code and the resulting plot](/images/scripting_status.png "Example code for plotting all relevant sensory features available for the location and timeframe")

For the `activity_cooking` a separate plot was prepared, showing only data, relevant for this pipeline and overlaying coaching data over it.
![](/images/scripting_PMC.png "Example for visualizing powermeter data.")

![](images/scripting_status.png )

# Contact

Maintainer: Peter Rupnik, peter.rupnik AT ijs.si . Drop me a line anytime.