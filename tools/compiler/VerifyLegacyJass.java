import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import systems.crigges.jmpq3.JMpqEditor;
import systems.crigges.jmpq3.MPQOpenOption;

/** Fail closed on the script actually packaged in the final MPQ. Never rewrite emitted Jass. */
public final class VerifyLegacyJass {
    private static final Pattern FUNCTIONS = Pattern.compile("(?ms)^function\\s+(\\w+)\\b(.*?)^endfunction\\s*$");
    // Match the complete function, not a safe-looking fragment inside an unsafe function.
    private static final Pattern ALLOCATOR = Pattern.compile(
        "\\s+takes\\s+(?:nothing|string\\s+\\w+)\\s+returns\\s+integer\\s+"
        + "local\\s+integer\\s+(?<id>\\w+)\\s+"
        + "(?<push>set\\s+wurst_stack\\[wurst_stack_depth\\]\\s*=\\s*\\w+\\s+"
        + "set\\s+wurst_stack_depth\\s*=\\s*wurst_stack_depth\\s*\\+\\s*1\\s+)?"
        + "if\\s+(?<free>\\w+)\\s*==\\s*0\\s+then\\s+"
        + "if\\s+(?<max>\\w+)\\s*<\\s*(?:8191|JASS_MAX_ARRAY_SIZE\\s*-\\s*1)\\s+then\\s+"
        + "set\\s+\\k<max>\\s*=\\s*\\k<max>\\s*\\+\\s*1\\s+"
        + "set\\s+\\k<id>\\s*=\\s*\\k<max>\\s+"
        + "(?:set\\s+(?<type>\\w+)\\[\\k<id>\\]\\s*=\\s*(?<tag>\\d+)\\s+)?else\\s+"
        + "call\\s+\\w+\\(\"Out of memory: Could not create [^\"\\r\\n]+\""
        + "(?:,\\s*(?:\"[^\"\\r\\n]*\"|\\w+))?\\)\\s+"
        + "set\\s+\\k<id>\\s*=\\s*0\\s+endif\\s+else\\s+"
        + "set\\s+\\k<free>\\s*=\\s*\\k<free>\\s*-\\s*1\\s+"
        + "set\\s+\\k<id>\\s*=\\s*\\w+\\[\\k<free>\\]\\s+"
        + "(?:set\\s+(?<freeType>\\w+)\\[\\k<id>\\]\\s*=\\s*(?<freeTag>\\d+)\\s+)?endif\\s+"
        + "(?<pop>set\\s+wurst_stack_depth\\s*=\\s*wurst_stack_depth\\s*-\\s*1\\s+)?"
        + "return\\s+\\k<id>\\s*");
    public static int verify(String script) {
        Matcher functions = FUNCTIONS.matcher(script);
        int count = 0;
        while (functions.find()) {
            String body = functions.group(2);
            if (!functions.group(1).startsWith("alloc_") && !body.contains("Out of memory: Could not create ")) { continue; }
            Matcher allocator = ALLOCATOR.matcher(body);
            if (!allocator.matches() || (allocator.group("push") == null) != (allocator.group("pop") == null)) {
                throw new IllegalStateException("Unknown/unsafe allocator: " + functions.group(1));
            }
            // Tree shaking can remove an unread typeId array. Only both writes absent, or the same two writes, are safe.
            if (!java.util.Objects.equals(allocator.group("type"), allocator.group("freeType"))
                || !java.util.Objects.equals(allocator.group("tag"), allocator.group("freeTag"))) {
                throw new IllegalStateException("Mismatched type-id branches: " + functions.group(1));
            }
            count++;
        }
        if (count == 0) { throw new IllegalStateException("No recognizable class allocators in packaged war3map.j"); }
        if (Pattern.compile("JASS_MAX_ARRAY_SIZE\\s*-\\s*1").matcher(script).find()) {
            Matcher assignments = Pattern.compile("(?m)^\\s*(?:(?:constant\\s+)?integer|set)\\s+JASS_MAX_ARRAY_SIZE\\s*=\\s*([^\\r\\n]+)").matcher(script);
            int initialized = 0;
            while (assignments.find()) {
                String value = assignments.group(1).trim();
                if (value.equals("8192")) { initialized++; }
                else if (!value.equals("0")) { throw new IllegalStateException("Unsafe target capacity assignment: " + value); }
            }
            // The compiler leaves game-supplied common.j globals as exact declaration comments.
            // Run-Grill also verifies the pinned common.j capacity before compilation.
            Matcher external = Pattern.compile("(?m)^// integer JASS_MAX_ARRAY_SIZE\\s*=\\s*8192\\s*$").matcher(script);
            while (external.find()) { initialized++; }
            if (initialized != 1) { throw new IllegalStateException("Target array capacity must be initialized to 8192 exactly once"); }
        }
        return count;
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 1) { throw new IllegalArgumentException("Usage: VerifyLegacyJass <final-map.w3x>"); }
        String script;
        File map = new File(args[0]);
        byte[] before = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(map.toPath()));
        try (JMpqEditor mpq = new JMpqEditor(map, MPQOpenOption.READ_ONLY)) {
            script = new String(mpq.extractFileAsBytes("war3map.j"), StandardCharsets.UTF_8);
        }
        byte[] after = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(map.toPath()));
        if (!Arrays.equals(before, after)) { throw new IllegalStateException("Artifact gate modified its input map"); }
        System.out.println("Legacy Jass artifact gate PASS: " + verify(script) + " allocators in " + args[0]);
    }
}
