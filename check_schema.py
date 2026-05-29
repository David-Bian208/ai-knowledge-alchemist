#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/hot_pulse.db')
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(selected_items)")
columns = cursor.fetchall()
print("selected_items 表结构:")
for c in columns:
    print(f"  {c[1]} ({c[2]})")

cursor.execute("PRAGMA table_info(daily_reports)")
columns = cursor.fetchall()
print("\ndaily_reports 表结构:")
for c in columns:
    print(f"  {c[1]} ({c[2]})")

conn.close()
