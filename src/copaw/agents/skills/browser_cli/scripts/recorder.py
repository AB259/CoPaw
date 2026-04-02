#!/usr/bin/env python3
"""浏览器操作录制器。

记录browser_use的操作序列，保存为JSON配置文件。

用法:
    python recorder.py --start --name login_github
    python recorder.py --record --name login_github --action '{"action":"open","params":{...}}'
    python recorder.py --stop --name login_github
    python recorder.py --list
    python recorder.py --status --name login_github
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加父目录到路径以导入copaw模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from copaw.constant import get_request_working_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_recordings_dir() -> Path:
    """获取录制存储目录。"""
    working_dir = get_request_working_dir()
    recordings_dir = working_dir / "browser_recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    return recordings_dir


def get_recording_path(name: str) -> Path:
    """获取指定录制的目录路径。"""
    return get_recordings_dir() / name


def start_recording(name: str) -> Dict[str, Any]:
    """开始新的录制会话。"""
    recording_path = get_recording_path(name)

    if recording_path.exists():
        logger.warning(f"Recording '{name}' already exists, will be overwritten")
        # 清空现有内容
        for file in recording_path.iterdir():
            file.unlink()

    recording_path.mkdir(parents=True, exist_ok=True)

    # 创建初始recording.json
    recording_data = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actions": [],
        "status": "recording",
        "total_steps": 0,
    }

    recording_file = recording_path / "recording.json"
    with open(recording_file, "w", encoding="utf-8") as f:
        json.dump(recording_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Started recording '{name}' at {recording_path}")

    return {
        "ok": True,
        "name": name,
        "path": str(recording_path),
        "message": f"Recording '{name}' started",
    }


def record_action(name: str, action_json: str) -> Dict[str, Any]:
    """记录单个browser_use操作。"""
    recording_path = get_recording_path(name)
    recording_file = recording_path / "recording.json"

    if not recording_file.exists():
        return {
            "ok": False,
            "error": f"Recording '{name}' not found. Start recording first.",
        }

    try:
        action_data = json.loads(action_json)
    except json.JSONDecodeError as e:
        return {
            "ok": False,
            "error": f"Invalid JSON: {e}",
        }

    # 加载现有录制
    with open(recording_file, "r", encoding="utf-8") as f:
        recording_data = json.load(f)

    # 添加新action
    step_num = recording_data["total_steps"] + 1
    action_entry = {
        "step": step_num,
        "action": action_data.get("action", ""),
        "params": action_data.get("params", {}),
    }

    # 可选：记录结果摘要
    if "result" in action_data:
        result = action_data["result"]
        if isinstance(result, dict):
            action_entry["result_summary"] = result.get("message", "OK")
            # 如果是snapshot，保存refs信息
            if action_data.get("action") == "snapshot" and "refs" in result:
                action_entry["refs_saved"] = True
                save_refs_mapping(name, result.get("refs", {}), step_num)

    recording_data["actions"].append(action_entry)
    recording_data["total_steps"] = step_num

    # 保存更新
    with open(recording_file, "w", encoding="utf-8") as f:
        json.dump(recording_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Recorded action #{step_num}: {action_data.get('action')}")

    return {
        "ok": True,
        "step": step_num,
        "action": action_data.get("action"),
        "message": f"Action #{step_num} recorded",
    }


def save_refs_mapping(name: str, refs: Dict[str, Any], step: int) -> None:
    """保存snapshot的refs映射。"""
    recording_path = get_recording_path(name)
    refs_file = recording_path / "refs_mapping.json"

    # 加载或创建refs映射
    if refs_file.exists():
        with open(refs_file, "r", encoding="utf-8") as f:
            refs_data = json.load(f)
    else:
        refs_data = {"mappings": {}}

    # 添加本次snapshot的refs
    refs_data["mappings"][f"step_{step}"] = refs

    with open(refs_file, "w", encoding="utf-8") as f:
        json.dump(refs_data, f, indent=2, ensure_ascii=False)


def stop_recording(name: str) -> Dict[str, Any]:
    """结束录制会话。"""
    recording_path = get_recording_path(name)
    recording_file = recording_path / "recording.json"

    if not recording_file.exists():
        return {
            "ok": False,
            "error": f"Recording '{name}' not found",
        }

    # 加载并更新状态
    with open(recording_file, "r", encoding="utf-8") as f:
        recording_data = json.load(f)

    recording_data["status"] = "completed"
    recording_data["completed_at"] = datetime.now(timezone.utc).isoformat()

    with open(recording_file, "w", encoding="utf-8") as f:
        json.dump(recording_data, f, indent=2, ensure_ascii=False)

    # 创建默认metadata.json模板
    metadata_file = recording_path / "metadata.json"
    if not metadata_file.exists():
        create_default_metadata(name, recording_data)

    logger.info(f"Recording '{name}' completed with {recording_data['total_steps']} steps")

    return {
        "ok": True,
        "name": name,
        "total_steps": recording_data["total_steps"],
        "path": str(recording_path),
        "message": f"Recording '{name}' completed",
    }


def create_default_metadata(name: str, recording_data: Dict[str, Any]) -> None:
    """创建默认的metadata.json模板。"""
    recording_path = get_recording_path(name)
    metadata_file = recording_path / "metadata.json"

    # 分析录制，提取潜在参数
    potential_params = extract_potential_params(recording_data)

    metadata = {
        "name": name,
        "description": f"浏览器操作脚本: {name}",
        "parameters": potential_params,
        "cli_command": name.replace("_", "-"),
    }

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(f"Created default metadata.json with {len(potential_params)} potential parameters")


def extract_potential_params(recording_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从录制中提取潜在参数（包含占位符的值）。"""
    params = []

    for action in recording_data.get("actions", []):
        params_dict = action.get("params", {})

        for key, value in params_dict.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                param_name = value[1:-1]
                # 避免重复添加
                if not any(p["name"] == param_name for p in params):
                    params.append({
                        "name": param_name,
                        "type": "string",
                        "required": True,
                        "description": f"参数: {param_name}",
                        "cli_flag": f"--{param_name}",
                        "cli_short": f"-{param_name[0]}",
                    })

    return params


