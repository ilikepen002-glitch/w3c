import java.nio.file.Path;

/** Query Grill's installed public API, without assuming its source checkout matches the installed jar. */
public final class ProbeCompilerLaunch {
    public static void main(String[] args) throws Exception {
        Class<?> manager = Class.forName("global.InstallationManager");
        Object instance = manager.getField("INSTANCE").get(null);
        String[] command = (String[]) manager.getMethod("compilerLaunchCommand", String[].class)
            .invoke(instance, (Object) new String[]{"-version"});
        Path expected = Path.of(args[0]).toRealPath();
        if (command.length != 4 || !command[1].equals("-jar")
            || !Path.of(command[2]).toRealPath().equals(expected)
            || !Path.of(command[0]).isAbsolute() || !java.nio.file.Files.isRegularFile(Path.of(command[0]))) {
            throw new IllegalStateException("Grill selected an unexpected compiler/runtime: " + java.util.Arrays.toString(command));
        }
        System.out.println("Grill compiler verified: " + command[2]);
    }
}
