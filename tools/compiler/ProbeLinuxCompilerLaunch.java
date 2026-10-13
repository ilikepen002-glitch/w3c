import java.nio.file.Files;
import java.nio.file.Path;

/** The Linux profile must use this JDK, not another absolute executable or PATH java. */
public final class ProbeLinuxCompilerLaunch {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) { throw new IllegalArgumentException("Expected compiler jar and JDK java"); }
        Class<?> manager = Class.forName("global.InstallationManager");
        Object instance = manager.getField("INSTANCE").get(null);
        String[] command = (String[]) manager.getMethod("compilerLaunchCommand", String[].class)
            .invoke(instance, (Object) new String[]{"-version"});
        if (command.length != 4 || !command[1].equals("-jar") || !command[3].equals("-version")
            || !Path.of(command[0]).isAbsolute() || !Files.isRegularFile(Path.of(command[0]))
            || !Files.isExecutable(Path.of(command[0]))
            || !Path.of(command[0]).toRealPath().equals(Path.of(args[1]).toRealPath())
            || !Path.of(command[2]).toRealPath().equals(Path.of(args[0]).toRealPath())) {
            throw new IllegalStateException("Unexpected compiler/runtime: " + java.util.Arrays.toString(command));
        }
        System.out.println("Linux compiler launch verified: " + java.util.Arrays.toString(command));
    }
}
