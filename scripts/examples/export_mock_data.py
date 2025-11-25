#!/usr/bin/env python3
"""Script to export current mock data from the running service to JSON file."""

import asyncio
import json
from pathlib import Path

import httpx


async def export_mock_data():
    """Export all mock data by querying each entity type."""
    print("=" * 70)
    print("EXPORTING MOCK DATA FROM SERVICE")
    print("=" * 70)
    print()
    
    # Entities to export
    entities = ["bill", "invoice", "vendor", "project"]
    
    all_data = {}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for entity in entities:
            print(f"📤 Exporting {entity} data...")
            
            # Create export request to get all data for this entity
            export_request = {
                "entity": entity,
                "fields": ["*"],  # Get all fields
                "limit": 10000,  # Large limit to get all records
            }
            
            try:
                # Create export job
                response = await client.post(
                    "http://localhost:8000/exports",
                    json=export_request
                )
                
                if response.status_code == 201:
                    result = response.json()
                    run_id = result.get("run_id")
                    
                    # Wait for job to complete
                    await asyncio.sleep(2)
                    
                    # Get export result
                    result_response = await client.get(
                        f"http://localhost:8000/exports/{run_id}/result"
                    )
                    
                    if result_response.status_code == 200:
                        result_data = result_response.json()
                        
                        if result_data.get("status") == "succeeded":
                            # The result_metadata should contain the data
                            # But we need to parse the actual file or get the data differently
                            # For now, let's try to get the download URL and fetch the file
                            download_response = await client.get(
                                f"http://localhost:8000/exports/{run_id}/download"
                            )
                            
                            if download_response.status_code == 200:
                                download_data = download_response.json()
                                download_url = download_data.get("download_url")
                                
                                if download_url:
                                    # Try to fetch the file
                                    file_response = await client.get(download_url)
                                    if file_response.status_code == 200:
                                        # Parse CSV or JSON based on format
                                        content_type = file_response.headers.get("content-type", "")
                                        if "json" in content_type or download_url.endswith(".json"):
                                            data = file_response.json()
                                            if isinstance(data, list):
                                                all_data[entity] = data
                                                print(f"   ✅ Exported {len(data)} {entity} records")
                                            else:
                                                print(f"   ⚠️  Unexpected JSON format for {entity}")
                                        else:
                                            # CSV - would need to parse it
                                            print(f"   ⚠️  CSV format not yet supported for export")
                                    else:
                                        print(f"   ⚠️  Could not download file: {download_response.status_code}")
                                else:
                                    print(f"   ⚠️  No download URL available")
                            else:
                                print(f"   ⚠️  Could not get download URL: {download_response.status_code}")
                        else:
                            print(f"   ⚠️  Export failed: {result_data.get('error_message')}")
                    else:
                        print(f"   ⚠️  Could not get export result: {result_response.status_code}")
                else:
                    print(f"   ⚠️  Failed to create export: {response.status_code}")
                    print(f"   {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Error exporting {entity}: {e}")
    
    # Save to file
    if all_data:
        output_file = Path(__file__).parent.parent.parent / "mock_data.json"
        print()
        print(f"💾 Saving data to {output_file}...")
        
        with open(output_file, "w") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Data saved to {output_file}")
        print()
        print("📊 Summary:")
        for entity, records in all_data.items():
            print(f"   {entity}: {len(records)} records")
    else:
        print()
        print("⚠️  No data was exported")


if __name__ == "__main__":
    asyncio.run(export_mock_data())

