#!/usr/bin/env python3
"""Script to test import functionality with CSV file.

Uses the /imports/execute endpoint with a local file path.
In production, the full flow is:
  1. POST /imports/request-upload -> presigned URL + file_key
  2. PUT file to presigned URL (direct to cloud storage)
  3. POST /imports/confirm-upload -> validate + get columns
  4. POST /imports/execute -> run the import
"""

import asyncio
import json
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"


async def test_import_from_csv():
    """Test importing bills from a CSV file."""
    print("=" * 70)
    print("TESTING IMPORT FUNCTIONALITY")
    print("=" * 70)
    print()

    # Path to sample CSV file
    project_root = Path(__file__).parent.parent.parent
    csv_file = project_root / "test-data" / "bills_create.csv"

    if not csv_file.exists():
        # Fallback to fixtures
        csv_file = project_root / "tests" / "fixtures" / "sample_bills.csv"

    if not csv_file.exists():
        print(f"CSV file not found: {csv_file}")
        print("   Please create the file first.")
        return

    print(f"CSV file: {csv_file}")
    print()

    import_request = {
        "file_path": str(csv_file),
        "entity": "bill",
    }

    print("Executing import...")
    print(f"Request: {json.dumps(import_request, indent=2)}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Execute import
            url = f"{BASE_URL}/imports/execute"
            print(f"POST {url}")
            response = await client.post(url, json=import_request)

            print(f"Response Status: {response.status_code}")

            if response.status_code != 201:
                print(f"Failed to execute import: {response.text}")
                return

            result = response.json()
            job_id = result["job_id"]
            run_id = result["run_id"]
            print(f"Import job created: job_id={job_id}, run_id={run_id}")

            # Poll for completion
            print("Waiting for job to complete...")
            await asyncio.sleep(3)

            status_url = f"{BASE_URL}/jobs/{job_id}/runs/{run_id}"
            status_response = await client.get(status_url)

            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"\nImport Result:")
                print(f"   Status: {status_data.get('status')}")
                if status_data.get("result_metadata"):
                    meta = status_data["result_metadata"]
                    print(f"   Records Created: {meta.get('imported_count', 0)}")
                    print(f"   Records Updated: {meta.get('updated_count', 0)}")
                    print(f"   Records Skipped: {meta.get('skipped_count', 0)}")
                    print(f"   Records Failed: {meta.get('failed_count', 0)}")
                    print(f"   Total Rows: {meta.get('total_rows', 0)}")

                if status_data.get("error_message"):
                    print(f"   Error: {status_data.get('error_message')}")

                # Verify by exporting
                print("\nVerifying import by exporting bills...")
                export_request = {
                    "entity": "bill",
                    "fields": [
                        {"field": "id"},
                        {"field": "external_id"},
                        {"field": "amount"},
                        {"field": "date"},
                    ],
                }
                export_response = await client.post(
                    f"{BASE_URL}/exports", json=export_request
                )
                if export_response.status_code == 201:
                    export_result = export_response.json()
                    export_run_id = export_result.get("run_id")
                    print(f"   Export job created: run_id={export_run_id}")
                    await asyncio.sleep(2)

                    export_status = await client.get(
                        f"{BASE_URL}/exports/{export_run_id}/result"
                    )
                    if export_status.status_code == 200:
                        export_data = export_status.json()
                        if export_data.get("result_metadata"):
                            count = export_data["result_metadata"].get("count", 0)
                            print(
                                f"   Found {count} bills in system (includes imported ones)"
                            )

        except httpx.RequestError as e:
            print(f"\nRequest failed: {e}")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_import_from_csv())
