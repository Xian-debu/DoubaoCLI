"""CLI for Doubao Automation Framework.

Usage:
    doubao chat <prompt> [--new] [--timeout N]
    doubao status
    doubao pages [--close | --index N | --clean]
    doubao cookies extract [--path FILE]
    doubao cookies validate [--path FILE]
    doubao cookies refresh
    doubao conversations [--limit N]
    doubao api <prompt> [--timeout N]
"""

import sys
import time
from pathlib import Path


def cmd_chat(args):
    """Send a chat message via browser UI."""
    from . import CDPManager, AuthManager, HumanPacer, ChatSession

    print("Connecting to Edge...")
    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    auth = AuthManager(cdp)
    pacer = HumanPacer()
    session = ChatSession(cdp, auth, pacer)

    print(f"Sending: {args.prompt[:60]}...")
    result = session.send(
        args.prompt,
        new_conversation=args.new,
        timeout=getattr(args, "timeout", 120),
    )

    if result.error:
        print(f"  ERROR: {result.error}")
    else:
        print(f"  Response ({result.elapsed:.1f}s):")
        print(f"  {result.text}")

    cdp.close()


def cmd_status(args):
    """Print connection + auth status."""
    from . import CDPManager, AuthManager, HumanPacer

    print("Doubao Framework Status")
    print("-" * 40)

    # CDP
    print(f"CDP URL: default ({'localhost:9222'})")
    cdp = CDPManager()
    try:
        cdp.connect()
        print("  Connection: OK")
        page = cdp.find_page()
        if page:
            print(f"  Page: {page.title()[:60]} | {page.url[:80]}")
        else:
            print("  Page: no doubao tab found")
    except Exception as e:
        print(f"  Connection: FAILED — {e}")
        return

    # Auth
    auth = AuthManager(cdp)
    status = auth.is_logged_in(browser_check=True)
    print(f"  Logged in: {'YES' if status.is_logged_in else 'NO'}")
    if status.auth_key:
        print(f"  Auth key: {status.auth_key}")
    if status.session_valid is not None:
        print(f"  Session valid: {status.session_valid}")
    print(f"  Cookie count: {status.cookie_count}")

    # Rate
    pacer = HumanPacer()
    ok, msg = pacer.check_limit()
    print(f"  Rate limit: {'OK' if ok else 'BLOCKED'} — {msg}")

    cdp.close()


def cmd_pages(args):
    """Manage doubao browser tabs."""
    from . import CDPManager

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    if getattr(args, "close", False):
        index = getattr(args, "index", -1)
        closed = cdp.close_page(index=index)
        print(f"Closed {closed} page(s)")
    elif getattr(args, "clean", False):
        trimmed = cdp.trim_pages(max_pages=5)
        print(f"Trimmed {trimmed} page(s), {cdp.page_count} remaining")
    else:
        pages = cdp.list_doubao_pages()
        if not pages:
            print("No doubao pages found")
        else:
            current_url = cdp.page.url if cdp.page else ""
            for p in pages:
                marker = " <-- current" if p.url == current_url else ""
                cid = f" [{p.conversation_id[:12]}...]" if p.conversation_id else ""
                print(f"  [{p.index}] {p.title[:50]}{cid}{marker}")
            print(f"\n  Total: {len(pages)} pages")

    cdp.close()


def cmd_cookies_extract(args):
    """Extract and save cookies from browser."""
    from . import CDPManager, AuthManager

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    auth = AuthManager(cdp)
    cookies = auth.extract()
    status = auth.validate(cookies)
    print(f"Found {len(cookies)} cookies, logged in: {status.is_logged_in}")

    if not cookies:
        cdp.close()
        return

    target = getattr(args, "path", None) or auth.cookie_path
    count = auth.save(cookies, path=target)
    print(f"Saved {count} cookies to {target}")

    cdp.close()


