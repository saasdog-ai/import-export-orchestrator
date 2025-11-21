#!/usr/bin/env python3
"""Quick script to check job status by run_id."""

import sys
import json
import httpx

if len(sys.argv) < 2:
    print("Usage: python3 check_job_status.py <run_id>")
    sys.exit(1)

run_id = sys.argv[1]

async def check_status():
    async with httpx.AsyncClient() as client:
        # Get export result
        url = f"http://localhost:8000/exports/{run_id}/result"
        response = await client.get(url)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Export Job Status:")
            print(f"   Run ID: {run_id}")
            print(f"   Status: {result.get('status')}")
            print(f"   Entity: {result.get('entity')}")
            if result.get('result_metadata'):
                print(f"   Result Metadata:")
                print(json.dumps(result.get('result_metadata'), indent=2))
            if result.get('error_message'):
                print(f"   Error: {result.get('error_message')}")
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_status())

