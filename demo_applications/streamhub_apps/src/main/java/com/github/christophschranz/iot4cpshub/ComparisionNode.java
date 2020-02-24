package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import java.util.ArrayList;


/**
 * Class representing a node of the stream Parser and is represented by an logic operation and two children
 * that are LogicNodes or ComparisonNodes.
 */
public class ComparisionNode {
    String rawExpression;
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
        return "ComparisonNode: " +
                "\n\trawExpression: " + this.rawExpression +
                "\n\tcomparisonOperation: " + this.comparisonOperation +
                "\n\texprKey: " + this.exprKey +
                "\n\tstrValue: " + this.strValue + " \tdblValue: " + this.dblValue;
    }

    /**
     * Initializes a new LogicNode. Take a string expression and build the operator and children
     * @param str String expression that describes an comparison operation
     */
    public ComparisionNode(String str) {
        this.rawExpression = str;

        // extract the operator
        String operator = "=";
        if (str.contains("=")) {
            operator = "=";
            this.comparisonOperation = "==";
        }
        else if (str.contains("<"))
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
            }
            else {
                System.out.println("the expression key is not valid ['name', 'result' or 'time'] " + this.rawExpression);
                System.exit(12);
            }
        }
        // check the class of the value and save as String or double value
        if (rawValue.contains("'")) {
            this.stringOperation = true;
            this.strValue = rawValue.replaceAll("'","");
        }
        else {
            this.stringOperation = false;
            this.dblValue = Double.parseDouble(rawValue);
        }
    }


    /**
     * Return a boolean expression whether the expression of the comparison expression is true or false
     * @return boolean expression
     */
    public boolean isTrue(JsonObject jsonInput) {
        System.out.println("Check if a comparison is true, jsonInput: " + jsonInput);

        if (stringOperation) {
            String dataValue = jsonInput.get(exprKey).getAsString();
            System.out.println("dataValue: " + dataValue);
            System.out.println("strValue: " + strValue);

            if (comparisonOperation.equals("=="))
                return dataValue.equals(strValue);
            if (comparisonOperation.equals("<"))
                return this.interchanged ^ dataValue.compareTo(strValue) < 0;
            if (comparisonOperation.equals(">"))
                return this.interchanged ^ dataValue.compareTo(strValue) > 0;
        }
        else {
            double dataValue = jsonInput.get(exprKey).getAsDouble();
            if (comparisonOperation.equals("=="))
                return dataValue == dblValue;
            if (comparisonOperation.equals("<"))
                return this.interchanged ^ dataValue < dblValue;  // invert if the order of the expr is interchanged
            if (comparisonOperation.equals(">"))
                return this.interchanged ^ dataValue > dblValue;
        }
        System.out.println("Exception in Node: " + this.toString());
        return false;
    }
}
