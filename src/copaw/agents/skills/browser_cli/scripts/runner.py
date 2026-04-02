#!/usr/bin/env python3
"""浏览器脚本执行器。

加载录制并执行browser_use操作序列。

用法:
    python runner.py --recording login_github
    python runner.py --recording login_github --param username=user --param password=pass
    python runner.py --recording login_github --headed
"""

import argparse
import asyncio
import json
import logging
import re
import sys
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
    return working_dir / "browser_recordings"


def load_recording(name: str) -> Dict[str, Any]:
    """加载录制数据。"""
    recording_path = get_recordings_dir() / name
    recording_file = recording_path / "recording.json"

    if not recording_file.exists():
        raise FileNotFoundError(f"Recording '{name}' not found at {recording_file}")

    with open(recording_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_refs_mapping(name: str) -> Dict[str, Any]:
    """加载refs映射。"""
    recording_path = get_recordings_dir() / name
    refs_file = recording_path / "refs_mapping.json"

    if refs_file.exists():
        with open(refs_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"mappings": {}}


def substitute_params(params: Dict[str, Any], param_values: Dict[str, str]) -> Dict[str, Any]:
    """替换参数占位符。"""
    result = {}

    for key, value in params.items():
        if isinstance(value, str):
            # 替换 {param} 占位符
            def replacer(match):
                param_name = match.group(1)
                return param_values.get(param_name, match.group(0))

            result[key] = re.sub(r"\{(\w+)\}", replacer, value)
        elif isinstance(value, dict):
            result[key] = substitute_params(value, param_values)
        elif isinstance(value, list):
            result[key] = [
                re.sub(r"\{(\w+)\}", lambda m: param_values.get(m.group(1), m.group(0)), item)
                if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


async def execute_browser_action(
    action: str,
    params: Dict[str, Any],
    headless: bool = True,
) -> Dict[str, Any]:
    """执行单个browser_use操作。"""
    try:
        # 导入browser_use工具
        from copaw.agents.tools.browser_control import browser_use

        # 调整headless参数
        if action == "start":
            params["headed"] = not headless

        # 执行操作
        result = await browser_use(
            action=action,
            **params,
        )

        return {
            "ok": True,
            "action": action,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Failed to execute action '{action}': {e}")
        return {
            "ok": False,
            "action": action,
            "error": str(e),
        }


async def execute_recording(
    name: str,
    param_values: Dict[str, str],
    headless: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """执行完整的录制。"""
    try:
        recording = load_recording(name)
    except FileNotFoundError as e:
        return {
            "ok": False,
            "error": str(e),
        }

    actions = recording.get("actions", [])
    total_steps = len(actions)
    executed_steps = 0
    failed_steps = 0
    results = []

    logger.info(f"Executing recording '{name}' with {total_steps} steps")

    # 存储当前refs映射（用于元素定位）
    current_refs: Dict[str, Any] = {}

    for action_entry in actions:
        action = action_entry.get("action", "")
        original_params = action_entry.get("params", {})

        # 替换参数
        params = substitute_params(original_params, param_values)

        # 处理元素定位（混合策略）
        # 如果有selector，优先使用selector
        # 如果只有ref，尝试使用selector或重新获取refs
        if "ref" in params and "selector" in params:
            # 有selector，移除ref让browser_use使用selector
            # 注意：browser_use支持selector参数
            pass  # 保持两个参数，browser_use会优先使用ref
        elif "ref" in params and not "selector" in params:
            # 只有ref，需要确保refs有效
            # 如果执行前没有snapshot，需要先获取refs
            pass  # 暂时保持原样，后续可优化

        if dry_run:
            # 干运行模式，只打印不执行
            logger.info(f"[DRY RUN] Step {action_entry.get('step')}: {action} with params {params}")
            results.append({
                "step": action_entry.get("step"),
                "action": action,
                "params": params,
                "dry_run": True,
            })
            executed_steps += 1
            continue

        # 执行操作
        result = await execute_browser_action(action, params, headless)

        results.append({
            "step": action_entry.get("step"),
            "action": action,
            "params": params,
            "result": result,
        })

        if result.get("ok"):
            executed_steps += 1
            logger.info(f"Step {action_entry.get('step')}: {action} - OK")

            # 如果是snapshot，保存refs
            if action == "snapshot":
                browser_result = result.get("result", {})
                if isinstance(browser_result, dict):
                    # 从结果中提取refs
                    refs_data = browser_result.get("refs", {})
                    if refs_data:
                        current_refs = refs_data

        else:
            failed_steps += 1
            logger.error(f"Step {action_entry.get('step')}: {action} - FAILED: {result.get('error')}")

            # 可选：继续执行或停止
            # 这里选择继续执行

    # 关闭浏览器（如果需要）
    if not dry_run and executed_steps > 0:
        # 尝试关闭浏览器
        try:
            close_result = await execute_browser_action("stop", {}, headless)
            logger.info("Browser closed")
        except Exception:
            pass  # 忽略关闭错误

    return {
        "ok": failed_steps == 0,
        "name": name,
        "total_steps": total_steps,
        "executed_steps": executed_steps,
        "failed_steps": failed_steps,
        "results": results,
        "message": f"Recording '{name}' executed: {executed_steps}/{total_steps} steps completed",
    }


def parse_param_value(param_str: str) -> tuple:
    """解析参数字符串 key=value。"""
    if "=" in param_str:
        key, value = param_str.split("=", 1)
        return key.strip(), value.strip()
    return param_str, ""


def main():
    parser = argparse.ArgumentParser(
        description="浏览器脚本执行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--recording",
        type=str,
        required=True,
        help="录制名称",
    )
    parser.add_argument(
        "--param",
        type=str,
        action="append",
        default=[],
        help="参数值，格式: key=value",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="显示浏览器窗口",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="无头模式（默认）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干运行，只打印不执行",
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

    # 解析参数值
    param_values: Dict[str, str] = {}
    for param_str in args.param:
        key, value = parse_param_value(param_str)
        if key:
            param_values[key] = value

    # 确定headless模式
    headless = not args.headed

    # 执行录制
    try:
        result = asyncio.run(
            execute_recording(
                args.recording,
                param_values,
                headless,
                args.dry_run,
            )
        )
    except Exception as e:
        result = {
            "ok": False,
            "error": str(e),
        }

    # 输出结果
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not result.get("ok", False):
        sys.exit(1)


if __name__ == "__main__":
    main()