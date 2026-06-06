import java.io.File;
import net.moonlightflower.wc3libs.bin.app.MapFlag;
import net.moonlightflower.wc3libs.bin.app.W3I;
import systems.crigges.jmpq3.JMpqEditor;

public class InspectW3iFromMpq {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: InspectW3iFromMpq <mapfile>");
            System.exit(1);
        }

        File mapFile = new File(args[0]);
        try (JMpqEditor editor = new JMpqEditor(mapFile)) {
            W3I w3i = new W3I(editor.extractFileAsBytes("war3map.w3i"));

            System.out.println("Map: " + mapFile.getAbsolutePath());
            System.out.println("RecommendedPlayers: " + w3i.getPlayersRecommendedAmount());
            System.out.println("Flags:");
            System.out.println("  FIXED_PLAYER_FORCE_SETTING=" + w3i.getFlag(MapFlag.FIXED_PLAYER_FORCE_SETTING));
            System.out.println("  USE_CUSTOM_FORCES=" + w3i.getFlag(MapFlag.USE_CUSTOM_FORCES));
            System.out.println("Players:");
            for (W3I.Player p : w3i.getPlayers()) {
                System.out.println(
                    "  num=" + p.getNum()
                        + " name=" + p.getName()
                        + " type=" + p.getType()
                        + " startFixed=" + p.getStartPosFixed()
                        + " startPos=" + p.getStartPos()
                );
            }
            System.out.println("Forces:");
            for (W3I.Force force : w3i.getForces()) {
                System.out.println(
                    "  name=" + force.getName()
                        + " players=" + force.getPlayerNums()
                        + " flags=" + force.getFlags()
                );
            }
        }
    }
}
