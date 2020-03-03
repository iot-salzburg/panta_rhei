package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import java.util.ArrayList;


/**
 * Class representing a node of the stream Parser and is represented by an logic operation and two children
 * that are LogicNodes or ComparisonNodes.
 */
public class Node {
    String rawExpression;
    int degree;
    boolean isLeaf;  // leaf nodes are comparison nodes

    String logicOperation;  // AND, OR, XOR
    Node child1;  // left term of an expression
    Node child2;  // right term of an expression

    String comparisonOperation; // <, >, ==. This is only if the Node is a leaf Node
    boolean stringOperation;
    String exprKey;
    String strValue;
    double dblValue;
    boolean interchanged;


    /** toString-method
     * @return the node
     */
    public String toString(){
        String ch1_expr = null;
        String ch2_expr = null;
        if (this.child1 != null)
            ch1_expr = this.child1.rawExpression;
        if (this.child1 != null)
            ch2_expr = this.child2.rawExpression;
        return "\tNode: " +
                "\n\t rawExpression: " + this.rawExpression +
                "\n\t logicOperation: " + this.logicOperation +
                "\n\t child1: '" + ch1_expr + "'" +
                "\n\t child2: '" + ch2_expr + "'" +
                "\n\t degree: " + this.degree +
                "\n\t comparisonOperation: " + this.comparisonOperation +
                "\n\t exprKey: " + this.exprKey +
                "\n\t strValue: " + this.strValue + " \tdblValue: " + this.dblValue;
    }

    /**
     * Initializes a new Node. Take a string expression and build the operator and children
     * @param str String expression that describes an comparison operation
     */
    public Node(String str) {
        str = strip(str);
        this.rawExpression = str;

        // extract the outer logic operator. First iterate through the expr
        String outer_str = getOuterExpr(str);
        if (outer_str.contains(" AND "))
            this.logicOperation = "AND";
        else if (outer_str.contains(" OR "))
            this.logicOperation = "OR";
        else if (outer_str.contains(" XOR "))
            this.logicOperation = "XOR";
        else {
            this.isLeaf = true;
        }

        // create the child nodes if not a leaf
        if (!this.isLeaf) {
            String expr1 = str.substring(0, str.indexOf(" " + this.logicOperation + " ")).trim();
            this.child1 = new Node(expr1);

            String expr2 = str.substring(
                    str.indexOf(" " + this.logicOperation + " ")+this.logicOperation.length()+2).trim();
            this.child2 = new Node(expr2);
        }
        else {
            // remove brackets
            str = str.replaceAll("[()]", "");
            this.rawExpression = str;

            // extract the comparision operator else
            String operator = "=";
            if (str.contains("=")) {
                operator = "=";
                this.comparisonOperation = "==";
            } else if (str.contains("<"))
                operator = this.comparisonOperation = "<";
            else if (str.contains(">"))
                operator = this.comparisonOperation = ">";
            else {
                System.out.println("couldn't find operator for string expr. " + this.rawExpression);
                System.exit(11);
            }

            // extract both children, convert the correct object. (the one must match 'name', 'result' or 'time'
            this.exprKey = str.substring(0, str.indexOf(operator)).trim();
            String rawValue = str.substring(str.indexOf(operator) + 1).trim();

            ArrayList<String> allowedKeys = new ArrayList<String>() {{
                add("name");
                add("result");
                add("time");
            }};
            // switch if there is a val-key pair and exit if not valid expr key is found.
            if (!allowedKeys.contains(exprKey)) {
                if (allowedKeys.contains(rawValue)) {
                    String helper = rawValue;
                    rawValue = this.exprKey;
                    this.exprKey = helper;
                    this.interchanged = true;
                } else {
                    System.out.println("the expression key is not valid ['name', 'result' or 'time'] " + this.rawExpression);
                    System.exit(12);
                }
            }
            // check the class of the value and save as String or double value
            if (rawValue.contains("'")) {
                this.stringOperation = true;
                this.strValue = rawValue.replaceAll("'", "");
            } else {
                this.stringOperation = false;
                this.dblValue = Double.parseDouble(rawValue);
            }
        }
        this.degree = this.getDegree();
    }

