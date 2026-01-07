"""
Fast minimal API - returns sample data instantly without slow imports
"""
from flask import Flask, jsonify, send_from_directory
import time
import os

app = Flask(__name__)

# Sample flight data for instant loading
SAMPLE_FLIGHTS = [
    {
        'flight_number': 'UA5261',
        'airline': 'United Airlines',
        'origin': 'ORD',
        'destination': 'ICT',
        'status': 'On Time',
        'scheduled': '10:30 AM',
        'estimated': '10:30 AM',
        'gate': 'A4',
        'aircraft': 'E175'
    },
    {
        'flight_number': 'WN3845',
        'airline': 'Southwest',
        'origin': 'DEN',
        'destination': 'ICT',
        'status': 'Delayed',
        'scheduled': '11:15 AM',
        'estimated': '11:45 AM',
        'gate': 'B2',
        'aircraft': 'B737'
    },
    {
        'flight_number': 'AA2156',
        'airline': 'American Airlines',
        'origin': 'DFW',
        'destination': 'ICT',
        'status': 'On Time',
        'scheduled': '2:20 PM',
        'estimated': '2:20 PM',
        'gate': 'C1',
        'aircraft': 'A320'
    }
]

SAMPLE_WEATHER = {
    'ICT': {'temp': 45, 'conditions': 'Clear', 'wind': '10 mph NW'},
    'ORD': {'temp': 38, 'conditions': 'Cloudy', 'wind': '15 mph N'},
    'DEN': {'temp': 52, 'conditions': 'Sunny', 'wind': '5 mph W'}
}

@app.route('/')
def index():
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, 'index.html')

@app.route('/api/flights')
@app.route('/api/flights/all')
def api_flights():
    return jsonify({
        'flights': SAMPLE_FLIGHTS,
        'count': len(SAMPLE_FLIGHTS),
        'timestamp': time.time()
    })

@app.route('/api/weather')
def api_weather():
    return jsonify({
        'weather': SAMPLE_WEATHER,
        'timestamp': time.time()
    })

@app.route('/api/flights/history')
def api_history():
    return jsonify({
        'arrivals': SAMPLE_FLIGHTS[:2],
        'departures': SAMPLE_FLIGHTS[1:],
        'stats': {'total': 3, 'on_time': 2, 'delayed': 1}
    })

@app.route('/api/operations/today')
def api_operations():
    return jsonify({
        'operations': [],
        'count': 0
    })

@app.route('/api/predictions/all')
def api_predictions():
    return jsonify({
        'predictions': []
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, filename)

if __name__ == '__main__':
    print("Starting fast minimal server on http://127.0.0.1:5001")
    app.run(host='127.0.0.1', port=5001, debug=False)
