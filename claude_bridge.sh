#!/bin/bash
# Claude Bridge — polls MOO's #0.claude_inbox for messages
# Outputs one line per new message for Monitor to pick up
# Usage: called by Claude's Monitor tool

while true; do
  # Connect to MOO, read inbox, clear it
  RESULT=$(python3 -c "
import socket, time, re
s = socket.socket()
try:
    s.connect(('localhost', 7777))
    s.settimeout(5)
    time.sleep(0.3)
    try: s.recv(65536)
    except: pass
    s.sendall(b'connect wizard\r\n')
    time.sleep(0.8)
    try: s.recv(65536)
    except: pass
    s.sendall(b'; msgs = #0.claude_inbox; #0.claude_inbox = {}; for m in (msgs) player:tell(\"CLAUDE_MSG:\" + m); endfor\r\n')
    time.sleep(1.0)
    d = b''
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk: break
            d += chunk
    except: pass
    out = re.sub(r'\x1b\[[0-9;]*m', '', d.decode('utf-8', errors='replace'))
    for line in out.split('\n'):
        line = line.strip()
        if line.startswith('CLAUDE_MSG:'):
            print(line[11:])
    s.close()
except Exception as e:
    pass
" 2>/dev/null)

  if [ -n "$RESULT" ]; then
    echo "$RESULT"
  fi

  sleep 5
done
