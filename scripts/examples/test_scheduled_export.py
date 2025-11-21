#!/usr/bin/env python3
"""Test script for scheduled exports.

This script:
1. Creates a scheduled export job that runs at the top of every hour
2. Monitors the job to see when it runs
3. Shows job run history

Usage:
    python test_scheduled_export.py
"""

import asyncio
import json
from datetime import datetime, timedelta
from uuid import UUID

import httpx

# Configuration
BASE_URL = "http://localhost:8000"
DEFAULT_CLIENT_ID = "00000000-0000-0000-0000-000000000000"  # Default when auth is disabled

# For testing, we can schedule it to run in the next minute instead of waiting for top of hour
# Cron format: "minute hour day month day_of_week"
# "0 * * * *" = top of every hour
# For testing: schedule it to run in 1-2 minutes from now
def get_test_cron_expression() -> str:
    """Get a cron expression that runs in the next 1-2 minutes for testing."""
    now = datetime.utcnow()
    next_minute = now + timedelta(minutes=1)
    # Run at the next minute (e.g., if it's 14:23, run at 14:24)
    minute = next_minute.minute
    return f"{minute} * * * *"  # Run at minute X of every hour

def get_top_of_hour_cron() -> str:
    """Get cron expression for top of every hour."""
    return "0 * * * *"  # Minute 0 of every hour

async def create_scheduled_export_job(use_test_schedule: bool = True) -> dict:
    """Create a scheduled export job."""
    headers = {"Content-Type": "application/json"}
    
    cron_expression = get_test_cron_expression() if use_test_schedule else get_top_of_hour_cron()
    
    job_data = {
        "client_id": DEFAULT_CLIENT_ID,
        "name": f"Scheduled Export Test - {datetime.utcnow().isoformat()}",
        "job_type": "export",
        "export_config": {
            "entity": "bill",
            "fields": ["id", "amount", "date", "description"],
            "limit": 100,
        },
        "cron_schedule": cron_expression,
        "enabled": True,
    }
    
    print(f"📅 Creating scheduled export job...")
    print(f"   Cron schedule: {cron_expression}")
    print(f"   {'(Test: runs in ~1 minute)' if use_test_schedule else '(Runs at top of every hour)'}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{BASE_URL}/jobs", json=job_data, headers=headers)
        
        if response.status_code == 201:
            job = response.json()
            print(f"✅ Job created successfully!")
            print(f"   Job ID: {job['id']}")
            print(f"   Name: {job['name']}")
            print(f"   Cron: {job.get('cron_schedule', 'N/A')}")
            print(f"   Enabled: {job.get('enabled', False)}")
            return job
        else:
            print(f"❌ Failed to create job: {response.status_code}")
            print(f"   Response: {response.text}")
            return {}

async def get_job(job_id: str) -> dict:
    """Get job details."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/jobs/{job_id}")
        if response.status_code == 200:
            return response.json()
        return {}

async def get_job_runs(job_id: str) -> list[dict]:
    """Get all runs for a job."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/jobs/{job_id}/runs")
        if response.status_code == 200:
            return response.json()
        return []

async def monitor_job(job_id: str, duration_minutes: int = 5):
    """Monitor a job for scheduled runs."""
    print(f"\n👀 Monitoring job {job_id} for {duration_minutes} minutes...")
    print("   (Press Ctrl+C to stop early)\n")
    
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(minutes=duration_minutes)
    last_run_count = 0
    
    try:
        while datetime.utcnow() < end_time:
            # Get current job runs
            runs = await get_job_runs(job_id)
            current_run_count = len(runs)
            
            # Show new runs
            if current_run_count > last_run_count:
                new_runs = runs[last_run_count:]
                for run in new_runs:
                    print(f"🔄 New job run detected!")
                    print(f"   Run ID: {run['id']}")
                    print(f"   Status: {run['status']}")
                    print(f"   Started at: {run.get('started_at', 'N/A')}")
                    print(f"   Created at: {run.get('created_at', 'N/A')}")
                    
                    # Wait a bit and check status again
                    await asyncio.sleep(2)
                    updated_runs = await get_job_runs(job_id)
                    for updated_run in updated_runs:
                        if updated_run['id'] == run['id']:
                            print(f"   Updated Status: {updated_run['status']}")
                            if updated_run.get('completed_at'):
                                print(f"   Completed at: {updated_run['completed_at']}")
                            if updated_run.get('result_metadata'):
                                metadata = updated_run['result_metadata']
                                print(f"   Result: {json.dumps(metadata, indent=6)}")
                            break
                    print()
                
                last_run_count = current_run_count
            
            # Show status every 30 seconds
            await asyncio.sleep(30)
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            print(f"⏱️  Monitoring... ({int(elapsed)}s elapsed, {current_run_count} runs so far)")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
    
    # Final summary
    final_runs = await get_job_runs(job_id)
    print(f"\n📊 Final Summary:")
    print(f"   Total runs: {len(final_runs)}")
    for i, run in enumerate(final_runs, 1):
        print(f"   Run {i}: {run['status']} - Created: {run.get('created_at', 'N/A')}")

async def main():
    """Main test function."""
    print("=" * 70)
    print("Scheduled Export Test")
    print("=" * 70)
    print()
    
    # Ask user if they want to test with immediate schedule or top of hour
    print("Schedule options:")
    print("  1. Test schedule (runs in ~1 minute) - Recommended for testing")
    print("  2. Top of hour (runs at minute 0 of every hour)")
    choice = input("\nChoose option (1 or 2, default=1): ").strip() or "1"
    
    use_test_schedule = choice == "1"
    
    # Create scheduled job
    job = await create_scheduled_export_job(use_test_schedule=use_test_schedule)
    
    if not job or 'id' not in job:
        print("❌ Failed to create job. Exiting.")
        return
    
    job_id = job['id']
    
    # Show initial state
    print(f"\n📋 Initial Job State:")
    initial_runs = await get_job_runs(job_id)
    print(f"   Runs: {len(initial_runs)}")
    
    # Monitor for scheduled runs
    if use_test_schedule:
        monitor_duration = 3  # Monitor for 3 minutes (should see run in ~1 minute)
    else:
        # For top of hour, calculate minutes until next hour
        now = datetime.utcnow()
        next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        minutes_until_next_hour = (next_hour - now).total_seconds() / 60
        monitor_duration = int(minutes_until_next_hour) + 2  # Monitor until next hour + 2 minutes buffer
        print(f"\n⏰ Next run scheduled for: {next_hour.isoformat()} UTC")
        print(f"   (Waiting {int(minutes_until_next_hour)} minutes)")
    
    await monitor_job(job_id, duration_minutes=monitor_duration)
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)
    print(f"\nTo check job runs later:")
    print(f"  curl {BASE_URL}/jobs/{job_id}/runs")
    print(f"\nTo view job details:")
    print(f"  curl {BASE_URL}/jobs/{job_id}")

if __name__ == "__main__":
    asyncio.run(main())

