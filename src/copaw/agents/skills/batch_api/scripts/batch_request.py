#!/usr/bin/env python3
"""Batch API Request Executor.

Executes multiple API requests based on input data file and configuration.
Supports progress tracking, error recovery, and result aggregation.

Usage:
    python batch_request.py --config config.json --input input.json --output results.json
    python batch_request.py --config config.json --input input.json --output results.json --resume
"""

import argparse
import asyncio
import csv
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration for batch requests."""
    base_url: str
    endpoint: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    request_body: Optional[Dict[str, Any]] = None
    url_params: Dict[str, str] = field(default_factory=dict)
    response_data_path: str = "$"
    id_field: str = "id"
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    concurrency: int = 1
    delay_between_requests: float = 0.0


@dataclass
class Progress:
    """Progress tracking state."""
    processed_ids: List[str] = field(default_factory=list)
    last_index: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "processed_ids": self.processed_ids,
            "last_index": self.last_index,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Progress":
        return cls(
            processed_ids=data.get("processed_ids", []),
            last_index=data.get("last_index", 0),
            timestamp=data.get("timestamp", ""),
        )


def load_config(config_path: Path) -> Config:
    """Load configuration from JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Config(**data)


def load_input(input_path: Path) -> List[Dict[str, Any]]:
    """Load input data from JSON or CSV file."""
    suffix = input_path.suffix.lower()

    if suffix == ".json":
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        raise ValueError("JSON input must be a list or contain a 'data' key")

    elif suffix == ".csv":
        items = []
        with open(input_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(dict(row))
        return items

    else:
        raise ValueError(f"Unsupported input format: {suffix}")


def substitute_template(template: str, data: Dict[str, Any]) -> str:
    """Substitute {field} placeholders with data values."""
    def replacer(match):
        field_name = match.group(1)
        value = data.get(field_name, "")
        return str(value)

    return re.sub(r"\{(\w+)\}", replacer, template)


def substitute_dict(template: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively substitute placeholders in dict."""
    result = {}
    for key, value in template.items():
        if isinstance(value, str):
            result[key] = substitute_template(value, data)
        elif isinstance(value, dict):
            result[key] = substitute_dict(value, data)
        elif isinstance(value, list):
            result[key] = [
                substitute_template(item, data) if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def extract_jsonpath(data: Any, path: str) -> Any:
    """Extract data using simple JSONPath ($ separated by dots)."""
    if path == "$":
        return data

    parts = path.lstrip("$.").split(".")
    result = data
    for part in parts:
        if not part:
            continue
        if isinstance(result, dict):
            result = result.get(part)
        elif isinstance(result, list) and part.isdigit():
            result = result[int(part)]
        else:
            return None
    return result


async def make_request(
    client: httpx.AsyncClient,
    config: Config,
    item: Dict[str, Any],
) -> Dict[str, Any]:
    """Make a single API request with retry logic."""
    # Build URL
    endpoint = substitute_template(config.endpoint, item)
    url = f"{config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    # Build headers
    headers = substitute_dict(config.headers, item) if config.headers else {}

    # Build URL params
    params = substitute_dict(config.url_params, item) if config.url_params else None

    # Build request body
    body = None
    if config.request_body and config.method in ("POST", "PUT", "PATCH"):
        body = substitute_dict(config.request_body, item)

    # Retry loop
    last_error = None
    for attempt in range(config.retry_count):
        try:
            response = await client.request(
                method=config.method,
                url=url,
                headers=headers,
                params=params,
                json=body,
                timeout=config.timeout,
            )
            response.raise_for_status()

            result_data = response.json()
            extracted = extract_jsonpath(result_data, config.response_data_path)

            return {
                "input": item,
                "output": extracted,
                "status": "success",
                "status_code": response.status_code,
            }

        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            if e.response.status_code < 500:
                break
        except httpx.RequestError as e:
            last_error = str(e)
        except json.JSONDecodeError:
            last_error = "Invalid JSON response"

        if attempt < config.retry_count - 1:
            await asyncio.sleep(config.retry_delay * (attempt + 1))

    return {
        "input": item,
        "error": last_error,
        "status": "failed",
    }


async def process_batch(
    config: Config,
    items: List[Dict[str, Any]],
    progress: Progress,
    output_path: Path,
    progress_path: Path,
    errors_path: Optional[Path],
    previous_results: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Process all items with progress tracking."""
    results = previous_results.get("results", []) if previous_results else []
    errors = previous_results.get("errors", []) if previous_results else []
    success_count = previous_results.get("success", 0) if previous_results else 0
    failed_count = previous_results.get("failed", 0) if previous_results else 0

    # Filter already processed items
    processed_set = set(progress.processed_ids)
    pending_items = [
        item for item in items
        if item.get(config.id_field) not in processed_set
    ]

    if not pending_items:
        logger.info("All items already processed")
        return {
            "status": "completed",
            "total": len(items),
            "success": success_count,
            "failed": failed_count,
            "message": "All items already processed",
        }

    logger.info(f"Processing {len(pending_items)} items (total: {len(items)}, already done: {len(processed_set)})")

    start_time = datetime.now(timezone.utc)

    async with httpx.AsyncClient() as client:
        semaphore = asyncio.Semaphore(min(config.concurrency, 10))

        async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                result = await make_request(client, config, item)

                if config.delay_between_requests > 0:
                    await asyncio.sleep(config.delay_between_requests)

                return result

        # Process in batches for progress updates
        batch_size = max(10, len(pending_items) // 10)

        for i in range(0, len(pending_items), batch_size):
            batch = pending_items[i:i + batch_size]
            batch_results = await asyncio.gather(*[process_item(item) for item in batch])

            for result in batch_results:
                results.append(result)
                item_id = result["input"].get(config.id_field, "")

                if result["status"] == "success":
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(result)
                    if errors_path:
                        with open(errors_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(result, ensure_ascii=False) + "\n")

                progress.processed_ids.append(item_id)

            progress.last_index = i + len(batch)
            progress.timestamp = datetime.now(timezone.utc).isoformat()

            # Save progress
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(progress.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info(f"Progress: {len(progress.processed_ids)}/{len(items)} ({success_count} success, {failed_count} failed)")

    end_time = datetime.now(timezone.utc)

    # Build final output
    output = {
        "status": "completed",
        "total": len(items),
        "success": success_count,
        "failed": failed_count,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": (end_time - start_time).total_seconds(),
        "results": results,
    }

    if errors:
        output["errors"] = errors

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Execute batch API requests with progress tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", "-c",
        required=True,
        help="Path to config JSON file",
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input JSON or CSV file",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Path to output results JSON file",
    )
    parser.add_argument(
        "--progress", "-p",
        help="Path to progress tracking file (default: output + .progress.json)",
    )
    parser.add_argument(
        "--errors", "-e",
        help="Path to errors JSONL file (default: output + .errors.jsonl)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous progress if available",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output and progress files",
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    input_path = Path(args.input)
    output_path = Path(args.output)
    progress_path = Path(args.progress) if args.progress else Path(f"{args.output}.progress.json")
    errors_path = Path(args.errors) if args.errors else Path(f"{args.output}.errors.jsonl")

    # Validate inputs
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Check existing files (skip if resuming)
    if output_path.exists() and not args.force and not args.resume:
        print(f"Error: Output file exists: {output_path}. Use --force to overwrite or --resume to continue.", file=sys.stderr)
        sys.exit(1)

    # Load config and input
    config = load_config(config_path)
    items = load_input(input_path)

    if not items:
        print("Error: No items to process", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(items)} items from {input_path}")
    print(f"Endpoint: {config.base_url}{config.endpoint}")
    print(f"Method: {config.method}")
    print(f"Concurrency: {config.concurrency}")

    # Load or initialize progress
    progress = Progress()
    if args.resume and progress_path.exists():
        with open(progress_path, "r", encoding="utf-8") as f:
            progress = Progress.from_dict(json.load(f))
        print(f"Resuming from progress: {len(progress.processed_ids)} items already processed")
    elif progress_path.exists() and not args.force:
        print(f"Progress file exists: {progress_path}. Use --resume to continue or --force to restart.")
        sys.exit(1)

    # Clear errors file if starting fresh
    if errors_path.exists() and (not args.resume or args.force):
        errors_path.unlink()

    # Load previous results if resuming
    previous_results = None
    if args.resume and output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                previous_results = json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass

    # Run batch processing
    try:
        result = asyncio.run(process_batch(
            config=config,
            items=items,
            progress=progress,
            output_path=output_path,
            progress_path=progress_path,
            errors_path=errors_path,
            previous_results=previous_results,
        ))

        # Save final results
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Clean up progress file on success
        if progress_path.exists():
            progress_path.unlink()

        print(f"\nCompleted: {result['success']}/{result['total']} successful")
        if result['failed'] > 0:
            print(f"Failed: {result['failed']}")
            print(f"Errors saved to: {errors_path}")
        print(f"Results saved to: {output_path}")

    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved to:", progress_path)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()