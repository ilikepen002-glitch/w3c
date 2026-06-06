import java.io.File;
import java.nio.file.Files;
import net.moonlightflower.wc3libs.bin.app.MapFlag;
import net.moonlightflower.wc3libs.bin.app.W3I;
import net.moonlightflower.wc3libs.dataTypes.app.Controller;
import net.moonlightflower.wc3libs.dataTypes.app.Coords2DF;
import systems.crigges.jmpq3.JMpqEditor;

public class PatchMapSlots {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: PatchMapSlots <mapfile>");
            System.exit(1);
        }

        File mapFile = new File(args[0]);
        W3I w3i = W3I.ofMapFile(mapFile);

        while (w3i.getPlayers().size() > 2) {
            w3i.getPlayers().remove(w3i.getPlayers().size() - 1);
        }

        W3I.Player player0;
        if (w3i.getPlayers().isEmpty()) {
            player0 = new W3I.Player();
            player0.setNum(0);
            player0.setStartPos(new Coords2DF(-128f, 64f));
            w3i.addPlayer(player0);
        } else {
            player0 = w3i.getPlayers().get(0);
        }

        player0.setNum(0);
        player0.setName("Player 1");
        player0.setType(Controller.USER);

        W3I.Player player1;
        if (w3i.getPlayers().size() < 2) {
            player1 = new W3I.Player();
            w3i.addPlayer(player1);
        } else {
            player1 = w3i.getPlayers().get(1);
        }

        player1.setNum(1);
        player1.setName("Enemy Slot");
        player1.setType(Controller.COMPUTER);
        player1.setStartPos(new Coords2DF(128f, 64f));
        player1.setStartPosFixed(0);

        w3i.clearForces();
        W3I.Force playerForce = new W3I.Force();
        playerForce.setName("Player");
        playerForce.addPlayerNums(0);
        w3i.addForce(playerForce);

        W3I.Force enemyForce = new W3I.Force();
        enemyForce.setName("Enemy");
        enemyForce.addPlayerNums(1);
        w3i.addForce(enemyForce);

        w3i.setFlag(MapFlag.USE_CUSTOM_FORCES, true);
        w3i.setFlag(MapFlag.FIXED_PLAYER_FORCE_SETTING, true);
        w3i.setFlag(MapFlag.MODIFY_ALLY_PRIORITIES, false);
        w3i.setPlayersRecommendedAmount("1");

        File tempW3i = File.createTempFile("war3map", ".w3i");
        try {
            w3i.write(tempW3i);
            W3I writtenW3i = new W3I(tempW3i);
            System.out.println("temp players=" + writtenW3i.getPlayers().size()
                + " customForces=" + writtenW3i.getFlag(MapFlag.USE_CUSTOM_FORCES)
                + " fixedForces=" + writtenW3i.getFlag(MapFlag.FIXED_PLAYER_FORCE_SETTING));
            try (JMpqEditor editor = new JMpqEditor(mapFile)) {
                editor.insertFile("war3map.w3i", tempW3i, true);
                W3I roundTrip = new W3I(editor.extractFileAsBytes("war3map.w3i"));
                System.out.println("mpq players=" + roundTrip.getPlayers().size()
                    + " customForces=" + roundTrip.getFlag(MapFlag.USE_CUSTOM_FORCES)
                    + " fixedForces=" + roundTrip.getFlag(MapFlag.FIXED_PLAYER_FORCE_SETTING));
            }
        } finally {
            Files.deleteIfExists(tempW3i.toPath());
        }
    }
}
