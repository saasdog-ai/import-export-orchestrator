#!/usr/bin/env python3
"""Script to run exports against the AWS ECS service."""

import asyncio
import json
import os
import sys
from uuid import UUID

import httpx


async def run_export_aws(base_url: str | None = None):
    """Create and run a sample export job against AWS service."""
    
    # Get base URL from environment or use provided
    if not base_url:
        base_url = os.getenv("API_BASE_URL")
    
    if not base_url:
        print("❌ Error: API base URL not provided")
        print()
        print("Usage:")
        print("  python scripts/examples/run_export_aws.py <base_url>")
        print("  or")
        print("  API_BASE_URL=https://your-alb-dns-name.us-east-1.elb.amazonaws.com python scripts/examples/run_export_aws.py")
        print()
        print("To get the ALB DNS name, run:")
        print("  cd infra/aws/terraform")
        print("  terraform output alb_dns_name")
        print()
        print("Or if ALB is not enabled, you can use port forwarding:")
        print("  1. Get task IP from ECS console")
        print("  2. Use AWS Systems Manager Session Manager or port forwarding")
        sys.exit(1)
    
    # Ensure URL doesn't end with /
    base_url = base_url.rstrip("/")
    
    # Use default client ID (mock data is available for this client)
    default_client_id = UUID("00000000-0000-0000-0000-000000000000")
    client_id = default_client_id
    
    print(f"🌐 Connecting to: {base_url}")
    print(f"Using client ID: {client_id} (default - has mock data)")
    print()
    
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
    
    print("📤 Creating export job...")
    print(f"Request: {json.dumps(export_request, indent=2)}")
    print()
    
    async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for AWS
        # Create export job
        url = f"{base_url}/exports"
        print(f"POST {url}")
        
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
                print("\n⏳ Waiting 5 seconds for job to process...")
                await asyncio.sleep(5)
                
                # Get the export result
                result_url = f"{base_url}/exports/{run_id}/result"
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
                            download_url_endpoint = f"{base_url}/exports/{run_id}/download"
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
                
        except httpx.ConnectError as e:
            print(f"\n❌ Connection failed: {e}")
            print(f"   Make sure the service is running and accessible at {base_url}")
            print(f"   Check security groups and network configuration")
        except httpx.TimeoutException:
            print(f"\n❌ Request timed out")
            print(f"   The service might be slow or unavailable")
        except httpx.RequestError as e:
            print(f"\n❌ Request failed: {e}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(run_export_aws(base_url))

