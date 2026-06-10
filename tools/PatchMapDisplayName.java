import java.io.File;
import java.nio.file.Files;
import net.moonlightflower.wc3libs.bin.app.W3I;
import systems.crigges.jmpq3.JMpqEditor;

public class PatchMapDisplayName {
    private static final String BASE_NAME = "\u6DF1\u6E0A\u5B88\u671B";

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("Usage: PatchMapDisplayName <mapfile> <HHmm>");
            System.exit(1);
        }

        File mapFile = new File(args[0]);
        String timestamp = args[1];
        String displayName = BASE_NAME + " " + timestamp;

        W3I w3i = W3I.ofMapFile(mapFile);
        w3i.setMapName(displayName);

        W3I.LoadingScreen loadingScreen = w3i.getLoadingScreen();
        if (loadingScreen != null) {
            loadingScreen.setTitle(displayName);
            w3i.setLoadingScreen(loadingScreen);
        }

        File tempW3i = File.createTempFile("war3map", ".w3i");
        try {
            w3i.write(tempW3i);
            try (JMpqEditor editor = new JMpqEditor(mapFile)) {
                editor.insertFile("war3map.w3i", tempW3i, true);
            }
        } finally {
            Files.deleteIfExists(tempW3i.toPath());
        }

        W3I patched = W3I.ofMapFile(mapFile);
        System.out.println("Patched map name: " + patched.getMapName());
        if (patched.getLoadingScreen() != null) {
            System.out.println("Patched loading title: " + patched.getLoadingScreen().getTitle());
        }
    }
}