def cmd_cookies_validate(args):
    """Validate saved cookie file."""
    from .auth import AuthManager

    path = getattr(args, "path", None)
    auth = AuthManager(cookie_path=path) if path else AuthManager()
    cookies = auth.load(path) if path else auth.load()
    status = auth.validate(cookies)

    print(f"File: {path or auth.cookie_path}")
    print(f"Cookies: {len(cookies)}")
    print(f"Logged in: {status.is_logged_in}")
    if status.auth_key:
        print(f"Auth key: {status.auth_key}")


def cmd_cookies_refresh(args):
    """Re-extract and re-save cookies from browser."""
    from . import CDPManager, AuthManager

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    auth = AuthManager(cdp)
    ok = auth.refresh()
    if ok:
        print(f"Cookies refreshed: {auth.cookie_path}")
    else:
        print("Refresh failed")

    cdp.close()


def cmd_conversations(args):
    """List conversation history."""
    from . import CDPManager, AuthManager
    from .chat import ChatSession

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    limit = getattr(args, "limit", 10)

    convs = session.get_conversations(limit=limit)
    if convs:
        print(f"Conversations ({len(convs)}):")
        for c in convs:
            print(f"  [{c.id}] {c.title[:60]}")
            if c.preview:
                print(f"       {c.preview[:80]}")
    else:
        print("No conversations found (sidebar structure may have changed)")

    cdp.close()


def cmd_mode(args):
    """Switch chat mode."""
    from . import CDPManager
    from .modes import switch_mode, get_active_mode

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    page = cdp.find_page("doubao.com")
    if not page:
        print("No doubao page found")
        cdp.close()
        return

    current = get_active_mode(page)
    print(f"Current mode: {current or 'unknown'}")
    mode = args.mode
    ok = switch_mode(page, mode)
    print(f"Switch to '{mode}': {'OK' if ok else 'FAILED'}")
    cdp.close()


def cmd_skill(args):
    """Select a skill tool."""
    from . import CDPManager
    from .modes import select_skill, get_available_skills

    if args.list:
        skills = get_available_skills(None)
        print("Available skills:")
        for s in skills:
            print(f"  - {s}")
        return

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    page = cdp.find_page("doubao.com")
    if not page:
        print("No doubao page found")
        cdp.close()
        return

    ok = select_skill(page, args.name)
    print(f"Select skill '{args.name}': {'OK' if ok else 'FAILED'}")
    cdp.close()


def cmd_think(args):
    """Toggle deep think mode (via 超能模式)."""
    from . import CDPManager
    from .deep_think import enable, disable, is_enabled, get_thinking_process

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    page = cdp.find_page("doubao.com")
    if not page:
        print("No doubao page found")
        cdp.close()
        return

    if args.show:
        thinking = get_thinking_process(page)
        if thinking:
            print(f"Thinking process:\n{thinking[:1000]}")
        else:
            print("No thinking content found (超能モード may not be active)")
    else:
        state = args.state
        if state == "on":
            ok = enable(page)
        else:
            ok = disable(page)
        print(f"Deep think '{state}': {'OK' if ok else 'FAILED'}")
    cdp.close()


def cmd_multi(args):
    """Send a message in multi-response comparison mode."""
    from . import CDPManager, AuthManager, ChatSession

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    print(f"Sending (multi): {args.prompt[:60]}...")
    result = session.send_multi(args.prompt, timeout=getattr(args, "timeout", 180))
    if result.error:
        print(f"  ERROR: {result.error}")
    else:
        print(f"  Response ({result.elapsed:.1f}s):")
        print(f"  {result.text[:1500]}")
    cdp.close()


def cmd_image(args):
    """Generate an AI image."""
    from . import CDPManager, AuthManager, ChatSession

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    print(f"Generating image: {args.prompt[:60]}...")
    result = session.send_image(args.prompt, timeout=getattr(args, "timeout", 120))
    if result.error:
        print(f"  ERROR: {result.error}")
    else:
        print(f"  Model: {result.model}  |  Time: {result.elapsed:.1f}s")
        for i, url in enumerate(result.urls):
            print(f"  [{i+1}] {url[:120]}")
        if not result.urls:
            print("  No images returned")
    cdp.close()


