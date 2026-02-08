#!/usr/bin/env python3
"""
Carma Smart Metering Historical Data Scraper
Navigates through previous months to collect all historical consumption data
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import re
import os
from dotenv import load_dotenv
import sqlite3
from contextlib import closing
import time
import argparse


class CarmaHistoricalScraper:
    def __init__(self, username, password, db_path='power_consumption.db'):
        self.username = username
        self.password = password
        self.db_path = db_path
        self.base_url = "http://www.carmasmartmetering.com/DirectConsumptionDev/"
        self.login_url = f"{self.base_url}login.aspx"
        self.graphing_url = f"{self.base_url}graphing.aspx"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Initialize database
        self.init_database()
        
        # Track processed months
        self.processed_months = set()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            
            # Create meter_readings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS meter_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reading_date DATE NOT NULL,
                    meter_value REAL NOT NULL,
                    unit TEXT DEFAULT 'kWh',
                    location TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(reading_date, location)
                )
            ''')
            
            # Create daily_consumption table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_consumption (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consumption_date DATE NOT NULL,
                    consumption_kwh REAL NOT NULL,
                    location TEXT,
                    month TEXT,
                    year INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(consumption_date, location)
                )
            ''')
            
            # Create consumption_summary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS consumption_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    total_consumption REAL,
                    average_daily REAL,
                    days_count INTEGER,
                    location TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(month, year, location)
                )
            ''')
            
            # Create scraping_history table to track what we've collected
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraping_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    location TEXT,
                    scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    records_count INTEGER,
                    UNIQUE(month, year, location)
                )
            ''')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_daily_consumption_date 
                ON daily_consumption(consumption_date)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_daily_consumption_month_year 
                ON daily_consumption(month, year)
            ''')
            
            conn.commit()
            print(f"✓ Database initialized at {self.db_path}")
    
    def get_asp_net_fields(self, html):
        """Extract ASP.NET form fields"""
        soup = BeautifulSoup(html, 'html.parser')
        fields = {}
        for field in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION', '__EVENTTARGET', '__EVENTARGUMENT']:
            element = soup.find('input', {'name': field})
            if element:
                fields[field] = element.get('value', '')
        return fields
    
    def login(self):
        """Login to the portal"""
        print("Logging in...")
        
        # Get login page
        response = self.session.get(self.login_url)
        asp_fields = self.get_asp_net_fields(response.text)
        
        # Submit login
        login_data = {
            **asp_fields,
            'username_txt': self.username,
            'password_txt': self.password,
            'login_btn': 'Login'
        }
        
        response = self.session.post(
            self.login_url,
            data=login_data,
            allow_redirects=True
        )
        
        if 'graphing.aspx' in response.url:
            print(f"✓ Login successful!")
            self.current_page_html = response.text
            
            # Check if we need to navigate to current month
            self.navigate_to_current_month()
            
            return True
        else:
            print("✗ Login failed")
            return False
    
    def navigate_to_current_month(self):
        """Navigate to the current month if Next Month button is available"""
        try:
            soup = BeautifulSoup(self.current_page_html, 'html.parser')
            
            # Check if Next Month button exists and is enabled
            next_month_btn = soup.find('input', {'name': 'nextMonth_btn'})
            
            if next_month_btn:
                # Check if button is disabled (some sites add disabled attribute)
                if not next_month_btn.get('disabled'):
                    print("  → Next Month button found, navigating to current month...")
                    
                    # Keep clicking next month until it's disabled or we reach current month
                    attempts = 0
                    max_attempts = 12  # Don't navigate more than 12 months forward
                    
                    while attempts < max_attempts:
                        # Check current displayed month
                        current_display = self.extract_current_month(self.current_page_html)
                        if current_display:
                            current_year = current_display[1]
                            current_month_name = current_display[0]
                            
                            # Check if we're at current actual month
                            from datetime import datetime
                            now = datetime.now()
                            months = ['January', 'February', 'March', 'April', 'May', 'June',
                                    'July', 'August', 'September', 'October', 'November', 'December']
                            
                            if current_year == now.year and current_month_name == months[now.month - 1]:
                                print(f"  ✓ Already at current month: {current_month_name} {current_year}")
                                break
                        
                        # Try to navigate forward
                        asp_fields = self.get_asp_net_fields(self.current_page_html)
                        postback_data = {
                            **asp_fields,
                            'nextMonth_btn': 'Next Month',
                            '__EVENTTARGET': '',
                            '__EVENTARGUMENT': ''
                        }
                        
                        response = self.session.post(
                            self.graphing_url,
                            data=postback_data,
                            headers={
                                'Referer': self.graphing_url,
                                'Content-Type': 'application/x-www-form-urlencoded'
                            }
                        )
                        
                        if response.status_code == 200:
                            self.current_page_html = response.text
                            
                            # Check if next button is now disabled
                            soup = BeautifulSoup(self.current_page_html, 'html.parser')
                            next_month_btn = soup.find('input', {'name': 'nextMonth_btn'})
                            
                            if not next_month_btn or next_month_btn.get('disabled'):
                                print(f"  ✓ Reached most recent month available")
                                break
                                
                            attempts += 1
                        else:
                            print(f"  ⚠️ Could not navigate forward")
                            break
                            
                    if attempts >= max_attempts:
                        print(f"  ⚠️ Stopped after {max_attempts} attempts")
                        
        except Exception as e:
            print(f"  ⚠️ Error navigating to current month: {e}")
    
    def navigate_to_previous_month(self, retry_on_500=True):
        """Click the 'Previous Month' button to navigate to earlier data"""
        try:
            # Get current page ASP.NET fields
            asp_fields = self.get_asp_net_fields(self.current_page_html)
            
            # The page has a prevMonth_btn button
            postback_data = {
                **asp_fields,
                'prevMonth_btn': 'Prev Month',
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': ''
            }
            
            print("  → Navigating to previous month...")
            response = self.session.post(
                self.graphing_url,
                data=postback_data,
                headers={
                    'Referer': self.graphing_url,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            if response.status_code == 200:
                self.current_page_html = response.text
                # Check if the month actually changed
                new_month = self.extract_current_month(response.text)
                if new_month:
                    return True
                else:
                    print("  ✗ Month didn't change")
                    return False
            elif response.status_code == 500:
                print(f"  ⚠️ Server error (500) - will retry after delay")
                if retry_on_500:
                    return 'retry_500'
                return False
            else:
                print(f"  ✗ Navigation failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ✗ Navigation error: {e}")
            return False
    
    def extract_current_month(self, html):
        """Extract the current month/year being displayed"""
        # Look for month/year in the title
        title_match = re.search(r"Daily Consumption During\s+(\w+)\s+(\d{4})", html)
        if title_match:
            month = title_match.group(1)
            year = int(title_match.group(2))
            return (month, year)
        return None
    
    def extract_consumption_data(self, html):
        """Extract consumption data from JavaScript in the page"""
        data = {
            'title': None,
            'subtitle': None,
            'location': None,
            'dates': [],
            'consumption': [],
            'average': None,
            'unit': 'kWh',
            'meter_reading': None,
            'reading_date': None,
            'month': None,
            'year': None
        }
        
        # Extract title and location
        title_match = re.search(r"text:\s*'([^']*Daily Consumption[^']*)'", html)
        if title_match:
            data['title'] = title_match.group(1)
            # Extract location from title
            location_match = re.search(r'for\s+(.+?)$', data['title'])
            if location_match:
                data['location'] = location_match.group(1).strip()
            # Extract month and year
            month_year_match = re.search(r'During\s+(\w+)\s+(\d{4})', data['title'])
            if month_year_match:
                data['month'] = month_year_match.group(1)
                data['year'] = int(month_year_match.group(2))
        
        # Extract subtitle with meter reading
        subtitle_match = re.search(r"subtitle:\s*{\s*text:\s*'([^']*)'", html)
        if subtitle_match:
            data['subtitle'] = subtitle_match.group(1)
            # Extract reading value and date
            reading_match = re.search(r'Reading as of (.+) is ([\d.]+)\s*kWh', data['subtitle'])
            if reading_match:
                data['reading_date'] = reading_match.group(1)
                data['meter_reading'] = float(reading_match.group(2))
        
        # Extract dates (categories)
        categories_match = re.search(r"categories:\s*\[(.*?)\]", html, re.DOTALL)
        if categories_match:
            dates_str = categories_match.group(1)
            dates = re.findall(r"'([^']*)'", dates_str)
            data['dates'] = [d for d in dates if d and '/' in d]
        
        # Extract consumption values
        consumption_match = re.search(r"name:\s*'Daily Consumption',\s*data:\s*\[(.*?)\]", html, re.DOTALL)
        if consumption_match:
            consumption_str = consumption_match.group(1)
            values = []
            
            # Find all numbers and objects
            items = consumption_str.split(',')
            for item in items:
                item = item.strip()
                if '{' in item:
                    # Object format {y: value, color: '#...'}
                    y_match = re.search(r'y:\s*([\d.]+)', item)
                    if y_match:
                        values.append(float(y_match.group(1)))
                else:
                    # Plain number
                    try:
                        values.append(float(item))
                    except:
                        pass
            
            data['consumption'] = values
            
            if values:
                data['total_consumption'] = sum(values)
                data['average_daily'] = sum(values) / len(values)
        
        return data
    
    def parse_date(self, date_str, year):
        """Parse date string like '01/Jan/2026' to datetime object"""
        try:
            # Parse the date string
            return datetime.strptime(f"{date_str}/{year}", '%d/%b/%Y/%Y')
        except:
            # Try alternative format if year is already in the date
            try:
                return datetime.strptime(date_str, '%d/%b/%Y')
            except:
                return None
    
    def save_to_database(self, data):
        """Save consumption data to SQLite database"""
        if not data['consumption']:
            return False
        
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            
            try:
                # Save meter reading if available
                if data['meter_reading'] and data['reading_date']:
                    try:
                        # Parse reading date
                        reading_dt = datetime.strptime(data['reading_date'], '%A, %d %B %Y')
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO meter_readings 
                            (reading_date, meter_value, unit, location)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            reading_dt.date(),
                            data['meter_reading'],
                            data['unit'],
                            data['location']
                        ))
                    except:
                        pass  # Skip if date parsing fails
                
                # Save daily consumption data
                saved_count = 0
                updated_count = 0
                for date_str, consumption in zip(data['dates'], data['consumption']):
                    date_obj = self.parse_date(date_str, data['year'])
                    if date_obj:
                        # Check if record exists and get current value
                        cursor.execute('''
                            SELECT id, consumption_kwh FROM daily_consumption 
                            WHERE consumption_date = ? AND location = ?
                        ''', (date_obj.date(), data['location']))
                        
                        existing = cursor.fetchone()
                        
                        if existing:
                            existing_id, existing_consumption = existing
                            
                            # Never update to 0, and only update if value has changed
                            if consumption > 0 and consumption != existing_consumption:
                                # Update existing record with new value
                                cursor.execute('''
                                    UPDATE daily_consumption 
                                    SET consumption_kwh = ?, month = ?, year = ?, 
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (
                                    consumption,
                                    data['month'],
                                    data['year'],
                                    existing_id
                                ))
                                updated_count += 1
                            # If new value is 0 and existing value is non-zero, keep existing
                            elif consumption == 0 and existing_consumption > 0:
                                # Skip update, keep existing non-zero value
                                pass
                        else:
                            # Only insert new record if consumption is not 0
                            if consumption > 0:
                                # Insert new record
                                cursor.execute('''
                                    INSERT INTO daily_consumption 
                                    (consumption_date, consumption_kwh, location, month, year)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (
                                    date_obj.date(),
                                    consumption,
                                    data['location'],
                                    data['month'],
                                    data['year']
                                ))
                                saved_count += 1
                
                # Save or update monthly summary
                cursor.execute('''
                    INSERT OR REPLACE INTO consumption_summary 
                    (month, year, total_consumption, average_daily, days_count, location, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    data['month'],
                    data['year'],
                    data['total_consumption'],
                    data['average_daily'],
                    len(data['consumption']),
                    data['location']
                ))
                
                # Record scraping history
                cursor.execute('''
                    INSERT OR REPLACE INTO scraping_history 
                    (month, year, location, records_count)
                    VALUES (?, ?, ?, ?)
                ''', (
                    data['month'],
                    data['year'],
                    data['location'],
                    len(data['consumption'])
                ))
                
                conn.commit()
                
                print(f"    ✓ {saved_count} new, {updated_count} updated records")
                
                return True
                
            except sqlite3.Error as e:
                print(f"    ✗ Database error: {e}")
                conn.rollback()
                return False
    
    def scrape_historical_data(self, months_back=12, stop_on_empty=True, pause_interval=6, pause_duration=30):
        """Scrape historical data going back specified number of months
        
        Args:
            months_back: Number of months to go back
            stop_on_empty: Stop if encountering empty months
            pause_interval: Pause every N months (default 6)
            pause_duration: How long to pause in seconds (default 30)
        """
        print("\n" + "="*60)
        print("STARTING HISTORICAL DATA COLLECTION")
        print("="*60 + "\n")
        
        if not self.login():
            return False
        
        months_collected = 0
        empty_months = 0
        max_empty_months = 3  # Stop after 3 consecutive empty months
        
        # Process current month first
        current_month_data = self.extract_current_month(self.current_page_html)
        if current_month_data:
            print(f"\n📅 Processing {current_month_data[0]} {current_month_data[1]}...")
            data = self.extract_consumption_data(self.current_page_html)
            
            if data['consumption']:
                print(f"  Found {len(data['consumption'])} days of data")
                print(f"  Total: {data.get('total_consumption', 0):.2f} kWh")
                self.save_to_database(data)
                self.processed_months.add(current_month_data)
                months_collected += 1
                empty_months = 0
            else:
                print("  No consumption data found")
                empty_months += 1
        
        # Navigate through previous months
        for month_num in range(1, months_back):
            if stop_on_empty and empty_months >= max_empty_months:
                print(f"\nStopped after {empty_months} consecutive empty months")
                break
            
            # Add longer delay every N months to let server catch up
            if pause_interval > 0 and month_num > 0 and month_num % pause_interval == 0:
                print(f"\n⏸️  Pausing for {pause_duration} seconds after {month_num} months to let server catch up...")
                for i in range(pause_duration, 0, -5):
                    print(f"    Resuming in {i} seconds...", end='\r')
                    time.sleep(min(5, i))
                print(" " * 50, end='\r')  # Clear the line
            else:
                # Regular delay between requests
                time.sleep(1)
            
            # Navigate to previous month
            nav_result = self.navigate_to_previous_month()
            
            if nav_result == 'retry_500':
                # Server error 500 - wait and retry
                print("  ⏳ Waiting 10 seconds before retrying due to server error...")
                time.sleep(10)
                
                # Try navigation again
                nav_result = self.navigate_to_previous_month(retry_on_500=False)
                if nav_result == True:
                    print("  ✓ Retry successful, continuing...")
                elif nav_result == False:
                    print("  ⚠️ Retry failed, skipping to next attempt...")
                    # Try one more navigation to skip this problematic month
                    time.sleep(5)
                    nav_result = self.navigate_to_previous_month(retry_on_500=False)
                    if not nav_result:
                        print(f"\nCould not navigate past server errors")
                        # Don't break - continue trying
                        continue
            elif not nav_result:
                print(f"\nCould not navigate further back")
                break
            
            # Extract month info
            month_data = self.extract_current_month(self.current_page_html)
            if not month_data:
                print(f"\nCould not determine current month")
                break
            
            # Skip if already processed
            if month_data in self.processed_months:
                print(f"\n📅 {month_data[0]} {month_data[1]} - Already processed, skipping...")
                continue
            
            print(f"\n📅 Processing {month_data[0]} {month_data[1]}...")
            
            # Extract and save data
            data = self.extract_consumption_data(self.current_page_html)
            
            if data['consumption']:
                print(f"  Found {len(data['consumption'])} days of data")
                print(f"  Total: {data.get('total_consumption', 0):.2f} kWh")
                self.save_to_database(data)
                self.processed_months.add(month_data)
                months_collected += 1
                empty_months = 0
            else:
                print("  No consumption data found")
                empty_months += 1
        
        # Summary
        print("\n" + "="*60)
        print("HISTORICAL DATA COLLECTION COMPLETE")
        print("="*60)
        print(f"\n✓ Collected data for {months_collected} months")
        
        # Show database summary
        self.show_database_summary()
        
        return True
    
    def show_database_summary(self):
        """Display summary of data in database"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            
            # Get total records
            cursor.execute('SELECT COUNT(*) FROM daily_consumption')
            total_records = cursor.fetchone()[0]
            
            # Get date range
            cursor.execute('''
                SELECT MIN(consumption_date), MAX(consumption_date) 
                FROM daily_consumption
            ''')
            date_range = cursor.fetchone()
            
            # Get monthly summaries
            cursor.execute('''
                SELECT month, year, total_consumption 
                FROM consumption_summary 
                ORDER BY year DESC, 
                    CASE month
                        WHEN 'January' THEN 1
                        WHEN 'February' THEN 2
                        WHEN 'March' THEN 3
                        WHEN 'April' THEN 4
                        WHEN 'May' THEN 5
                        WHEN 'June' THEN 6
                        WHEN 'July' THEN 7
                        WHEN 'August' THEN 8
                        WHEN 'September' THEN 9
                        WHEN 'October' THEN 10
                        WHEN 'November' THEN 11
                        WHEN 'December' THEN 12
                    END DESC
            ''')
            summaries = cursor.fetchall()
            
            print("\n📊 DATABASE SUMMARY")
            print("-" * 40)
            print(f"Total daily records: {total_records}")
            if date_range[0]:
                print(f"Date range: {date_range[0]} to {date_range[1]}")
            
            if summaries:
                print(f"\nMonths collected ({len(summaries)} total):")
                total_kwh = 0
                for month, year, total in summaries:
                    print(f"  • {month} {year}: {total:.2f} kWh")
                    total_kwh += total
                print(f"\nTotal consumption: {total_kwh:.2f} kWh")


def main():
    parser = argparse.ArgumentParser(description='Scrape historical power consumption data')
    parser.add_argument('--months', type=int, default=12, 
                        help='Number of months to go back (default: 12)')
    parser.add_argument('--db', default='power_consumption.db', 
                        help='Database path (default: power_consumption.db)')
    parser.add_argument('--no-stop', action='store_true',
                        help='Don\'t stop on empty months')
    parser.add_argument('--pause-interval', type=int, default=6,
                        help='Pause every N months (default: 6, set to 0 to disable)')
    parser.add_argument('--pause-duration', type=int, default=30,
                        help='Pause duration in seconds (default: 30)')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    
    if not username or not password:
        print("Error: Please set USERNAME and PASSWORD in .env file")
        return
    
    # Run historical scraper
    scraper = CarmaHistoricalScraper(username, password, args.db)
    scraper.scrape_historical_data(
        months_back=args.months,
        stop_on_empty=not args.no_stop,
        pause_interval=args.pause_interval,
        pause_duration=args.pause_duration
    )


if __name__ == "__main__":
    main()