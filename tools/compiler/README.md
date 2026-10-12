# Legacy Jass compiler

This project uses a dedicated compiler built from WurstScript source, not a patched binary. It targets Warcraft III 1.27a's 8192 array slots and reserves object id 0, so each inheritance/closure allocation pool has 8191 usable ids. This distribution is deliberately limited to legacy Jass projects; do not select it as the global compiler or use it for modern/Lua maps.

Source checkout: `E:/WurstToolchain/WurstScript-source`, branch `codex/legacy-jass-array-capacity`, upstream baseline `82c1bd2940e5559df1cf8769cd8652e899066836`. The reviewed source patch is `legacy-jass-array-capacity.patch`. The lock records its hash and the built compiler/installed Grill jar hashes.

The old allocator looked for `JASS_MAX_ARRAY_SIZE` only after early tree shaking had removed that unread global. It then selected 32768. Pinning the target constant preserves the existing capacity path. This dedicated distribution also uses 8192 as its default and class-member multiarray dimension. The allocator compares `maxIndex < capacity - 1` before incrementing, checks the free list first, and leaves allocation state unchanged on exhaustion. Constructors return null immediately if a returning error handler permits execution to continue after allocation failure.

Build in `de.peeeq.wurstscript/` with a complete JDK 27 and the checked-in Gradle wrapper:

```powershell
$env:JAVA_HOME = 'C:/Users/huawei/.wurst/wurst-jdk'
$env:Path = "$env:JAVA_HOME/bin;$env:Path"
./gradlew.bat shadowJar test --tests tests.wurstscript.tests.LegacyJassAllocationTests -PskipErrorProne -PskipStdLibFetch -PtestForks=1 --no-daemon
```

`skipStdLibFetch` is valid for these self-contained regression programs; it does not change the map's existing standard-library lock. The tests execute emitted Jass with each standard optimization combination, including stack traces. They cover the last legal id, repeated exhaustion, returning error handlers, member initialization, inheritance, closure pools, recycling, and class-member arrays at the last id. They do not establish engine-native behavior or substitute for a real-client playtest.

If Java dependency downloads fail TLS negotiation, keep SSL verification enabled. Cache the exact pinned official Maven/JitPack artifacts using a working HTTPS client and add the local Maven cache with a temporary Gradle init script. No dependency versions or repository build source need to change. This machine's successful final command appended `--offline --init-script E:/WurstToolchain/tmp/legacy-local.init.gradle` to the command above, after the exact official dependencies had been cached. The init script only adds `file:///E:/WurstToolchain/tmp/legacy-maven` as a Maven repository in `beforeSettings` (plugin management), `settingsEvaluated` (dependency resolution), and `beforeProject` (project repositories). It makes no source or global Gradle configuration edits. The successful build log is in the source checkout's `de.peeeq.wurstscript/build-legacy.log`; six existing targeted class/closure/tree-shaker regression results are in `build-legacy-existing-tests.log`.

The custom-capacity regression supplies `JASS_MAX_ARRAY_SIZE=3` itself. Its pjass input removes that one declaration from the validator's bundled common.j to prevent a duplicate definition, preserving all other native declarations. Both transformed IM and generated Jass execute the custom target; pjass still checks every emitted optimization variant.

Install the reviewed jar:

```powershell
./tools/compiler/Install-LegacyCompiler.ps1
```

Default isolated installation: `E:/WurstToolchain/legacy-jass-8192`. Its `wurst-runtime` junction points to the existing bundled runtime. `WURST_LEGACY_INSTALL_DIR` may select another installation only if its jar matches the lock. The global compiler is untouched. `Run-Grill.bat` verifies SHA256, project JASS/v1.28 configuration, the locked stdlib's common.j capacity, and Grill's actual public `compilerLaunchCommand` before build/typecheck/test. Grill receives `-Dwurst.install.dir` to use exactly that installation.

The final-map gate runs after the display-name patch and before publishing the root map or deploying to Warcraft III. It opens the MPQ read-only, checks input SHA256 before/after reading real `war3map.j`, enumerates every `alloc_` function, and rejects unknown allocator shapes, unsafe boundaries or empty coverage. A numeric 32768 elsewhere is allowed. `VerifyLegacyJassTests` tests both safe acceptance and unsafe/unknown rejection.

Routine project validation remains `tools/Run-WurstChecks.bat` followed by `build-and-deploy-test-map.bat`. Shared staging/build validation must run serially.
