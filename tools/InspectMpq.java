import java.io.File;
import systems.crigges.jmpq3.JMpqEditor;

public class InspectMpq {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: InspectMpq <mapfile>");
            System.exit(1);
        }

        try (JMpqEditor editor = new JMpqEditor(new File(args[0]))) {
            System.out.println("has war3map.w3i: " + editor.hasFile("war3map.w3i"));
            System.out.println("visible files:");
            for (String name : editor.getFileNames()) {
                System.out.println("  " + name);
            }
        }
    }
}
