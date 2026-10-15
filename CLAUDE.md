# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A learning project implementing TCP/IP client-server communication in Python, secured with SSL/TLS over a self-signed certificate. It contains two alternate server designs (single-client and multi-client) kept side by side for comparison, plus one interactive client. Python 3.12 venv at `.venv/` (`.venv/Scripts/python.exe`); only PyYAML, colorama and pytest are needed.

## Before anything runs: the certificate

`certs/` is gitignored (`.gitignore` lists both `certs/` and `*.pem`) and untracked, so a fresh clone has no cert at all — `_find_full_file_path()` returns `None` and every module (`raise FileExistsError`) refuses to start until a pair exists. The local pair `certs/ilana_cert_01.pem` / `ilana_key_01.pem` is currently valid (regenerated 2026-09-11, expires 2027-09-11); regenerate before that date, or immediately on a fresh clone (filenames are hardcoded in all four modules; `check_hostname = False` on the client means no SAN is required):

```
openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj "/C=IL" -keyout certs/ilana_key_01.pem -out certs/ilana_cert_01.pem
```

## Commands

Run tests (from repo root):

```
.venv/Scripts/python.exe -m pytest
```

`from src.client_tcp import Client` resolves with no extra setup: `src/` and `tests/` both have `__init__.py`, so pytest inserts the repo root on `sys.path`. `python.ini` holds `[pytest]\npythonpath = src` but is **not** one of pytest's auto-discovered filenames (`pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`) — it is effectively dead config, so don't add `-c python.ini` expecting it to change anything.

Run a single test (all live in `tests/test_client.py::TestClient`; `--collect-only -q` lists the 7):

```
.venv/Scripts/python.exe -m pytest tests/test_client.py::TestClient::test_client_gives_up_after_max_retries -s
```

`-s` is worth adding: every module narrates its state with `print()`, and that output is the main debugging signal. All `@pytest.fixture`s in `tests/test_client.py` are commented out; each test builds and tears down its own server process inline. `tests/test_server.py` contains imports only, no test cases.

Expect a full run to be slow — wall-clock is dominated by real delays: `test_client_gives_up_after_max_retries` waits out all `max_retries × retry_delay` (10 × 2s ≈ 20s), and `test_client_start_client_server_yet_running` delays server start by 15s.

Run the apps directly (pick one server implementation, they are not interchangeable — see Architecture):

```
python src/server_tcp.py                         # single-client server
python src/multi_client_by_select_server_tcp.py  # multi-client server
python src/client_tcp.py                         # interactive client
```

Start whichever server first, then the client(s) — the client retries connecting (`max_retries` / `retry_delay` in `configs/client_config.yaml`) but the single-client server does not wait for late clients. Type `q` at the client prompt to end a session; that message is also what tells the server to shut down its per-client path.

## Architecture

**Two independent server implementations (`Server` and `Multi_Clients_Server`), not interchangeable:**

- `src/server_tcp.py` — single client only (`MAX_CONNECTIONS = 1`), blocking `accept()`. After connecting, two long-lived threads coordinate through one `queue.Queue`: `_receive_messages` (socket → queue) and `_process_messages` (queue → socket, sends a fixed reply). When the client vanishes, `_receive_messages` pushes a sentinel `'q'` into the queue — that is how the second thread learns to stop. Config is read in `__init__`; socket setup happens in `start()`.
- `src/multi_client_by_select_server_tcp.py` — multi-client. `start()` runs `_init()` → `_create_server_socket()` → `_scan_sockets()`. The main thread's `select.select()` (5s timeout) multiplexes `accept()` on the listening socket and `recv()` across all connected client sockets; a fixed pool of worker threads (`_working_thread`, count from `number_working_threads` in `configs/server_config.yaml`) pulls `(socket, address, message)` tuples off one shared `queue.Queue` and replies directly on that client's socket. The whole server returns once the last client leaves — whether it sent `q`, closed gracefully (empty `recv`), or crashed (`ConnectionError`/`ssl.SSLError` from `recv`); all three paths go through `_remove_client()`, which returns `True` when `monitored_client_sockets_list` and `all_clients` are both empty. Worker threads are daemons named `working_thread_<N>`, and `_working_thread` parses `<N>` out of its own thread name to index `colors_dict` for colored log output — so thread count is implicitly capped at 10 (keys 0-9), and a larger value raises `KeyError` inside the worker.

Both servers `wrap_socket(..., server_side=True)` the *listening* socket, so each TLS handshake runs inside `accept()` on the accepting thread.

