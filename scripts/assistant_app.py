"""Schedule assistant app.

    uv run python scripts/assistant_app.py serve --demo      # fictional data, no model, no network
    uv run python scripts/assistant_app.py serve             # Mistral + Tavily (spends credits)
    uv run python scripts/assistant_app.py run-once --demo   # one run in the terminal

Live mode calls the model and web search only when a run starts (the
"지금 실행" button, or the schedule if you turn it on in Settings), and stops
at the daily caps in Settings. Nothing is retried.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from assistant import db, demo  # noqa: E402
from assistant.activity import EventBus  # noqa: E402
from assistant.config import DEFAULTS, load_secrets, load_settings, save_settings  # noqa: E402
from assistant.llm import client_from_settings  # noqa: E402
from assistant.pipeline import AppContext, run_now  # noqa: E402
from assistant.scheduler import Scheduler  # noqa: E402


def build_context(args) -> AppContext:
    data_dir = (args.data_dir or ROOT / ".assistant" / ("demo" if args.demo else "live")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    settings_path = data_dir / "settings.json"
    if not settings_path.exists():
        save_settings(settings_path, demo.demo_settings(DEFAULTS) if args.demo else DEFAULTS)
    if args.demo:
        data = demo.build()
        delay = 0.0 if args.command == "run-once" else args.demo_delay
        return AppContext(data_dir, EventBus(), lambda s: demo.demo_client(data, delay_s=delay),
                          lambda s: demo.DemoWeb(data), mode="demo")
    loaded = load_secrets(ROOT / ".env")
    print(f".env에서 읽은 키: {', '.join(loaded) or '없음'} (값은 표시하지 않음)")
    from task_a.web import LiveWebProvider
    return AppContext(data_dir, EventBus(), lambda s: client_from_settings(s["llm"]),
                      lambda s: LiveWebProvider(provider="tavily"), mode="live")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["serve", "run-once"])
    parser.add_argument("--demo", action="store_true", help="가상 데이터와 가짜 모델로 실행(비용 없음)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--demo-delay", type=float, default=0.6, help="시연에서 단계 사이 지연(초)")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reset", action="store_true", help="데이터 폴더의 DB를 지우고 시작(시연 재시작용)")
    args = parser.parse_args(argv)
    if args.host not in ("127.0.0.1", "localhost"):
        parser.error("이 앱은 내 컴퓨터(127.0.0.1)에서만 엽니다.")

    ctx = build_context(args)
    if args.reset and ctx.db_path.exists():
        for suffix in ("", "-wal", "-shm"):
            Path(str(ctx.db_path) + suffix).unlink(missing_ok=True)
    conn = ctx.connect()
    interrupted = db.mark_interrupted_runs(conn)
    conn.close()
    if interrupted:
        print(f"지난번에 끝나지 않은 실행 {interrupted}개를 '중단됨'으로 기록했습니다.")

    if args.command == "run-once":
        run_id = run_now(ctx, "cli")
        conn = ctx.connect()
        run = db.get_run(conn, run_id)
        print(f"실행 {run_id}: {run['status']} · {run['summary']}")
        return 0 if run["status"] == "ok" else 1

    from assistant.server import make_server
    server = make_server(ctx, args.host, args.port)
    Scheduler(ctx).start()
    url = f"http://{args.host}:{server.server_address[1]}/"
    sched = load_settings(ctx.settings_path)["schedule"]
    print(f"일정 비서 ({'시연 모드' if args.demo else '실제 모드'}): {url}")
    print(f"자동 실행: {'켜짐 ' + sched['daily_at'] if sched['enabled'] else '꺼짐'} · 끄려면 Ctrl+C")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
