#!/usr/bin/env python3
"""Run all Doubao framework tests sequentially."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import test_config
import test_pacing
import test_auth
import test_browser
import test_api_client
import test_chat
import test_modes
import test_message_actions
import test_conversation
import test_deep_think
import test_file_upload
import test_integration


def main():
    print("=" * 50)
    print("  Doubao Framework Test Suite")
    print("=" * 50)
    print()

    modules = [
        ("config", test_config),
        ("pacing", test_pacing),
        ("browser", test_browser),
        ("auth", test_auth),
        ("api_client", test_api_client),
        ("chat", test_chat),
        ("modes", test_modes),
        ("msg_actions", test_message_actions),
        ("conversation", test_conversation),
        ("deep_think", test_deep_think),
        ("file_upload", test_file_upload),
        ("integration", test_integration),
    ]

    passed = 0
    failed = 0
    t_start = time.time()

    for name, module in modules:
        try:
            t0 = time.time()
            module.run_all()
            elapsed = time.time() - t0
            passed += 1
        except AssertionError as e:
            elapsed = time.time() - t0
            print(f"  [{name}] FAIL: {e}")
            failed += 1
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  [{name}] ERROR: {type(e).__name__}: {e}")
            failed += 1

    total = time.time() - t_start
    print()
    print("=" * 50)
    print(f"  Results: {passed} passed, {failed} failed ({total:.1f}s)")
    if failed > 0:
        print(f"  WARNING: {failed} module(s) had failures")
        sys.exit(1)
    else:
        print("  All modules passed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
