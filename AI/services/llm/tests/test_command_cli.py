"""
LLM 명령 생성 + MCP API 테스트 CLI (간소화 버전)

명령 생성 → 실행 → 실패 시 재시도
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 추가
services_root = Path(__file__).resolve().parents[2]
project_root = services_root.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(services_root))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[ERROR] requests 모듈 필요: pip install requests")
    sys.exit(1)

from llm.generators.command_generator import CommandGenerator
from llm.tests.session_manager import get_session_manager

# MCP API 서버
MCP_API_URL = "http://localhost:8000"


def execute_commands(commands):
    """MCP API로 명령 실행"""
    payload = {
        "type": "tool_calls",
        "data": {
            "commands": [
                {
                    "action": cmd.tool_name,
                    "args": cmd.arguments,
                    "desc": cmd.description or ""
                }
                for cmd in commands
            ]
        }
    }
    
    try:
        response = requests.post(
            f"{MCP_API_URL}/execute",
            json=payload,
            timeout=30
        )
        return response.json()
    except Exception as e:
        print(f"[ERROR] API 실행 실패: {e}")
        return None


def print_commands(result):
    """명령 출력"""
    print(f"\n[RULE] {result.matched_rule}")
    print(f"[RESP] {result.response_text}")
    print(f"[CMD] {len(result.commands)}개 명령")
    for i, cmd in enumerate(result.commands, 1):
        print(f"  {i}. {cmd.tool_name}({cmd.arguments})")


def print_result(api_result):
    """실행 결과 출력"""
    print("\n[EXEC] 결과:")
    results = api_result.get("results", [])
    for r in results:
        status = "✅" if r.get("success") else "❌"
        desc = r.get("desc", "명령")
        msg = r.get("result") or r.get("error", "")
        print(f"  {status} {desc}: {msg}")


async def interactive_mode(initial_url: str):
    """대화형 모드"""
    generator = CommandGenerator()
    session_mgr = get_session_manager()
    session = session_mgr.get_or_create_session("test-cli", initial_url)
    
    # MCP 연결
    print("\n=== LLM 명령 생성 CLI ===")
    print("[INFO] MCP 연결 중...")
    try:
        resp = requests.post(f"{MCP_API_URL}/start", timeout=10)
        if resp.ok:
            print("[OK] 연결 성공")
            url_resp = requests.get(f"{MCP_API_URL}/url", timeout=5)
            if url_resp.ok:
                session.update_url(url_resp.json().get("url", session.current_url))
    except:
        print("[WARN] MCP 연결 실패")
    
    print(f"\n명령어:")
    print(f"  /q       - 종료")
    print(f"\n[URL] {session.current_url}\n")
    
    while True:
        try:
            user_input = input("명령> ").strip()
            if not user_input:
                continue
            
            # 특수 명령
            if user_input in ["/q", "/quit"]:
                break
            # 명령 생성
            result = await generator.generate(user_input, session.current_url)
            print_commands(result)
            
            # 자동 실행
            if result.commands:
                print("\n[EXEC] 실행 중...")
                api_result = execute_commands(result.commands)
                if api_result:
                    print_result(api_result)
                    
                    # 실패 시 재시도
                    results = api_result.get("results", [])
                    has_failure = any(not r.get("success") for r in results)
                    
                    if has_failure:
                        failed_result = next((r for r in results if not r.get("success")), None)
                        error_msg = failed_result.get("error", "") if failed_result else ""
                        if result.matched_rule == "llm_fallback":
                            print(f"\n[ERROR] LLM fallback 실행 실패: {error_msg}")
                        else:
                            print("\n[RETRY] LLM 재시도...")
                            if failed_result:
                                failed_cmd = result.commands[results.index(failed_result)]
                                
                                retry_result = await generator.retry_with_llm(
                                    user_input,
                                    session.current_url,
                                    failed_cmd,
                                    error_msg
                                )
                                
                                if retry_result.commands:
                                    print_commands(retry_result)
                                    print("\n[EXEC] 재실행 중...")
                                    retry_api = execute_commands(retry_result.commands)
                                    if retry_api:
                                        print_result(retry_api)
                    
                    # URL 업데이트
                    try:
                        url_resp = requests.get(f"{MCP_API_URL}/url", timeout=5)
                        if url_resp.ok:
                            session.update_url(url_resp.json().get("url", session.current_url))
                    except:
                        pass
        
        except KeyboardInterrupt:
            print("\n종료")
            break
        except Exception as e:
            print(f"[ERROR] {e}")


def main():
    parser = argparse.ArgumentParser(description="LLM 명령 생성 CLI")
    parser.add_argument("--url", default="https://www.coupang.com/", help="초기 URL")
    parser.add_argument("-i", "--input", help="단일 명령 테스트")
    
    args = parser.parse_args()
    
    if args.input:
        # 단일 명령 모드
        async def run_single():
            generator = CommandGenerator()
            result = await generator.generate(args.input, args.url)
            print_commands(result)
            # 자동 실행
            if result.commands:
                api_result = execute_commands(result.commands)
                if api_result:
                    print_result(api_result)
        
        asyncio.run(run_single())
    else:
        # 대화형 모드
        asyncio.run(interactive_mode(args.url))


if __name__ == "__main__":
    main()
