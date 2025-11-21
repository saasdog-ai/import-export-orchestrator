#!/usr/bin/env python3
"""Script to test import functionality with CSV file."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx


async def test_import_from_csv():
    """Test importing bills from a CSV file."""
    print("=" * 70)
    print("TESTING IMPORT FUNCTIONALITY")
    print("=" * 70)
    print()
    
    # Path to sample CSV file (go up to project root, then to tests/fixtures)
    project_root = Path(__file__).parent.parent.parent
    csv_file_host = project_root / "tests" / "fixtures" / "sample_bills.csv"
    
    # Check if file exists on host
    if not csv_file_host.exists():
        print(f"❌ CSV file not found: {csv_file_host}")
        print("   Please create the file first.")
        return
    
    print(f"📄 CSV file: {csv_file_host}")
    
    # Copy file to Docker container's /tmp directory (accessible from app)
    import subprocess
    print(f"📋 Copying file to Docker container...")
    try:
        result = subprocess.run(
            ["docker", "cp", str(csv_file_host.absolute()), "job_runner_app:/tmp/sample_bills.csv"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"   ⚠️  Warning: Could not copy file to container: {result.stderr}")
            print(f"   Will try using container path anyway...")
        else:
            print(f"   ✅ File copied to container")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not copy file: {e}")
    
    csv_file_container = "/tmp/sample_bills.csv"
    print(f"📄 Using container path: {csv_file_container}")
    print()
    
    # Generate a client ID (in real scenario, this comes from JWT token)
    # For testing without auth, we use the default dummy client_id
    default_client_id = "00000000-0000-0000-0000-000000000000"
    
    # Create import job configuration
    # Use container path since the app runs in Docker
    job_data = {
        "client_id": default_client_id,  # Must match authenticated client_id (default when no JWT)
        "name": "Import Bills from CSV",
        "job_type": "import",
        "import_config": {
            "source": "csv_file",
            "entity": "bill",
            "options": {
                "source_file": csv_file_container  # Use container path
            }
        },
        "enabled": True,
    }
    
    print("📤 Creating import job...")
    print(f"Request: {json.dumps(job_data, indent=2)}")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create import job
        url = "http://localhost:8000/jobs"
        print(f"POST {url}")
        
        try:
            response = await client.post(url, json=job_data)
            
            print(f"\nResponse Status: {response.status_code}")
            
            if response.status_code == 201:
                result = response.json()
                job_id = result.get("id")
                print(f"\n✅ Import job created successfully!")
                print(f"   Job ID: {job_id}")
                print(f"   Name: {result.get('name')}")
                
                # Trigger the job run
                print(f"\n🚀 Triggering job run...")
                run_url = f"http://localhost:8000/jobs/{job_id}/run"
                run_response = await client.post(run_url)
                
                if run_response.status_code == 201:
                    run_result = run_response.json()
                    run_id = run_result.get("id")
                    print(f"   Run ID: {run_id}")
                    print(f"   Status: {run_result.get('status')}")
                    
                    # Wait for job to complete
                    print(f"\n⏳ Waiting 3 seconds for job to process...")
                    await asyncio.sleep(3)
                    
                    # Check job run status
                    status_url = f"http://localhost:8000/jobs/{job_id}/runs/{run_id}"
                    status_response = await client.get(status_url)
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"\n📊 Import Job Result:")
                        print(f"   Status: {status_data.get('status')}")
                        if status_data.get('result_metadata'):
                            meta = status_data['result_metadata']
                            print(f"   Records Created: {meta.get('imported_count', 0)}")
                            print(f"   Records Updated: {meta.get('updated_count', 0)}")
                            print(f"   Records Failed: {meta.get('failed_count', 0)}")
                        
                        if status_data.get('error_message'):
                            print(f"   ⚠️  Error: {status_data.get('error_message')}")
                        
                        # Verify by exporting the bills
                        print(f"\n🔍 Verifying import by exporting bills...")
                        export_request = {
                            "entity": "bill",
                            "fields": ["id", "amount", "date", "description", "status"],
                            "limit": 100,
                        }
                        export_response = await client.post("http://localhost:8000/exports", json=export_request)
                        if export_response.status_code == 201:
                            export_result = export_response.json()
                            print(f"   Export job created: {export_result.get('run_id')}")
                            await asyncio.sleep(2)
                            # Get export result
                            export_status = await client.get(
                                f"http://localhost:8000/exports/{export_result.get('run_id')}/result"
                            )
                            if export_status.status_code == 200:
                                export_data = export_status.json()
                                if export_data.get('result_metadata'):
                                    count = export_data['result_metadata'].get('count', 0)
                                    print(f"   ✅ Found {count} bills in system (should include imported ones)")
                else:
                    print(f"\n❌ Failed to trigger job run: {run_response.status_code}")
                    print(f"   {run_response.text}")
            else:
                print(f"\n❌ Failed to create import job")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except httpx.RequestError as e:
            print(f"\n❌ Request failed: {e}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_import_from_csv())

