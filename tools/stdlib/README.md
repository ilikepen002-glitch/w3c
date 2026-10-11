# Locked legacy damage-engine source

The map uses an independently maintained Git checkout on E: for its pre-1.29
standard library. The unmodified upstream engine mistakes concurrent pending
damage for recursion (reproduced with 50 real Bladestorm victims, TEST-0722).
`damage-causal-depth.patch` fixes causal depth and restores the deferred damage
context. It retains the recursion limit of 48 and the public API.

`lock.json` identifies the upstream base and exact fixed Git tree. The reference
commit is provenance, not a reproducibility requirement: rebuilding a commit at
a different time changes its SHA but must produce the same tree. Upstream
license and history are retained in the independent checkout. No generated
dependency file is edited by hand.

The existing Grill 1.4 supports cloning this committed local Git repository via
`file:///E:/WurstToolchain/WurstStdlib2-source:pre1.29`. It does not support the
newer live-directory dependency feature. Commit source edits before installing.
The map's compiler/check/build wrapper verifies both the source tree and the
installed dependency tree, with clean working directories, before compiling.
It fails on missing or changed content and never resets either checkout.

## First preparation on this machine

Use an absent destination; do not overwrite an existing checkout. Clone upstream
to the path in `lock.json`, check out `baseCommit` on the existing `pre1.29` branch,
apply the patch with `git apply --check` followed by `git apply`, and commit it.
Check `git rev-parse HEAD^{tree}` against `fixedTree`. The installed source
checkout was prepared this way; its reference commit is recorded in the lock.

From the map repository run `tools\Run-Grill.bat install` to have Grill install
the committed source through its normal dependency manager. Then run
`powershell -NoProfile -File tools\Verify-StdlibSource.ps1`, followed by the normal
`tools\Run-WurstChecks.bat` and `build-and-deploy-test-map.bat` workflows.

If GitHub needs this machine's proxy, use Git's per-command
`-c http.proxy=http://127.0.0.1:7890`. No global Git or Java settings are changed.
The absolute E: path is an explicit machine prerequisite. Do not silently fall
back to the unfixed upstream copy if that drive or source is unavailable.

The maintained source is based on
https://github.com/wurstscript/WurstStdlib2/commit/6604e4a9b04bce1ff723a2b81eb90a1dd7c0c25f.
