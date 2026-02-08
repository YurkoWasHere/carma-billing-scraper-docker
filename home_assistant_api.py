#!/usr/bin/env python3
"""
Home Assistant Integration API for Carman Power Consumption Data
Provides REST API endpoints for Home Assistant to fetch power consumption data
"""

from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import sqlite3
from contextlib import closing
import os
from dotenv import load_dotenv
import threading
import time
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
DB_PATH = os.getenv('DB_PATH', 'power_consumption.db')
UPDATE_HOUR = int(os.getenv('UPDATE_HOUR', 5))  # Default: 5 AM
AUTO_UPDATE = os.getenv('AUTO_UPDATE', 'true').lower() == 'true'

# Load environment variables
load_dotenv()


def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)


def get_next_update_time():
    """Calculate next scheduled update time"""
    now = datetime.now()
    next_update = now.replace(hour=UPDATE_HOUR, minute=0, second=0, microsecond=0)
    if now >= next_update:
        next_update += timedelta(days=1)
    return next_update.strftime('%Y-%m-%d %H:%M:%S')


def update_data_from_scraper():
    """Run the scraper to update data"""
    try:
        logger.info("Running scraper to update data...")
        result = subprocess.run(
            ['python3', 'carman_scraper.py', '--months', '1'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("Data updated successfully")
        else:
            logger.error(f"Scraper failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Error updating data: {e}")


def auto_update_loop():
    """Background thread to update data once daily at specified hour"""
    while True:
        now = datetime.now()
        # Calculate next update time (5 AM)
        next_update = now.replace(hour=UPDATE_HOUR, minute=0, second=0, microsecond=0)
        
        # If we're past today's update time, schedule for tomorrow
        if now >= next_update:
            next_update += timedelta(days=1)
        
        # Calculate seconds until next update
        sleep_seconds = (next_update - now).total_seconds()
        
        logger.info(f"Next update scheduled for {next_update.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Sleeping for {sleep_seconds/3600:.1f} hours")
        
        # Sleep until update time
        time.sleep(sleep_seconds)
        
        # Run the update
        update_data_from_scraper()


@app.route('/api/status', methods=['GET'])
def status():
    """Check API status and database connection"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM daily_consumption')
            count = cursor.fetchone()[0]
            
            cursor.execute('SELECT MAX(consumption_date) FROM daily_consumption')
            latest_date = cursor.fetchone()[0]
            
        return jsonify({
            'status': 'ok',
            'records': count,
            'latest_date': latest_date,
            'database': DB_PATH,
            'auto_update': AUTO_UPDATE,
            'update_hour': f"{UPDATE_HOUR}:00 AM",
            'next_update': get_next_update_time()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/current', methods=['GET'])
def get_current_consumption():
    """Get today's and yesterday's consumption"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            
            # Get today's consumption
            today = datetime.now().date()
            cursor.execute('''
                SELECT consumption_kwh 
                FROM daily_consumption 
                WHERE consumption_date = ?
            ''', (today,))
            today_result = cursor.fetchone()
            
            # Get yesterday's consumption
            yesterday = today - timedelta(days=1)
            cursor.execute('''
                SELECT consumption_kwh 
                FROM daily_consumption 
                WHERE consumption_date = ?
            ''', (yesterday,))
            yesterday_result = cursor.fetchone()
            
            # Get current month total
            cursor.execute('''
                SELECT SUM(consumption_kwh) 
                FROM daily_consumption 
                WHERE strftime('%Y-%m', consumption_date) = strftime('%Y-%m', 'now')
            ''')
            month_total = cursor.fetchone()[0]
            
            # Get latest meter reading
            cursor.execute('''
                SELECT meter_value, reading_date 
                FROM meter_readings 
                ORDER BY reading_date DESC 
                LIMIT 1
            ''')
            meter_reading = cursor.fetchone()
            
        return jsonify({
            'today_kwh': today_result[0] if today_result else None,
            'yesterday_kwh': yesterday_result[0] if yesterday_result else None,
            'month_total_kwh': month_total or 0,
            'meter_reading': meter_reading[0] if meter_reading else None,
            'meter_reading_date': meter_reading[1] if meter_reading else None,
            'unit': 'kWh'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/daily/<date>', methods=['GET'])
def get_daily_consumption(date):
    """Get consumption for a specific date"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT consumption_kwh, month, year, location 
                FROM daily_consumption 
                WHERE consumption_date = ?
            ''', (date,))
            result = cursor.fetchone()
            
        if result:
            return jsonify({
                'date': date,
                'consumption_kwh': result[0],
                'month': result[1],
                'year': result[2],
                'location': result[3]
            })
        else:
            return jsonify({'error': 'No data for this date'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/monthly/<year>/<month>', methods=['GET'])
def get_monthly_consumption(year, month):
    """Get monthly consumption summary"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            
            # Get monthly summary
            cursor.execute('''
                SELECT total_consumption, average_daily, days_count, location 
                FROM consumption_summary 
                WHERE year = ? AND month = ?
            ''', (int(year), month))
            summary = cursor.fetchone()
            
            # Get daily details
            cursor.execute('''
                SELECT consumption_date, consumption_kwh 
                FROM daily_consumption 
                WHERE year = ? AND month = ?
                ORDER BY consumption_date
            ''', (int(year), month))
            daily_data = cursor.fetchall()
            
        if summary:
            return jsonify({
                'year': int(year),
                'month': month,
                'total_kwh': summary[0],
                'average_daily_kwh': summary[1],
                'days': summary[2],
                'location': summary[3],
                'daily': [
                    {'date': d[0], 'kwh': d[1]} for d in daily_data
                ]
            })
        else:
            return jsonify({'error': 'No data for this month'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/range', methods=['GET'])
def get_range_consumption():
    """Get consumption for a date range"""
    try:
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start and end dates required'}), 400
        
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT consumption_date, consumption_kwh 
                FROM daily_consumption 
                WHERE consumption_date BETWEEN ? AND ?
                ORDER BY consumption_date
            ''', (start_date, end_date))
            results = cursor.fetchall()
            
            # Calculate totals
            total = sum(r[1] for r in results)
            avg = total / len(results) if results else 0
            
        return jsonify({
            'start_date': start_date,
            'end_date': end_date,
            'total_kwh': total,
            'average_daily_kwh': avg,
            'days': len(results),
            'daily': [
                {'date': r[0], 'kwh': r[1]} for r in results
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get overall statistics"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            
            # Get overall stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_days,
                    SUM(consumption_kwh) as total_consumption,
                    AVG(consumption_kwh) as avg_daily,
                    MAX(consumption_kwh) as max_daily,
                    MIN(consumption_kwh) as min_daily,
                    MIN(consumption_date) as first_date,
                    MAX(consumption_date) as last_date
                FROM daily_consumption
            ''')
            stats = cursor.fetchone()
            
            # Get highest consumption day
            cursor.execute('''
                SELECT consumption_date, consumption_kwh 
                FROM daily_consumption 
                ORDER BY consumption_kwh DESC 
                LIMIT 1
            ''')
            highest_day = cursor.fetchone()
            
            # Get lowest consumption day
            cursor.execute('''
                SELECT consumption_date, consumption_kwh 
                FROM daily_consumption 
                ORDER BY consumption_kwh ASC 
                LIMIT 1
            ''')
            lowest_day = cursor.fetchone()
            
        return jsonify({
            'total_days': stats[0],
            'total_consumption_kwh': stats[1],
            'average_daily_kwh': stats[2],
            'max_daily_kwh': stats[3],
            'min_daily_kwh': stats[4],
            'date_range': {
                'first': stats[5],
                'last': stats[6]
            },
            'highest_day': {
                'date': highest_day[0],
                'kwh': highest_day[1]
            } if highest_day else None,
            'lowest_day': {
                'date': lowest_day[0],
                'kwh': lowest_day[1]
            } if lowest_day else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/update', methods=['POST'])
def trigger_update():
    """Manually trigger data update"""
    try:
        # Run update in background thread to avoid blocking
        thread = threading.Thread(target=update_data_from_scraper)
        thread.start()
        
        return jsonify({
            'status': 'update started',
            'message': 'Data update initiated in background'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Start auto-update thread if enabled
    if AUTO_UPDATE:
        logger.info(f"Starting auto-update thread (daily at {UPDATE_HOUR}:00 AM)")
        logger.info(f"Next update: {get_next_update_time()}")
        update_thread = threading.Thread(target=auto_update_loop, daemon=True)
        update_thread.start()
    
    # Start Flask app
    port = int(os.getenv('API_PORT', 5000))
    host = os.getenv('API_HOST', '0.0.0.0')
    
    logger.info(f"Starting API server on {host}:{port}")
    app.run(host=host, port=port, debug=False)