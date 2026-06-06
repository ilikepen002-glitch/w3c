import java.io.File;
import net.moonlightflower.wc3libs.bin.app.MapFlag;
import net.moonlightflower.wc3libs.bin.app.W3I;

public class InspectMapInfo {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: InspectMapInfo <mapfile>");
            System.exit(1);
        }

        File mapFile = new File(args[0]);
        W3I w3i = W3I.ofMapFile(mapFile);

        System.out.println("Map: " + mapFile.getAbsolutePath());
        System.out.println("Name: " + w3i.getMapName());
        System.out.println("Author: " + w3i.getMapAuthor());
        System.out.println("RecommendedPlayers: " + w3i.getPlayersRecommendedAmount());
        System.out.println("Flags:");
        System.out.println("  MELEE_MAP=" + w3i.getFlag(MapFlag.MELEE_MAP));
        System.out.println("  FIXED_PLAYER_FORCE_SETTING=" + w3i.getFlag(MapFlag.FIXED_PLAYER_FORCE_SETTING));
        System.out.println("  USE_CUSTOM_FORCES=" + w3i.getFlag(MapFlag.USE_CUSTOM_FORCES));
        System.out.println("  MODIFY_ALLY_PRIORITIES=" + w3i.getFlag(MapFlag.MODIFY_ALLY_PRIORITIES));
        System.out.println("Players:");
        for (W3I.Player p : w3i.getPlayers()) {
            System.out.println(
                "  num=" + p.getNum()
                    + " name=" + p.getName()
                    + " type=" + p.getType()
                    + " race=" + p.getRace()
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
