#!/usr/bin/env python3
"""Focused live browser checks; run only against the documented disposable fixtures.

Requires Playwright/Chromium, kubectl, saved UI connection ui-nats, JetStream
stream BROWSER_UI (browser.>), KV bucket BROWSER_KV, RedisInsight onboarding
and a saved Redis connection, key browser:redisinsight, and saved tree settings.
All application operations use the browser. CLI calls seed or independently
verify backend data. No localStorage injection or API response mocking is used.
"""
import argparse
import base64
import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--redis-url", default="http://localhost:5540")
parser.add_argument("--nui-url", default="http://localhost:31314")
parser.add_argument("--phase", choices=["initial", "after-pod-replacement"], default="initial")
parser.add_argument("--output", required=True)
args = parser.parse_args()
results = []
errors = []
http_errors = []
stamp = str(time.time_ns())
subject = "browser.check" + stamp
kv_key = "check" + stamp
payload = json.dumps({"source": "browser", "phase": args.phase, "nonce": stamp})

def check(name, condition=True):
    assert condition, (name, errors, http_errors)
    results.append({"name": name, "passed": True})

def cli(*command):
    return subprocess.check_output(
        ["kubectl", "-n", "broker", "exec", "deploy/nats-box", "--",
         "nats", "-s", "nats://nats:4222", *command], text=True
    ).strip()

def redis(command):
    # The password stays inside the fixture Pod's environment.
    return subprocess.check_output(
        ["kubectl", "-n", "ui", "exec", "deploy/redis-validation", "--",
         "sh", "-c", 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli ' + command],
        text=True,
    ).strip()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

    def new_page(url):
        # Each page has its own fresh browser context; never seed localStorage.
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: http_errors.append(
            {"path": r.url.split("/api/", 1)[-1], "status": r.status}
        ) if "/api/" in r.url and r.status >= 400 else None)
        page.goto(url, wait_until="networkidle")
        return page

    def nui_connection():
        page = new_page(args.nui_url)
        check("NUI fresh profile has no preloaded layout",
              page.evaluate("localStorage.getItem('docs-state')") is None)
        page.get_by_text("ALL", exact=True).click()
        page.get_by_text("ui-nats", exact=True).first.click()
        return page

    # RedisInsight: the browser must authenticate using its saved connection.
    redis("SET browser:redisinsight written-by-redis-cli")
    page = new_page(args.redis_url)
    page.locator('[data-testid^="instance-name-"]').first.click()
    page.get_by_test_id("search-key").fill("browser:redisinsight")
    page.get_by_test_id("search-key").press("Enter")
    page.get_by_test_id("key-redisinsight").click()
    expect(page.get_by_test_id("string-value")).to_have_text("written-by-redis-cli")
    check("RedisInsight browser reads redis-cli write")
    page.get_by_test_id("edit-key-value-btn").click()
    page.get_by_test_id("string-value").fill("verified-ui-" + args.phase)
    page.get_by_test_id("apply-btn").click()
    expect(page.get_by_test_id("string-value")).to_have_text("verified-ui-" + args.phase)
    check("RedisInsight browser edit confirmed by redis-cli",
          redis("GET browser:redisinsight") == "verified-ui-" + args.phase)
    page.reload(wait_until="networkidle")
    expect(page.get_by_test_id("search-key")).to_be_visible()
    check("RedisInsight browser reload recovers without onboarding")

    # NUI: publish through its actual editor and send control.
    page = nui_connection()
    page.locator(".card-connections.card--filled .jack-focus-1 .jack-cmp-button").click()
    page.get_by_placeholder("Click SUBJECT button or write here e.g. orders.>").fill(subject)
    page.locator(".monaco-editor textarea").focus()
    page.keyboard.insert_text(payload)
    with page.expect_response(lambda r: "/messages/publish" in r.url) as response:
        page.get_by_text("SEND", exact=True).click()
    check("NUI browser publish succeeds", response.value.status == 200)
    sequence = json.loads(cli("stream", "info", "BROWSER_UI", "--json"))["state"]["last_seq"]
    message = json.loads(cli("stream", "get", "BROWSER_UI", str(sequence), "--json"))
    check("NATS CLI confirms browser-published payload",
          json.loads(base64.b64decode(message["data"])) == json.loads(payload))
    cli_subject = "browser.cli" + stamp
    cli("pub", cli_subject, '{"source":"cli"}')

    # A separate fresh profile browses stored UI and CLI messages.
    page = nui_connection()
    page.locator(".card-connections.card--filled .jack-focus-3").click()
    page.get_by_text("BROWSER_UI", exact=True).first.click()
    page.locator(".card-streams.card--filled .jack-focus-1").click()
    expect(page.get_by_text(subject, exact=True).first).to_be_visible()
    expect(page.get_by_text(cli_subject, exact=True).first).to_be_visible()
    check("NUI browser lists persisted UI and CLI messages")

    # Create a KV entry in the browser, then verify both write directions.
    page = nui_connection()
    page.locator(".card-connections.card--filled .jack-focus-4").click()
    page.get_by_text("BROWSER_KV", exact=True).first.click()
    page.locator(".card-buckets.card--filled .jack-focus-1").click()
    page.locator(".jack-framework").last.get_by_text("NEW", exact=True).click()
    card = page.locator(".jack-framework").last
    card.get_by_text("KEY", exact=True).locator("..").locator("input").fill(kv_key)
    card.locator(".monaco-editor textarea").focus()
    page.keyboard.insert_text(payload)
    with page.expect_response(lambda r: "/key/" + kv_key in r.url and r.request.method == "POST") as response:
        card.get_by_text("CREATE", exact=True).click()
    check("NUI browser creates KV entry", response.value.status == 200)
    check("NATS CLI confirms browser KV payload",
          json.loads(cli("kv", "get", "BROWSER_KV", kv_key, "--raw")) == json.loads(payload))
    cli("kv", "put", "BROWSER_KV", "cli-created", '{"source":"nats-cli"}')
    page = nui_connection()
    page.locator(".card-connections.card--filled .jack-focus-4").click()
    page.get_by_text("BROWSER_KV", exact=True).first.click()
    page.locator(".card-buckets.card--filled .jack-focus-1").click()
    page.get_by_text("cli-created", exact=True).first.click()
    expect(page.locator(".monaco-editor")).to_contain_text("nats-cli")
    check("NUI browser reads CLI KV write")
    page.reload(wait_until="networkidle")
    expect(page.locator(".monaco-editor")).to_contain_text("nats-cli")
    check("NUI saved browser session reloads with KV detail")
    check("No browser JavaScript errors", not errors)
    check("No application API HTTP errors", not http_errors)
    browser.close()

evidence = {"phase": args.phase, "passed": len(results), "checks": results,
            "page_errors": errors, "application_http_errors": http_errors}
Path(args.output).write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps(evidence, indent=2))
