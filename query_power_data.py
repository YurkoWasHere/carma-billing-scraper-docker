#!/usr/bin/env python3
"""
Query utility for power consumption database
"""

import sqlite3
from contextlib import closing
import sys
from datetime import datetime, timedelta
import argparse


def query_daily(db_path, start_date=None, end_date=None):
    """Query daily consumption data"""
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT consumption_date, consumption_kwh 
            FROM daily_consumption 
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += ' AND consumption_date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND consumption_date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY consumption_date'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if results:
            print(f"\nDaily Consumption ({len(results)} days):")
            print("-" * 40)
            total = 0
            for date, kwh in results:
                print(f"{date}: {kwh:.2f} kWh")
                total += kwh
            print("-" * 40)
            print(f"Total: {total:.2f} kWh")
            print(f"Average: {total/len(results):.2f} kWh/day")
        else:
            print("No data found for the specified period")


def query_summary(db_path):
    """Query monthly summaries"""
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT month, year, total_consumption, average_daily, days_count
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
        
        results = cursor.fetchall()
        
        if results:
            print("\nMonthly Summaries:")
            print("-" * 50)
            print(f"{'Month':<15} {'Total (kWh)':<12} {'Avg/Day':<10} Days")
            print("-" * 50)
            
            yearly_total = 0
            for month, year, total, avg, days in results:
                print(f"{month} {year:<4} {total:>10.2f}  {avg:>8.2f}  {days:>4}")
                yearly_total += total
            
            print("-" * 50)
            print(f"{'TOTAL':<15} {yearly_total:>10.2f}")
        else:
            print("No summary data found")


def query_highest_lowest(db_path, n=5):
    """Query highest and lowest consumption days"""
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()
        
        # Highest consumption days
        cursor.execute('''
            SELECT consumption_date, consumption_kwh 
            FROM daily_consumption 
            ORDER BY consumption_kwh DESC 
            LIMIT ?
        ''', (n,))
        
        highest = cursor.fetchall()
        
        # Lowest consumption days
        cursor.execute('''
            SELECT consumption_date, consumption_kwh 
            FROM daily_consumption 
            ORDER BY consumption_kwh ASC 
            LIMIT ?
        ''', (n,))
        
        lowest = cursor.fetchall()
        
        print(f"\nTop {n} Highest Consumption Days:")
        print("-" * 35)
        for date, kwh in highest:
            print(f"{date}: {kwh:.2f} kWh")
        
        print(f"\nTop {n} Lowest Consumption Days:")
        print("-" * 35)
        for date, kwh in lowest:
            print(f"{date}: {kwh:.2f} kWh")


def query_latest_reading(db_path):
    """Query latest meter reading"""
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT reading_date, meter_value, location 
            FROM meter_readings 
            ORDER BY reading_date DESC 
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        
        if result:
            print("\nLatest Meter Reading:")
            print("-" * 35)
            print(f"Date: {result[0]}")
            print(f"Reading: {result[1]:.2f} kWh")
            print(f"Location: {result[2]}")
        else:
            print("No meter readings found")


def main():
    parser = argparse.ArgumentParser(description='Query power consumption database')
    parser.add_argument('--db', default='power_consumption.db', help='Database path')
    parser.add_argument('--daily', action='store_true', help='Show daily consumption')
    parser.add_argument('--summary', action='store_true', help='Show monthly summaries')
    parser.add_argument('--extremes', action='store_true', help='Show highest/lowest days')
    parser.add_argument('--reading', action='store_true', help='Show latest meter reading')
    parser.add_argument('--start', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', help='End date (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='Show all reports')
    
    args = parser.parse_args()
    
    # If no specific query requested, show summary
    if not any([args.daily, args.summary, args.extremes, args.reading, args.all]):
        args.summary = True
    
    print("="*60)
    print("POWER CONSUMPTION DATABASE QUERY")
    print("="*60)
    
    if args.all or args.reading:
        query_latest_reading(args.db)
    
    if args.all or args.summary:
        query_summary(args.db)
    
    if args.all or args.extremes:
        query_highest_lowest(args.db)
    
    if args.all or args.daily:
        query_daily(args.db, args.start, args.end)
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()