    /**
     * Return a boolean expression whether the expression of the comparison expression is true or false
     * or the subtree is true or false. This works by traversing the Nodes recursively to the comparision leaf nodes.
     * @return boolean expression
     */
    public boolean isTrue(JsonObject jsonInput) {
        if (this.isLeaf) {
            System.out.println("Check the comparison '" + this.rawExpression + "':");
            if (stringOperation) {
//                System.out.println("  expressionKey: " + exprKey);
//                System.out.println();
                String dataValue = jsonInput.get(exprKey).getAsString();
                if (comparisonOperation.equals("=="))
                    return dataValue.equals(strValue);
                if (comparisonOperation.equals("<"))
                    return this.interchanged ^ dataValue.compareTo(strValue) < 0;
                if (comparisonOperation.equals(">"))
                    return this.interchanged ^ dataValue.compareTo(strValue) > 0;
            } else {
                double dataValue = jsonInput.get(exprKey).getAsDouble();
                if (comparisonOperation.equals("=="))
                    return dataValue == dblValue;
                if (comparisonOperation.equals("<"))
                    return this.interchanged ^ dataValue < dblValue;  // invert if the order of the expr is interchanged
                if (comparisonOperation.equals(">"))
                    return this.interchanged ^ dataValue > dblValue;
            }
        }
        else {
            System.out.println("Check the logical statement '" + this.rawExpression + "':");
            if (logicOperation.equals("AND"))
                return (child1.isTrue(jsonInput) && child2.isTrue(jsonInput));
            if (logicOperation.equals("OR"))
                return (child1.isTrue(jsonInput) || child2.isTrue(jsonInput));
            if (logicOperation.equals("XOR"))
                return (child1.isTrue(jsonInput) ^ child2.isTrue(jsonInput));
        }
        System.out.println("Exception in Node: " + this.toString());
        return false;
    }
    /**
     * Return the outer expression that is not between brackets.
     * Remove brackets if no outer statement was found.
     * @return String of the outer expression
     */
    public static String getOuterExpr(String str) {
        str = str.trim();
        int i = 0;  // idx for str
        int idx = 0;  // idx for outerString generation
        int depth = 0;
        char[] ca = new char[str.length()];
        while (i<str.length()) {
            if (str.charAt(i) == '(')
                depth ++;
            if (str.charAt(i) == ')')
                depth--;
            if (depth == 0) {
                ca[idx] = str.charAt(i);
                idx ++;
            }
            i ++;
        }

        // correct invalid number of parentheses
        if (depth != 0) {
            if (depth >= 1 && str.charAt(0) == '(')  // trim '(' for split
                return getOuterExpr(str.substring(1));
            if (depth >= -1 && str.charAt(str.length()-1) == ')')  // trim ')' for split
                return getOuterExpr(str.substring(0, str.length()-1));
            System.out.println("Query is invalid, parentheses are not closing: " + str);
            System.exit(15);

        }
        if (idx <= 1) {
            // recursive call to remove outer parentheses
            if (str.startsWith("(") && str.endsWith(")")) {
                System.out.println("case idx <= idx, " + str);
                return getOuterExpr(str.substring(1, str.length()-1));
            }
            System.out.println("Query is invalid: " + str);
            System.exit(16);
        }
        String outerString = String.valueOf(ca);
        idx = Math.min(idx, str.length()-1);
        outerString = outerString.substring(0, idx+1).replaceAll("[)]", "");
        System.out.println(outerString);
        return outerString;
    }
    /**
     * Strip outer parenthesis
     * Remove brackets and strip the expression if no outer statement was found.
     * @return Cleaned expression String
     */
    public static String strip(String str) {
        if (str.charAt(0) == '(' && str.charAt(str.length()-1) == ')')  // trim  '(' and ')' for split
            return strip(str.substring(1, str.length()-1).trim());
        else
            return str.trim();
    }
    /**
     * Return the degree of the node, by recursively calling the children's getDegree till leafNode with degree 0.
     * @return int the degree of the node
     */
    public int getDegree() {
        if (this.isLeaf)
            return 0;
        else
            return Math.max(this.child1.getDegree(), this.child2.getDegree()) + 1;
    }
}
