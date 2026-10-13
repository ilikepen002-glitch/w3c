import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;
import net.moonlightflower.wc3libs.antlr.JassLexer;
import net.moonlightflower.wc3libs.antlr.JassParser;

// Read-only independent JASS syntax evidence, using wc3libs rather than Python AST.
// Expressions are copied from packaged JASS, then inputs/helpers replaced by
// their documented constant values. The parser, not this evaluator, groups operators.
class VerifyJassBooleanGrouping {
    static Object evaluate(ParseTree tree) {
        int n = tree.getChildCount();
        if (n == 0) {
            String value = tree.getText();
            if (value.equals("true")) return true;
            if (value.equals("false")) return false;
            return Integer.valueOf(value);
        }
        if (n == 1) return evaluate(tree.getChild(0));
        if (n == 2 && tree.getChild(0).getText().equals("not"))
            return !(Boolean)evaluate(tree.getChild(1));
        if (n == 3) {
            if (tree.getChild(0).getText().equals("(")) return evaluate(tree.getChild(1));
            String op = tree.getChild(1).getText();
            Object a = evaluate(tree.getChild(0)), b = evaluate(tree.getChild(2));
            return switch (op) {
                case "or" -> (Boolean)a || (Boolean)b;
                case "and" -> (Boolean)a && (Boolean)b;
                case "!=" -> !a.equals(b);
                case "==" -> a.equals(b);
                case ">=" -> (Integer)a >= (Integer)b;
                case "<=" -> (Integer)a <= (Integer)b;
                case ">" -> (Integer)a > (Integer)b;
                case "<" -> (Integer)a < (Integer)b;
                default -> throw new IllegalArgumentException("Unsupported operator " + op);
            };
        }
        throw new IllegalArgumentException("Unsupported node: " + tree.getText());
    }
    static void prove(String label, String expression, boolean expected) {
        var tokens = new CommonTokenStream(new JassLexer(CharStreams.fromString(expression)));
        var parser = new JassParser(tokens);
        var tree = parser.bool_expr();
        if (parser.getNumberOfSyntaxErrors() != 0 || tokens.LA(1) != Token.EOF)
            throw new IllegalArgumentException("JASS did not parse the entire expression");
        boolean actual = (Boolean)evaluate(tree);
        System.out.println(label + " => " + actual + " | " + expression);
        if (actual != expected) throw new AssertionError(label);
        System.out.println("PARSE: " + tree.toStringTree(parser));
    }
    public static void main(String[] args) {
        System.out.println("Independent parser: " + JassParser.class.getName());
        System.out.println("Conjunct token=" + JassParser.BOOL_OP_CONJUNCT + "; disjunct token=" + JassParser.BOOL_OP_DISJUNCT);
        prove("HOST compiled skill10, split=false, corpse=false", "10 != 9 or false and 10 != 10 or false", true);
        prove("HOST intended same inputs", "(10 != 9 or false) and (10 != 10 or false)", false);
        prove("HOST compiled skill9, split=false, corpse=true", "9 != 9 or false and 9 != 10 or true", true);
        prove("HOST intended same inputs", "(9 != 9 or false) and (9 != 10 or true)", false);
        prove("SKILL compiled slot1 skill0 unused no-active", "(not true) and 1 != 1 or false and (not false) or (not false)", true);
        prove("SKILL intended same inputs", "(not true) and (1 != 1 or false) and ((not false) or (not false))", false);
        prove("SKILL compiled slot2 skill13 unused already-active", "(not false) and 2 != 1 or true and (not true) or (not true)", true);
        prove("SKILL intended same inputs", "(not false) and (2 != 1 or true) and ((not true) or (not true))", false);
        prove("GUARD compiled failed outer check, matching wave", "false and 0 == 0 or 4 == 4", true);
        prove("GUARD intended failed outer check, matching wave", "false and (0 == 0 or 4 == 4)", false);
        System.out.println("PASS: Five paired counterexamples differ under independent wc3libs JASS grammar; no Python expression parser used.");
    }
}