def cmd_qa(args):
    """Run a deep Q&A session on a document."""
    from . import CDPManager, AuthManager, ChatSession
    from .deep_qa import DeepQA
    from .pacing import HumanPacer

    cdp = CDPManager()
    try: cdp.connect()
    except Exception as e: print(f"ERROR: {e}"); return

    auth = AuthManager(cdp)
    pacer = HumanPacer(mode="research")
    session = ChatSession(cdp, auth, pacer)

    # Questions from args or defaults
    questions = getattr(args, "questions", None)
    if not questions:
        questions = [
            "请详细总结这篇文档的研究目标、核心方法和主要发现。",
            "文档中使用的核心技术/方法具体是怎么实现的？",
            "文档研究了哪些关键问题？各有什么特征？",
            "实验/验证是怎么设计的？用了什么数据？",
            "文档中有什么关键公式、数据或定量结果？请列出并解释。",
            "这个研究有什么局限性或不足？",
            "这个方法的实际应用前景如何？有什么挑战？",
            "文档引用了哪些关键相关工作？",
        ]

    qa = DeepQA(session)
    results = qa.run(
        args.file,
        questions=questions,
        max_rounds=getattr(args, "rounds", len(questions)),
        quality_threshold=getattr(args, "quality", 80),
    )

    print(f"\n{'='*60}")
    ok_count = len([r for r in results if r.get('status') == 'ok'])
    print(f"  Deep QA Complete: {ok_count}/{len(results)} quality answers")
    for r in results:
        if r.get("error"):
            print(f"  ERROR: {r['error']}")
            continue
        if "question" not in r:
            continue
        status_icon = "✓" if r.get("status") == "ok" else "✗"
        q_preview = r["question"][:60]
        a_len = len(r.get("answer", "") or "")
        print(f"  R{r['round']}(C{r.get('conv',1)}) {status_icon} Q={q_preview}... A={a_len}chars")
    cdp.close()


def cmd_msg(args):
    """Perform an action on the last message."""
    from . import CDPManager, AuthManager, ChatSession

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    action = args.action
    if action == "like":
        ok = session.like()
    elif action == "dislike":
        ok = session.dislike()
    elif action == "regenerate":
        ok = session.regenerate()
    elif action == "copy":
        from .message_actions import copy_response
        ok = copy_response(cdp.page)
    else:
        print(f"Unknown action: {action}")
        ok = False
    print(f"Action '{action}': {'OK' if ok else 'FAILED'}")
    cdp.close()


def cmd_conv(args):
    """Manage conversations."""
    from . import CDPManager, AuthManager
    from .conversation import list_conversations, delete_conversation

    cdp = CDPManager()
    try:
        cdp.connect()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    auth = AuthManager(cdp)
    page = cdp.find_page("doubao.com")

    if args.delete:
        ok = delete_conversation(page, args.delete)
        print(f"Delete conv '{args.delete}': {'OK' if ok else 'FAILED'}")
    else:
        if not page:
            print("No doubao page found")
        else:
            convs = list_conversations(page, limit=args.limit or 20)
            for c in convs:
                print(f"  [{c.id[:12]}...] {c.title[:50]}{' ' + c.preview if c.preview else ''}")
            print(f"\n  Total: {len(convs)} conversations")
    cdp.close()


def cmd_upload(args):
    """Upload a file to Doubao chat."""
    from . import CDPManager, AuthManager, ChatSession

    cdp = CDPManager()
    try: cdp.connect()
    except Exception as e: print(f"ERROR: {e}"); return

    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    prompt = getattr(args, "prompt", None) or f"请分析这个文件：{args.file}"

    print(f"Uploading: {args.file}")
    result = session.send_with_file(prompt, args.file, timeout=getattr(args, "timeout", 180))
    if result.error: print(f"  ERROR: {result.error}")
    else: print(f"  Response ({result.elapsed:.1f}s):\n  {result.text[:2000]}")
    cdp.close()


