#!/usr/bin/env python3
"""Test script for import validation with good and bad inputs."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx


async def test_import_validation():
    """Test import validation with various inputs."""
    print("=" * 80)
    print("TESTING IMPORT VALIDATION")
    print("=" * 80)
    print()

    base_url = "http://localhost:8000"
    default_client_id = "00000000-0000-0000-0000-000000000000"
    headers = {}  # No JWT for testing (uses default client_id)

    # Test files
    test_files = [
        {
            "name": "Valid CSV",
            "file": "tests/fixtures/bills_valid.csv",
            "expected": "validated",
        },
        {
            "name": "Invalid CSV (bad data)",
            "file": "tests/fixtures/bills_invalid.csv",
            "expected": "validation_failed",
        },
        {
            "name": "Missing Required Fields",
            "file": "tests/fixtures/bills_missing_fields.csv",
            "expected": "validation_failed",
        },
    ]

    async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
        for test_case in test_files:
            print(f"\n{'='*80}")
            print(f"TEST: {test_case['name']}")
            print(f"{'='*80}")
            
            # Go up to project root, then navigate to test file
            project_root = Path(__file__).parent.parent.parent
            file_path = project_root / test_case["file"]
            
            if not file_path.exists():
                print(f"❌ Test file not found: {file_path}")
                continue

            print(f"📄 File: {file_path.name}")
            print(f"📋 Path: {file_path}")
            print()

            # Copy file to Docker container
            import subprocess
            container_path = f"/tmp/{file_path.name}"
            try:
                result = subprocess.run(
                    ["docker", "cp", str(file_path.absolute()), f"job_runner_app:{container_path}"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(f"⚠️  Warning: Could not copy file to container: {result.stderr}")
                    print(f"   Using container path: {container_path}")
                else:
                    print(f"✅ File copied to container: {container_path}")
            except Exception as e:
                print(f"⚠️  Warning: Could not copy file: {e}")
                print(f"   Using container path: {container_path}")

            # Read file content for upload
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Upload and validate
            print(f"\n📤 Uploading and validating file...")
            print(f"POST {base_url}/imports/upload?entity=bill")
            
            try:
                files = {"file": (file_path.name, file_content, "text/csv")}
                response = await client.post(
                    f"{base_url}/imports/upload?entity=bill",
                    files=files,
                )

                print(f"\n📊 Response Status: {response.status_code}")
                result = response.json()
                
                if response.status_code == 200:
                    print(f"✅ Validation Status: {result.get('status')}")
                    print(f"   Message: {result.get('message')}")
                    print(f"   File Path: {result.get('file_path')}")
                    print(f"   Entity: {result.get('entity')}")
                    
                    if test_case["expected"] == "validated":
                        print(f"\n✅ TEST PASSED: Expected validation success, got success")
                        
                        # If validation passed, test import execution
                        if result.get("file_path"):
                            print(f"\n🚀 Testing import execution...")
                            execute_request = {
                                "file_path": result["file_path"],
                                "entity": "bill",
                            }
                            execute_response = await client.post(
                                f"{base_url}/imports/execute",
                                json=execute_request,
                            )
                            
                            if execute_response.status_code == 201:
                                execute_result = execute_response.json()
                                print(f"✅ Import job created:")
                                print(f"   Job ID: {execute_result.get('job_id')}")
                                print(f"   Run ID: {execute_result.get('run_id')}")
                                print(f"   Status: {execute_result.get('status')}")
                                
                                # Wait for job to complete
                                print(f"\n⏳ Waiting 3 seconds for import to complete...")
                                await asyncio.sleep(3)
                                
                                # Check job run status
                                run_id = execute_result.get("run_id")
                                job_id = execute_result.get("job_id")
                                status_response = await client.get(
                                    f"{base_url}/jobs/{job_id}/runs/{run_id}"
                                )
                                
                                if status_response.status_code == 200:
                                    status_data = status_response.json()
                                    print(f"\n📊 Import Result:")
                                    print(f"   Status: {status_data.get('status')}")
                                    if status_data.get("result_metadata"):
                                        meta = status_data["result_metadata"]
                                        print(f"   Created: {meta.get('imported_count', 0)}")
                                        print(f"   Updated: {meta.get('updated_count', 0)}")
                                        print(f"   Failed: {meta.get('failed_count', 0)}")
                                        
                                        if meta.get("import_errors"):
                                            print(f"\n⚠️  Import Errors:")
                                            for error in meta["import_errors"]:
                                                print(f"   Row {error.get('row')}, Field '{error.get('field', 'N/A')}': {error.get('message')}")
                            else:
                                print(f"❌ Failed to execute import: {execute_response.status_code}")
                                print(f"   {execute_response.text}")
                    else:
                        print(f"\n❌ TEST FAILED: Expected validation failure, got success")
                elif response.status_code == 400:
                    print(f"❌ Validation Status: {result.get('status')}")
                    print(f"   Message: {result.get('message')}")
                    
                    validation_errors = result.get("validation_errors", [])
                    error_count = result.get("error_count", len(validation_errors))
                    
                    print(f"\n📋 Validation Errors ({error_count} total):")
                    for i, error in enumerate(validation_errors, 1):
                        row_info = f"Row {error.get('row', 'N/A')}" if error.get('row') is not None else "File level"
                        field_info = f", Field '{error.get('field')}'" if error.get('field') else ""
                        print(f"   {i}. {row_info}{field_info}: {error.get('message')}")
                    
                    if test_case["expected"] == "validation_failed":
                        print(f"\n✅ TEST PASSED: Expected validation failure, got failure with {error_count} errors")
                    else:
                        print(f"\n❌ TEST FAILED: Expected validation success, got failure")
                else:
                    print(f"❌ Unexpected status code: {response.status_code}")
                    print(f"   Response: {json.dumps(result, indent=2)}")
                    
            except httpx.RequestError as e:
                print(f"\n❌ Request failed: {e}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()

    print(f"\n{'='*80}")
    print("TESTING COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_import_validation())

