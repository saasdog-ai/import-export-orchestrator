#!/usr/bin/env python3
"""Test script for import validation with good and bad inputs.

Uses the /imports/preview endpoint to validate files without executing.
In production, validation also happens during /imports/confirm-upload.
"""

import asyncio
import json
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"


async def test_import_validation():
    """Test import validation with various inputs."""
    print("=" * 80)
    print("TESTING IMPORT VALIDATION")
    print("=" * 80)
    print()

    # Test files
    test_files = [
        {
            "name": "Valid CSV",
            "file": "tests/fixtures/bills_valid.csv",
            "expected": "valid",
        },
        {
            "name": "Invalid CSV (bad data)",
            "file": "tests/fixtures/bills_invalid.csv",
            "expected": "invalid",
        },
        {
            "name": "Missing Required Fields",
            "file": "tests/fixtures/bills_missing_fields.csv",
            "expected": "invalid",
        },
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        for test_case in test_files:
            print(f"\n{'=' * 80}")
            print(f"TEST: {test_case['name']}")
            print(f"{'=' * 80}")

            project_root = Path(__file__).parent.parent.parent
            file_path = project_root / test_case["file"]

            if not file_path.exists():
                print(f"Test file not found: {file_path}")
                continue

            print(f"File: {file_path.name}")
            print(f"Path: {file_path}")
            print()

            # Use preview endpoint to validate without executing
            preview_request = {
                "file_path": str(file_path),
                "entity": "bill",
            }

            print("Validating file via preview...")
            print(f"POST {BASE_URL}/imports/preview")

            try:
                response = await client.post(
                    f"{BASE_URL}/imports/preview",
                    json=preview_request,
                )

                print(f"\nResponse Status: {response.status_code}")
                result = response.json()

                if response.status_code == 200:
                    total = result.get("total_records", 0)
                    valid = result.get("valid_count", 0)
                    invalid = result.get("invalid_count", 0)

                    print(f"Total Records: {total}")
                    print(f"Valid: {valid}")
                    print(f"Invalid: {invalid}")

                    if invalid > 0:
                        print(f"\nValidation Errors:")
                        for record in result.get("records", []):
                            if not record.get("is_valid"):
                                row = record.get("row", "?")
                                for error in record.get("errors", []):
                                    field = error.get("field", "N/A")
                                    msg = error.get("message", "Unknown error")
                                    print(f"   Row {row}, Field '{field}': {msg}")

                    if test_case["expected"] == "valid" and invalid == 0:
                        print(f"\nTEST PASSED: Expected valid, got valid")

                        # If validation passed, test import execution
                        print("\nTesting import execution...")
                        execute_request = {
                            "file_path": str(file_path),
                            "entity": "bill",
                        }
                        execute_response = await client.post(
                            f"{BASE_URL}/imports/execute",
                            json=execute_request,
                        )

                        if execute_response.status_code == 201:
                            execute_result = execute_response.json()
                            print(f"Import job created:")
                            print(f"   Job ID: {execute_result.get('job_id')}")
                            print(f"   Run ID: {execute_result.get('run_id')}")

                            print("Waiting for import to complete...")
                            await asyncio.sleep(3)

                            run_id = execute_result.get("run_id")
                            job_id = execute_result.get("job_id")
                            status_response = await client.get(
                                f"{BASE_URL}/jobs/{job_id}/runs/{run_id}"
                            )

                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                print(f"\nImport Result:")
                                print(f"   Status: {status_data.get('status')}")
                                if status_data.get("result_metadata"):
                                    meta = status_data["result_metadata"]
                                    print(
                                        f"   Created: {meta.get('imported_count', 0)}"
                                    )
                                    print(f"   Updated: {meta.get('updated_count', 0)}")
                                    print(f"   Failed: {meta.get('failed_count', 0)}")
                        else:
                            print(
                                f"Failed to execute import: {execute_response.status_code}"
                            )
                            print(f"   {execute_response.text}")

                    elif test_case["expected"] == "invalid" and invalid > 0:
                        print(
                            f"\nTEST PASSED: Expected invalid, got {invalid} invalid records"
                        )
                    elif test_case["expected"] == "valid" and invalid > 0:
                        print(f"\nTEST FAILED: Expected valid, got {invalid} errors")
                    else:
                        print(f"\nTEST FAILED: Expected invalid, got all valid")

                elif response.status_code == 400:
                    print(f"Validation failed at file level: {result.get('detail')}")
                    if test_case["expected"] == "invalid":
                        print(f"\nTEST PASSED: Expected failure, got 400")
                    else:
                        print(f"\nTEST FAILED: Expected success, got 400")
                else:
                    print(f"Unexpected status code: {response.status_code}")
                    print(f"   Response: {json.dumps(result, indent=2)}")

            except httpx.RequestError as e:
                print(f"\nRequest failed: {e}")
            except Exception as e:
                print(f"\nError: {e}")
                import traceback

                traceback.print_exc()

    print(f"\n{'=' * 80}")
    print("TESTING COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(test_import_validation())
