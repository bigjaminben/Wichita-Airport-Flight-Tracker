import os
import importlib.util

# Ensure matplotlib uses a non-GUI backend for headless initialization
os.environ['MPLBACKEND'] = 'Agg'

path = r"c:\Users\basmussen\Desktop\Flight Trackers\New folder\Airport Tracker.py"
spec = importlib.util.spec_from_file_location('airport_tracker', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

Tracker = mod.AirportFlightTrackerWithGraphs('flights_data.txt', 'weather_data.txt')
print('FLIGHTS_COUNT:', len(Tracker.flights_data))
print('WEATHER_COUNT:', len(Tracker.weather_data))
