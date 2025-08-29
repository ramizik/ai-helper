#!/usr/bin/env python3
"""
Test script to debug Google Calendar event fetching
Run this locally to test the logic before deploying to Lambda
"""

import os
import json
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

def test_current_event_logic():
    """Test the current event detection logic"""
    
    # Simulate the current time logic from the Lambda
    now = datetime.utcnow()
    current_time = now.isoformat() + 'Z'
    
    print(f"🔍 Testing Current Event Logic")
    print(f"Current UTC time: {current_time}")
    print(f"Current local time: {datetime.now()}")
    print("")
    
    # Test different time ranges
    test_scenarios = [
        {
            "name": "Current Moment (Original Logic - BROKEN)",
            "timeMin": current_time,
            "timeMax": current_time,
            "description": "Looking for events that start AND end at exact same moment"
        },
        {
            "name": "Current Moment (Fixed Logic)",
            "timeMin": (now - timedelta(minutes=5)).isoformat() + 'Z',
            "timeMax": (now + timedelta(minutes=5)).isoformat() + 'Z',
            "description": "Looking for events within 5 minutes of now"
        },
        {
            "name": "Current Hour",
            "timeMin": now.replace(minute=0, second=0, microsecond=0).isoformat() + 'Z',
            "timeMax": (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)).isoformat() + 'Z',
            "description": "Looking for events in the current hour"
        },
        {
            "name": "Next 30 Minutes",
            "timeMin": current_time,
            "timeMax": (now + timedelta(minutes=30)).isoformat() + 'Z',
            "description": "Looking for events starting in next 30 minutes"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"📊 {scenario['name']}")
        print(f"   Description: {scenario['description']}")
        print(f"   timeMin: {scenario['timeMin']}")
        print(f"   timeMax: {scenario['timeMax']}")
        print("")
    
    print("💡 The issue is likely that the original logic uses:")
    print("   timeMin=current_time and timeMax=current_time")
    print("   This means it's looking for events that start AND end at the exact same moment!")
    print("")
    print("✅ The fix should use a time window around the current moment")

def test_event_time_ranges():
    """Test different event time range scenarios"""
    
    now = datetime.utcnow()
    
    print(f"🕐 Event Time Range Scenarios")
    print(f"Current time: {now}")
    print("")
    
    # Scenario 1: Event happening right now
    event_start = now - timedelta(minutes=30)  # Started 30 minutes ago
    event_end = now + timedelta(minutes=30)    # Ends in 30 minutes
    
    print(f"📅 Scenario 1: Event happening right now")
    print(f"   Event start: {event_start}")
    print(f"   Event end: {event_end}")
    print(f"   Is happening now? {event_start <= now <= event_end}")
    print("")
    
    # Scenario 2: Event starting in 5 minutes
    event_start = now + timedelta(minutes=5)
    event_end = now + timedelta(minutes=65)
    
    print(f"📅 Scenario 2: Event starting soon")
    print(f"   Event start: {event_start}")
    print(f"   Event end: {event_end}")
    print(f"   Is happening now? {event_start <= now <= event_end}")
    print("")
    
    # Scenario 3: Event just ended
    event_start = now - timedelta(minutes=65)
    event_end = now - timedelta(minutes=5)
    
    print(f"📅 Scenario 3: Event just ended")
    print(f"   Event start: {event_start}")
    print(f"   Event end: {event_end}")
    print(f"   Is happening now? {event_start <= now <= event_end}")
    print("")

if __name__ == "__main__":
    print("🚀 Google Calendar Event Detection Debug Tool")
    print("=" * 50)
    print("")
    
    test_current_event_logic()
    print("-" * 50)
    test_event_time_ranges()
    
    print("🔧 To fix the Lambda function:")
    print("1. Change timeMin and timeMax to use a time window")
    print("2. Example: 5 minutes before and after current time")
    print("3. Or use the current hour as the window")
    print("")
    print("📝 The current logic will NEVER find events because:")
    print("   - It looks for events that start AND end at the exact same moment")
    print("   - Events have duration, so start ≠ end")
    print("   - This creates an impossible search condition")
