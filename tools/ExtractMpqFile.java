import java.io.File;
import java.nio.charset.StandardCharsets;
import systems.crigges.jmpq3.JMpqEditor;

public class ExtractMpqFile {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("Usage: ExtractMpqFile <mapfile> <mpq-path>");
            System.exit(1);
        }

        File mapFile = new File(args[0]);
        String mpqPath = args[1];

        try (JMpqEditor editor = new JMpqEditor(mapFile)) {
            byte[] bytes = editor.extractFileAsBytes(mpqPath);
            System.out.print(new String(bytes, StandardCharsets.UTF_8));
        }
    }
}