def list_recordings() -> Dict[str, Any]:
    """列出所有录制。"""
    recordings_dir = get_recordings_dir()
    recordings = []

    if recordings_dir.exists():
        for path in recordings_dir.iterdir():
            if path.is_dir():
                recording_file = path / "recording.json"
                if recording_file.exists():
                    with open(recording_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    recordings.append({
                        "name": data.get("name", path.name),
                        "status": data.get("status", "unknown"),
                        "total_steps": data.get("total_steps", 0),
                        "created_at": data.get("created_at", ""),
                        "path": str(path),
                    })

    return {
        "ok": True,
        "recordings": recordings,
        "total": len(recordings),
    }


def get_recording_status(name: str) -> Dict[str, Any]:
    """获取录制状态。"""
    recording_path = get_recording_path(name)
    recording_file = recording_path / "recording.json"

    if not recording_file.exists():
        return {
            "ok": False,
            "error": f"Recording '{name}' not found",
        }

    with open(recording_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 检查metadata是否存在
    metadata_file = recording_path / "metadata.json"
    has_metadata = metadata_file.exists()

    return {
        "ok": True,
        "name": name,
        "status": data.get("status"),
        "total_steps": data.get("total_steps"),
        "created_at": data.get("created_at"),
        "completed_at": data.get("completed_at"),
        "has_metadata": has_metadata,
        "actions": data.get("actions", []),
        "path": str(recording_path),
    }


def delete_recording(name: str) -> Dict[str, Any]:
    """删除录制。"""
    recording_path = get_recording_path(name)

    if not recording_path.exists():
        return {
            "ok": False,
            "error": f"Recording '{name}' not found",
        }

    # 删除目录及其内容
    for file in recording_path.iterdir():
        file.unlink()
    recording_path.rmdir()

    logger.info(f"Deleted recording '{name}'")

    return {
        "ok": True,
        "name": name,
        "message": f"Recording '{name}' deleted",
    }


def main():
    parser = argparse.ArgumentParser(
        description="浏览器操作录制器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--start",
        action="store_true",
        help="开始新录制",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="记录操作",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="结束录制",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有录制",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="查看录制状态",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="删除录制",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="录制名称",
    )
    parser.add_argument(
        "--action",
        type=str,
        help="操作JSON（用于--record）",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="用户ID（多用户隔离）",
    )

    args = parser.parse_args()

    # 设置用户ID（如果提供）
    if args.user_id:
        import copaw.constant
        copaw.constant._request_user_id = args.user_id

    result: Dict[str, Any]

    if args.start:
        if not args.name:
            result = {"ok": False, "error": "--name is required for --start"}
        else:
            result = start_recording(args.name)

    elif args.record:
        if not args.name:
            result = {"ok": False, "error": "--name is required for --record"}
        elif not args.action:
            result = {"ok": False, "error": "--action is required for --record"}
        else:
            result = record_action(args.name, args.action)

    elif args.stop:
        if not args.name:
            result = {"ok": False, "error": "--name is required for --stop"}
        else:
            result = stop_recording(args.name)

    elif args.list:
        result = list_recordings()

    elif args.status:
        if not args.name:
            result = {"ok": False, "error": "--name is required for --status"}
        else:
            result = get_recording_status(args.name)

    elif args.delete:
        if not args.name:
            result = {"ok": False, "error": "--name is required for --delete"}
        else:
            result = delete_recording(args.name)

    else:
        result = {"ok": False, "error": "No action specified. Use --start, --record, --stop, --list, --status, or --delete"}

    # 输出结果
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not result.get("ok", False):
        sys.exit(1)


if __name__ == "__main__":
    main()