import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import net.moonlightflower.wc3libs.bin.app.MapFlag;
import net.moonlightflower.wc3libs.bin.app.W3I;
import systems.crigges.jmpq3.JMpqEditor;

/** Exercises the real patcher and MPQ/W3I APIs on disposable map copies. */
public class PatchMapDisplayNamePreviewFlagTest {
    private static void replaceInfo(File map, W3I info, Path directory) throws Exception {
        Path temp = Files.createTempFile(directory, "flag-fixture-", ".w3i");
        try {
            info.write(temp.toFile());
            try (JMpqEditor editor = new JMpqEditor(map)) {
                editor.insertFile("war3map.w3i", temp.toFile(), true);
            }
        } finally {
            Files.deleteIfExists(temp);
        }
    }

    private static byte[] encoded(W3I info, Path directory) throws Exception {
        Path temp = Files.createTempFile(directory, "flag-readback-", ".w3i");
        try {
            info.write(temp.toFile());
            return Files.readAllBytes(temp);
        } finally {
            Files.deleteIfExists(temp);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("Usage: PatchMapDisplayNamePreviewFlagTest <baseline-map> <temporary-directory>");
        }
        Path source = Path.of(args[0]), directory = Path.of(args[1]);
        Files.createDirectories(directory);
        int[] values = {0, 1, 0x10, 0x11, 56433, 0x4001, 0x40010011, 0x8000DC71, 0xFFFFFFFF};
        String timestamp = "20261012-2359-UTC+8";
        for (int flags : values) {
            Path copy = Files.createTempFile(directory, "preview-flag-", ".w3x");
            try {
                Files.copy(source, copy, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                W3I fixture = W3I.ofMapFile(copy.toFile());
                fixture.setFlags(W3I.Flags.valueOf(flags));
                replaceInfo(copy.toFile(), fixture, directory);
                if (W3I.ofMapFile(copy.toFile()).getFlags().toInt() != flags) {
                    throw new AssertionError("Fixture flags failed to round-trip");
                }
                PatchMapDisplayName.main(new String[]{copy.toString(), timestamp});
                W3I first = W3I.ofMapFile(copy.toFile());
                int expected = flags & ~0x0001;
                if (first.getFlags().toInt() != expected || first.getFlag(MapFlag.HIDE_MINIMAP)) {
                    throw new AssertionError("Patcher must clear only bit 0x0001: " + Integer.toHexString(flags));
                }
                fixture.setFlags(W3I.Flags.valueOf(expected));
                fixture.setMapName(first.getMapName());
                if (fixture.getLoadingScreen() != null) {
                    fixture.getLoadingScreen().setTitle(first.getLoadingScreen().getTitle());
                }
                byte[] expectedInfo = encoded(fixture, directory), firstInfo = encoded(first, directory);
                if (!Arrays.equals(expectedInfo, firstInfo)) {
                    throw new AssertionError("Patcher changed another W3I field");
                }
                PatchMapDisplayName.main(new String[]{copy.toString(), timestamp});
                W3I second = W3I.ofMapFile(copy.toFile());
                if (!Arrays.equals(firstInfo, encoded(second, directory))) {
                    throw new AssertionError("Patcher is not idempotent");
                }
                System.out.printf("PASS flags=0x%08x -> 0x%08x; other fields preserved; idempotent%n", flags, expected);
            } finally {
                Files.deleteIfExists(copy);
            }
        }
        System.out.println("PASS: all " + values.length + " real Java/API flag cases");
    }
}