def cmd_pdf(args):
    """PDF analysis commands."""
    from . import CDPManager, AuthManager, ChatSession

    cdp = CDPManager()
    try: cdp.connect()
    except Exception as e: print(f"ERROR: {e}"); return

    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)

    if getattr(args, "to_kb", False):
        print(f"PDF → KB: {args.file}")
        chunks = session.pdf_to_kb(args.file, category=getattr(args, "category", "document-analysis"),
                                   timeout=getattr(args, "timeout", 300))
        print(f"  Ingested: {chunks} chunks into KB")
    else:
        questions = getattr(args, "questions", None)
        print(f"Analyzing PDF: {args.file}")
        analysis = session.analyze_document(args.file, questions=questions,
                                            timeout=getattr(args, "timeout", 300))
        if "error" in analysis:
            print(f"  ERROR: {analysis['error']}")
        else:
            for s in analysis.get("sections", []):
                print(f"\n{'='*60}")
                print(f"Q: {s['question'][:100]}")
                print(f"A: {s['answer'][:800]}")
    cdp.close()


def cmd_image_describe(args):
    """Describe an image via Doubao."""
    from . import CDPManager, AuthManager, ChatSession

    cdp = CDPManager()
    try: cdp.connect()
    except Exception as e: print(f"ERROR: {e}"); return

    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    print(f"Analyzing image: {args.file}")
    desc = session.describe_image(args.file, question=getattr(args, "question", None),
                                  timeout=getattr(args, "timeout", 120))
    print(f"  {desc[:2000]}")
    cdp.close()


def cmd_api(args):
    """Send via HTTP API (fallback path)."""
    from .api_client import DoubaoAPIClient

    client = DoubaoAPIClient()
    print(f"API: {args.prompt[:60]}...")
    result = client.chat(args.prompt)

    if result.error:
        print(f"  ERROR: {result.error}")
        if result.raw_text:
            print(f"  Raw: {result.raw_text[:200]}")
    else:
        print(f"  Response ({result.elapsed:.1f}s):")
        print(f"  {result.text}")

    if result.raw_text and not result.error:
        # Show raw events if available
        if "event_type" in result.raw_text:
            events = client._parse_sse(result.raw_text)
            print(f"\n  SSE events: {len(events)}")


