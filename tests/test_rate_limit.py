"""Focused unit test for `check_rate_limit()` at the new window=1 second.

Exercises the sliding-window math that the production rate limiter uses,
without requiring a live Redis. Uses a hand-rolled fake redis that
implements only the ops check_rate_limit calls (zremrangebyscore, zadd,
zcard, expire, pipeline/execute).

Run:  python3 tests/test_rate_limit.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

# Make the project importable so `app.auth` resolves correctly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.auth as auth_mod  # noqa: E402


# ── Fake redis ──────────────────────────────────────────────────────────────


class FakeRedis:
    """Minimal Redis stub supporting only the ops check_rate_limit invokes."""

    def __init__(self) -> None:
        self.zsets: dict[str, dict[str, float]] = {}
        self.expiries: dict[str, int] = {}

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    """Async-friendly pipeline. Ops accumulate and execute() flushes them."""

    def __init__(self, redis: FakeRedis) -> None:
        self.redis = redis
        self.ops: list = []

    def zremrangebyscore(self, key, min_, max_):
        self.ops.append(("zremrangebyscore", key, min_, max_))
        return self

    def zadd(self, key, mapping):
        self.ops.append(("zadd", key, mapping))
        return self

    def zcard(self, key):
        self.ops.append(("zcard", key))
        return self

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))
        return self

    async def execute(self):
        results = []
        for op in self.ops:
            kind = op[0]
            if kind == "zremrangebyscore":
                _, key, min_, max_ = op
                cutoff_min = float(min_) if min_ != "-inf" else float("-inf")
                cutoff_max = float(max_) if max_ != "+inf" else float("inf")
                # Redis semantics: inclusive on both ends.
                members = self.redis.zsets.setdefault(key, {})
                to_drop = [m for m, s in list(members.items()) if cutoff_min <= s <= cutoff_max]
                for m in to_drop:
                    del members[m]
                results.append(len(to_drop))
            elif kind == "zadd":
                _, key, mapping = op
                self.redis.zsets.setdefault(key, {}).update(mapping)
                results.append(len(mapping))
            elif kind == "zcard":
                _, key = op
                results.append(len(self.redis.zsets.get(key, {})))
            elif kind == "expire":
                _, key, ttl = op
                self.redis.expiries[key] = ttl
                results.append(True)
        self.ops.clear()
        return results


# ── Test harness ────────────────────────────────────────────────────────────


async def main() -> None:
    fake = FakeRedis()
    # `check_rate_limit` resolves `get_redis` from `app.auth`'s globals —
    # patching the binding there is sufficient.
    auth_mod.get_redis = lambda: fake  # type: ignore[assignment]

    passed = failed = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal passed, failed
        status = "PASS" if cond else "FAIL"
        suffix = f" — {detail}" if detail else ""
        print(f"  [{status}] {name}{suffix}")
        if cond:
            passed += 1
        else:
            failed += 1

    # ── Test 1: single request, basic contract ──────────────────────────────
    print("\n── Test 1: single request, basic contract ──")
    fake.zsets.clear()
    fake.expiries.clear()
    ok, remaining, resets_at = await auth_mod.check_rate_limit("ip:solo", 5)
    check("first request allowed", ok is True)
    check("remaining == limit-1 (4)", remaining == 4, f"got {remaining}")
    # resets_at is floor(now + window). Allow ±1s wall-clock slack.
    expected_reset = int(time.time()) + 1
    check(
        "resets_at ≈ now+1",
        abs(resets_at - expected_reset) <= 1,
        f"got {resets_at}, expected ≈ {expected_reset}",
    )
    check("expire TTL is window+10 (11)", fake.expiries.get("ratelimit:ip:solo") == 11,
          f"got {fake.expiries.get('ratelimit:ip:solo')}")

    # ── Test 2: burst up to the limit ────────────────────────────────────────
    print("\n── Test 2: burst of limit=5, all allowed ──")
    fake.zsets.clear()
    fake.expiries.clear()
    last_remaining = None
    for i in range(1, 6):
        ok, last_remaining, _ = await auth_mod.check_rate_limit("ip:burst", 5)
        check(f"req #{i} allowed", ok is True)
    check("after 5 req, remaining == 0", last_remaining == 0, f"got {last_remaining}")
    check("zset has 5 members", len(fake.zsets["ratelimit:ip:burst"]) == 5)

    # ── Test 3: over the limit, denied ──────────────────────────────────────
    print("\n── Test 3: 6th request denied (still recorded in zset) ──")
    ok, remaining, _ = await auth_mod.check_rate_limit("ip:burst", 5)
    check("6th request denied", ok is False)
    check("remaining == 0", remaining == 0, f"got {remaining}")
    check("zset has 6 entries (denied request is still tracked)",
          len(fake.zsets["ratelimit:ip:burst"]) == 6)

    # ── Test 4: window resets after >1s ─────────────────────────────────────
    print("\n── Test 4: window resets after sleeping >1s ──")
    print("    sleeping 1.15s …")
    await asyncio.sleep(1.15)
    ok, remaining, _ = await auth_mod.check_rate_limit("ip:burst", 5)
    check("post-sleep request allowed", ok is True)
    check("remaining == 4 (window wiped)", remaining == 4, f"got {remaining}")

    # ── Test 5: limit=1, second request in same second denied ───────────────
    print("\n── Test 5: limit=1, tight window ──")
    fake.zsets.clear()
    fake.expiries.clear()
    ok1, r1, _ = await auth_mod.check_rate_limit("ip:tight", 1)
    ok2, r2, _ = await auth_mod.check_rate_limit("ip:tight", 1)
    check("first request allowed", ok1 is True)
    check("first remaining == 0", r1 == 0, f"got {r1}")
    check("second request denied (same second)", ok2 is False)
    check("second remaining == 0", r2 == 0, f"got {r2}")

    # ── Test 6: identifiers are isolated ────────────────────────────────────
    print("\n── Test 6: separate identifiers tracked independently ──")
    fake.zsets.clear()
    fake.expiries.clear()
    for _ in range(5):
        await auth_mod.check_rate_limit("ip:alice", 5)
    ok_alice_6, _, _ = await auth_mod.check_rate_limit("ip:alice", 5)
    check("alice hits limit", ok_alice_6 is False)

    ok_bob, bob_remaining, _ = await auth_mod.check_rate_limit("ip:bob", 5)
    check("bob unaffected by alice's traffic", ok_bob is True)
    check("bob remaining == 4", bob_remaining == 4, f"got {bob_remaining}")

    # ── Summary ─────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'=' * 50}")
    print(f"RESULTS: {passed} pass, {failed} fail ({total} total)")
    print('=' * 50)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