**Client:** `src/client_tcp.py` — one `Client`, interactive stdin loop (`start()`): read a line, `send()`, block on `_receive()`, repeat until the user types `q`. `send()` / `_receive()` return `True` / `False` rather than raising, so callers (and tests) can observe connection failure without a `try/except` — that return-value contract is what the tests assert on. `__init__` connects eagerly, so constructing a `Client` *is* the connection attempt. `_connect()` rebuilds the raw socket, the SSL context and the cert lookup fresh on *every* retry iteration (not once before the loop), and its `try/except` around `connect()` catches `ssl.SSLError` alongside `ConnectionRefusedError` / `socket.timeout` — so a handshake failure (bad/expired cert, reset connection) is retried up to `max_retries` times, `retry_delay` seconds apart, before falling into the `for...else` and calling `exit(1)`.

**TLS everywhere:** all three wrap raw TCP sockets with `ssl.create_default_context()` using the pair in `certs/`. Server side loads both via `load_cert_chain`. Client side pins trust to that same cert and sets `context.check_hostname = False`, since the cert is self-signed and carries no hostname (its subject is just `C=IL`).

**Config loading:** Client and each Server read `configs/client_config.yaml` / `configs/server_config.yaml` respectively (ip, port, `max_data_size`, plus client-only retry settings and server-only `number_working_threads`); both use port 8820. All three modules — plus `MockServer` in `tests/test_client.py` — duplicate a private `_find_full_file_path()` helper that `os.walk`s **downward from `Path.cwd().parent`**, i.e. from the directory *containing* this repo. Launched from the repo root it therefore recursively scans every sibling repo and `.venv/` for a filename match and takes the first hit — so the launch directory affects both startup cost and which file is found. A miss raises a bare `FileExistsError` (used, confusingly, to signal *not* found).

**Testing approach:** `tests/test_client.py` does not mock sockets. `MockServer` spins up a real SSL-wrapped echo server as a separate OS `multiprocessing.Process` so a test can `.terminate()` it mid-conversation to simulate a real server crash, then asserts on `Client.send()` / `Client._receive()` return values to check the client degrades gracefully instead of hanging or raising. The three `test_multi_client_server_*` / `test_client_start_client_server_yet_running` tests instead run the **real** `Multi_Clients_Server` in a child `Process` (via module-level `_start_multi_client_server(delay)`) and assert on `process.is_alive()` after `join(timeout=10)` to verify the server shuts itself down when the last client sends `q`. `test_client_gives_up_after_max_retries` starts no server and expects `pytest.raises(SystemExit)` with code 1 from `Client()`. Tests bind the real port 8820 from `configs/server_config.yaml` and use real `time.sleep()` delays for process startup/shutdown timing — they are not hermetic or parallel-safe, and the two runnable tests cannot run concurrently with each other.

## Known quirks

- **Avast Web Shield MITMs the TLS connection on loopback — recurring, not a one-time fix.** Confirmed three separate times (2026-09-16, -22, -29/-30) with a standalone `openssl s_client`/`s_server` handshake against `certs/ilana_cert_01.pem`, bypassing Python entirely: the certificate actually received on the wire is issued by `CN=Avast Web/Mail Shield Self-signed Root`, not the real self-signed cert — Avast's **Web Shield** (HTTPS scanning) is transparently proxying the whole TLS session, not just the handshake. Two distinct symptom patterns from the same root cause:
  - *Tests:* `Client()` construction raises `SystemExit: 1` — `_connect()`'s `do_handshake()` gets `SSLCertVerificationError`/`ConnectionResetError` on every `max_retries` attempt (the bare `except (..., ssl.SSLError):` in `_connect()` has no `as ee`, so the real reason never prints — only "Server is down / not started yet").
  - *Running the apps manually* (`server_tcp.py` / `multi_client_by_select_server_tcp.py` + real client(s)): everything still connects, but noticeably slowly — slow new-client connects, slow responses, and slow crash-detection (a client crash is detected by the server only once Avast's proxy notices *its own* link to the client died and reacts, not instantly like a direct TCP reset would). Confirmed on 2026-09-30 that fully disabling Avast removed all three symptoms immediately.
  - An Avast *app/firewall* exception does **not** fix this (different component). The confirmed working fix on this machine: open Avast Antivirus → **"Scam Guardian"** in the left sidebar → turn off **"Web Guard"** (center of that window). This has not stayed off reliably across sessions — it's come back at least twice without anyone re-enabling it deliberately, so re-check it each time something TLS-related looks broken *or* slow, rather than assuming a code regression. To confirm one way or the other, re-run the `openssl s_client`/`s_server` check on loopback (see this session's history) — if the certificate it receives is issued by `CN=Avast Web/Mail Shield Self-signed Root`, Web Guard is back on.
- A test run can hang pytest indefinitely: the `MockServer` process is non-daemon and blocks in `accept()`, so if the client never completes its handshake, pytest waits on the child at exit. Check for and kill stray `python.exe` processes after an aborted run.
- `config/test_config.cfg` (note `config/`, not `configs/`) exists but nothing in `src/` or `tests/` reads it — it is not wired into the pytest run.
- `~$planation.docx` and `~WRL3097.tmp` are committed Word lock/temp files, not source.