def main():
    """CLI entry point. Dispatches to cmd_<verb> functions."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Doubao Automation Framework",
        prog="doubao",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # chat
    p = sub.add_parser("chat", help="Send message via browser UI")
    p.add_argument("prompt", help="Message text")
    p.add_argument("--new", action="store_true", help="Start new conversation")
    p.add_argument("--timeout", type=int, default=120)
    p.set_defaults(func=cmd_chat)

    # status
    p = sub.add_parser("status", help="Check connection + auth + rate limits")
    p.set_defaults(func=cmd_status)

    # cookies extract
    p = sub.add_parser("cookies", help="Cookie management")
    csub = p.add_subparsers(dest="cookie_cmd")
    ce = csub.add_parser("extract", help="Extract cookies from browser")
    ce.add_argument("--path", type=str, help="Output file path")
    ce.set_defaults(func=cmd_cookies_extract)
    cv = csub.add_parser("validate", help="Validate cookie file")
    cv.add_argument("--path", type=str, help="Cookie file path")
    cv.set_defaults(func=cmd_cookies_validate)
    cr = csub.add_parser("refresh", help="Re-extract and save cookies")
    cr.set_defaults(func=cmd_cookies_refresh)

    # pages
    p = sub.add_parser("pages", help="Manage doubao browser tabs")
    p.add_argument("--close", action="store_true", help="Close all other pages")
    p.add_argument("--index", type=int, default=-1, help="Close specific page by index")
    p.add_argument("--clean", action="store_true", help="Trim to max 5 pages")
    p.set_defaults(func=cmd_pages)

    # conversations
    p = sub.add_parser("conversations", help="List conversation history")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_conversations)

    # mode
    p = sub.add_parser("mode", help="Switch chat mode (quick/super)")
    p.add_argument("mode", choices=["quick", "super"], help="Target mode")
    p.set_defaults(func=cmd_mode)

    # skill
    p = sub.add_parser("skill", help="Select a skill tool")
    p.add_argument("name", nargs="?", help="Skill name (15 available)")
    p.add_argument("--list", action="store_true", help="List all available skills")
    p.set_defaults(func=cmd_skill)

    # think
    p = sub.add_parser("think", help="Deep think mode (via 超能模式)")
    p.add_argument("state", nargs="?", choices=["on", "off"], help="Enable/disable")
    p.add_argument("--show", action="store_true", help="Show thinking process")
    p.set_defaults(func=cmd_think)

    # multi
    p = sub.add_parser("multi", help="Multi-response comparison (5 parallel answers)")
    p.add_argument("prompt", help="Message text")
    p.add_argument("--timeout", type=int, default=180)
    p.set_defaults(func=cmd_multi)

    # draw
    p = sub.add_parser("draw", help="Generate AI image via /chat/create-image")
    p.add_argument("prompt", help="Image description")
    p.add_argument("--timeout", type=int, default=120)
    p.set_defaults(func=cmd_image)

    # msg
    p = sub.add_parser("msg", help="Message action (like/dislike/regenerate/copy)")
    p.add_argument("action", choices=["like", "dislike", "regenerate", "copy"])
    p.set_defaults(func=cmd_msg)

    # conv
    p = sub.add_parser("conv", help="Conversation management")
    p.add_argument("--delete", type=str, metavar="ID", help="Delete conversation by ID")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_conv)

    # upload
    p = sub.add_parser("upload", help="Upload a file and ask about it")
    p.add_argument("file", help="File path to upload")
    p.add_argument("--prompt", type=str, help="Question about the file")
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--new", action="store_true", help="Start new conversation")
    p.set_defaults(func=cmd_upload)

    # pdf
    p = sub.add_parser("pdf", help="PDF analysis (analyze / to-kb)")
    p.add_argument("file", help="PDF file path")
    p.add_argument("--to-kb", action="store_true", help="Ingest analysis into KB")
    p.add_argument("--category", type=str, default="document-analysis")
    p.add_argument("--questions", nargs="+", help="Custom questions")
    p.add_argument("--timeout", type=int, default=300)
    p.set_defaults(func=cmd_pdf)

    # image (describe existing image via upload)
    p = sub.add_parser("image", help="Describe/analyze an image via Doubao")
    p.add_argument("file", help="Image file path")
    p.add_argument("--question", type=str, help="Custom question")
    p.add_argument("--timeout", type=int, default=120)
    p.set_defaults(func=cmd_image_describe)

    # qa
    p = sub.add_parser("qa", help="Deep Q&A session on a document")
    p.add_argument("file", help="Document file path")
    p.add_argument("--rounds", type=int, help="Max rounds")
    p.add_argument("--questions", nargs="+", help="Custom questions")
    p.add_argument("--quality", type=int, default=80, help="Min quality (chars)")
    p.set_defaults(func=cmd_qa)

    # api
    p = sub.add_parser("api", help="HTTP API fallback (rate-limited!)")
    p.add_argument("prompt", help="Message text")
    p.add_argument("--timeout", type=int, default=90)
    p.set_defaults(func=cmd_api)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
    elif args.command == "cookies" and not getattr(args, "cookie_cmd", None):
        parser.parse_args(["cookies", "--help"])
    else:
        args.func(args)


if __name__ == "__main__":
    main()
