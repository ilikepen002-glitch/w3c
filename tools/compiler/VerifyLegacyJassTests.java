/** Narrow acceptance/rejection tests for the final-artifact gate; no map modifications. */
public final class VerifyLegacyJassTests {
    private static final String SAFE = "function alloc_A takes nothing returns integer\n"
        + "local integer this\nif freeCount == 0 then\nif maxIndex < 8191 then\n"
        + "set maxIndex = maxIndex + 1\nset this = maxIndex\nset typeId[this] = 1\nelse\n"
        + "call error(\"Out of memory: Could not create A.\")\nset this = 0\nendif\nelse\n"
        + "set freeCount = freeCount - 1\nset this = free[freeCount]\nset typeId[this] = 1\nendif\nreturn this\nendfunction\n";
    private static void reject(String script) {
        try { VerifyLegacyJass.verify(script); }
        catch (IllegalStateException expected) { return; }
        throw new AssertionError("Unsafe/unknown script was accepted");
    }
    public static void main(String[] args) {
        if (VerifyLegacyJass.verify(SAFE + "// unrelated constant 32768\n") != 1) { throw new AssertionError(); }
        reject(SAFE.replace("8191", "32768"));
        reject(SAFE.replace("8191", "8192"));
        reject(SAFE.replace("set this = 0", "set typeId[0] = 1"));
        reject(SAFE.replace("freeCount - 1", "freeCount + 1"));
        reject("function main takes nothing returns nothing\nendfunction\n");
        reject(SAFE.replace("maxIndex < 8191", "maxIndex <= 8191"));
        reject(SAFE + SAFE.replace("alloc_A", "alloc_B").replace("Out of memory:", "diagnostic removed:"));
        reject(SAFE + "function alloc_B takes nothing returns integer\nreturn 99999\nendfunction\n");
        reject(SAFE.replace("return this", "set typeId[8192] = 1\nreturn this"));
        reject(SAFE.replace("return this", "set typeId[0] = 1\nreturn this"));
        reject(SAFE.replace("if freeCount", "set maxIndex = 99999\nif freeCount"));
        reject(SAFE.replace("set this = 0", "set maxIndex = maxIndex + 1\nset this = 0"));
        String symbolic = SAFE.replace("8191", "JASS_MAX_ARRAY_SIZE - 1");
        if (VerifyLegacyJass.verify("globals\nconstant integer JASS_MAX_ARRAY_SIZE = 8192\nendglobals\n" + symbolic) != 1) { throw new AssertionError(); }
        reject(symbolic);
        reject("globals\nconstant integer JASS_MAX_ARRAY_SIZE = 32768\nendglobals\n" + symbolic);
        reject("globals\ninteger JASS_MAX_ARRAY_SIZE = 8192\nendglobals\n" + symbolic + "function corrupt takes nothing returns nothing\nset JASS_MAX_ARRAY_SIZE = 32768\nendfunction\n");
        reject("globals\nconstant integer JASS_MAX_ARRAY_SIZE = 32768\nendglobals\n" + symbolic.replace("JASS_MAX_ARRAY_SIZE - 1", "JASS_MAX_ARRAY_SIZE-1"));
        reject("globals\nconstant integer JASS_MAX_ARRAY_SIZE = 8192+100\nendglobals\n" + symbolic);
        if (VerifyLegacyJass.verify("// integer JASS_MAX_ARRAY_SIZE=8192\n" + symbolic) != 1) { throw new AssertionError(); }
        reject("// integer JASS_MAX_ARRAY_SIZE=32768\n" + symbolic);
        reject("// integer JASS_MAX_ARRAY_SIZE=8192+100\n" + symbolic);
        reject("// integer JASS_MAX_ARRAY_SIZE=8192\n" + symbolic + "function corrupt takes nothing returns nothing\nset JASS_MAX_ARRAY_SIZE = 32768\nendfunction\n");
        String noType = SAFE.replace("set typeId[this] = 1\n", "");
        if (VerifyLegacyJass.verify(noType) != 1) { throw new AssertionError(); }
        reject(SAFE.replaceFirst("set typeId\\[this\\] = 1\\n", ""));
        reject(SAFE.replace("set this = free[freeCount]\nset typeId[this] = 1", "set this = free[freeCount]"));
        System.out.println("Legacy Jass artifact gate tests PASS");
    }
}
