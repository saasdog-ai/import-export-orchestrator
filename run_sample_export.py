#!/usr/bin/env python3
"""Script to create and run a sample export job."""

import asyncio
import json
from uuid import UUID, uuid4

import httpx


async def run_sample_export():
    """Create and run a sample export job."""
    # Generate a client ID (no need to create it in DB - clients managed in main SaaS app)
    client_id = uuid4()
    print(f"Using client ID: {client_id}")
    
    # Create export request
    export_request = {
        "entity": "bill",  # ExportEntity.BILL
        "fields": ["id", "amount", "date", "vendor.name"],
        "filters": {
            "operator": "and",
            "filters": [
                {
                    "field": "amount",
                    "operator": "gt",
                    "value": 1000
                },
                {
                    "field": "vendor.name",
                    "operator": "contains",
                    "value": "Acme"
                }
            ]
        },
        "sort": [
            {"field": "date", "direction": "desc"}
        ],
        "limit": 100,
        "offset": 0
    }
    
    print("\n📤 Creating export job...")
    print(f"Request: {json.dumps(export_request, indent=2)}")
    print(f"\nNote: client_id is extracted from JWT token (not in URL path)")
    print(f"Using client ID: {client_id} (from token)")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create export job
        # client_id is now extracted from JWT token, not from URL path
        url = "http://localhost:8000/exports"
        print(f"\nPOST {url}")
        print(f"Authorization: Bearer <token> (client_id: {client_id})")
        
        try:
            response = await client.post(url, json=export_request)
            
            print(f"\nResponse Status: {response.status_code}")
            
            if response.status_code == 201:
                result = response.json()
                run_id = result.get("run_id")
                status = result.get("status")
                
                print(f"\n✅ Export job created successfully!")
                print(f"   Run ID: {run_id}")
                print(f"   Status: {status}")
                print(f"   Entity: {result.get('entity')}")
                
                if result.get('error_message'):
                    print(f"   ⚠️  Error: {result.get('error_message')}")
                
                if result.get('result_metadata'):
                    print(f"\n📊 Result Metadata:")
                    print(json.dumps(result.get('result_metadata'), indent=2))
                
                # Wait a moment and check the result again
                print("\n⏳ Waiting 3 seconds for job to process...")
                await asyncio.sleep(3)
                
                # Get the export result
                result_url = f"http://localhost:8000/exports/{run_id}/result"
                print(f"\nGET {result_url}")
                result_response = await client.get(result_url)
                
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    print(f"\n📊 Final Export Result:")
                    print(f"   Status: {result_data.get('status')}")
                    if result_data.get('result_metadata'):
                        print(f"   Result Metadata:")
                        print(json.dumps(result_data.get('result_metadata'), indent=2))
                        
                        # Try to get download URL if available
                        if result_data.get('result_metadata', {}).get('remote_file_path'):
                            download_url_endpoint = f"http://localhost:8000/exports/{run_id}/download"
                            print(f"\n🔗 Getting download URL...")
                            download_response = await client.get(download_url_endpoint)
                            if download_response.status_code == 200:
                                download_data = download_response.json()
                                print(f"   Download URL: {download_data.get('download_url')}")
                            else:
                                print(f"   ⚠️  Could not get download URL: {download_response.status_code}")
                    if result_data.get('error_message'):
                        print(f"   ⚠️  Error: {result_data.get('error_message')}")
                else:
                    print(f"\n❌ Failed to get export result: {result_response.status_code}")
                    print(f"   {result_response.text}")
            else:
                print(f"\n❌ Failed to create export job")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except httpx.RequestError as e:
            print(f"\n❌ Request failed: {e}")
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(run_sample_export())

