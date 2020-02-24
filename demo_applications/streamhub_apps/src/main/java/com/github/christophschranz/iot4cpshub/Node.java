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
        return "Node: " +
                "\n\trawExpression: " + this.rawExpression +
                "\n\tlogicOperation: " + this.logicOperation +
                "\n\tchild1: " + this.child1 +
                "\n\tchild2: " + this.child2 +
                "\n\tdegree: " + this.degree +
                "\n\tcomparisonOperation: " + this.comparisonOperation +
                "\n\texprKey: " + this.exprKey +
                "\n\tstrValue: " + this.strValue + " \tdblValue: " + this.dblValue;
    }

    /**
     * Initializes a new LogicNode. Take a string expression and build the operator and children
     * @param str String expression that describes an comparison operation
     */
    public Node(String str) {
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
    }

    /**
     * Return a boolean expression whether the expression of the comparison expression is true or false
     * or the subtree is true or false
     * @return boolean expression
     */
    public boolean isTrue(JsonObject jsonInput) {
        if (this.isLeaf) {
            System.out.println("Check if the comparison '" + this.rawExpression + "' is true");
            System.out.println("\tjsonInput: " + jsonInput);

            if (stringOperation) {
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
            System.out.println("Check if the logical statement '" + this.rawExpression + "' is true");
            System.out.println("\tjsonInput: " + jsonInput);
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
        String outerString = "";
        if (!str.contains("("))
            return str;

        if (str.startsWith("(") && str.endsWith(")"))
            return str.substring(1, str.length()-1);
        else if (str.startsWith("(")) {
            return str.substring(str.lastIndexOf(')')+1);
        }
        else if (str.endsWith(")")) {
            return str.substring(0, str.indexOf('('));
        }
        System.out.println("unexpected exception for string: " + str);
        System.exit(13);
        return outerString;
    }
}
