package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;


/**
 * Class representing a ComparisionNode of the stream Parser that is represented by an binary comparision of two
 * ArithmeticNodes.
 */
public class ComparisonNode extends BaseNode {
//    inherited variables and methods:
//    // variables or BaseNode
//    String rawExpression;
//    int degree;
//    String operation;  // can be any form of operation: logical, comparison, or arithmetic.
//    BaseNode child1;  // left term of an expression
//    BaseNode child2;  // right term of an expression.
//    // methods:
//    public String toString();
//    public abstract boolean evaluate(JsonObject jsonInput);
//    public abstract int getDegree();
//    public static String getOuterExpr(String str);
//    public static String strip(String str);
//    public static Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);

    boolean stringOperation;
    String exprKey;
    String strValue;
    double dblValue;
    boolean interchanged;

    /**
     * Initializes a new ComparisionNode. Take a string expression and build the operator and children
     * @param str String expression that describes an comparison operation
     */
    public ComparisonNode(String str) {
        super();
        // remove recursively outer brackets and trim spaces
        this.rawExpression = str = strip(str);

        // extract the outer logic operator. First iterate through the expr
        String outer_str = getOuterExpr(str);

        // extract the comparision operator else
        String operator = " = ";
        if (outer_str.contains(" = ")) {
            operator = " = ";
            this.operation = "==";
        } else if (outer_str.contains(" < ")) {
            operator = " < ";
            this.operation = "<";
        }
        else if (outer_str.contains(" > ")) {
            operator = " > ";
            this.operation = ">";
        }
        else if (outer_str.contains(" <> ")) {
            operator = " <> ";
            this.operation = "<>";
        }
        else {
            BaseNode.logger.error("couldn't find operator for string expr. " + this.rawExpression);
            System.exit(41);
        }

        // extract both children, convert the correct object. (the one must match 'name', 'result' or 'time'
        this.exprKey = str.substring(0, str.indexOf(operator)).trim();
        String rawValue = str.substring(str.indexOf(operator) + operator.length()).trim();

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
                BaseNode.logger.error("the expression is not valid for keys ['name', 'result' or 'time'], syntax error near '"
                        + this.rawExpression + "'.");
                System.exit(42);
            }
        }
        // check the class of the value and save as String or double value
        if (rawValue.contains("'")) {
            this.stringOperation = true;
            this.strValue = rawValue.replaceAll("'", "");
        } else {
            // the strValue is an arithmetic expression that is build in the child Node
            this.stringOperation = false;
            this.child2 = new ArithmeticNode(rawValue);
            this.dblValue = child2.arithmeticEvaluate();
        }
        super.setDegree(this.getDegree());
    }

    /** toString-method
     * @return the ComparisonNode that is the class and the toString method from the base class
     */
    public String toString(){
        return "\tNode:" + "\n\t Class: " + getClass().getName() + super.toString();
    }

    /**
     * Return a boolean expression whether the jsonInput is evaluated by the expression as true or false
     * This works by traversing the Nodes recursively to the comparision leaf nodes.
     * @return boolean expression
     */
    public boolean evaluate(JsonObject jsonInput) {
        BaseNode.logger.info("Checking the comparison '" + this.rawExpression + "'.");

        if (stringOperation) {
            String dataValue = jsonInput.get(exprKey).getAsString();
            if (operation.equals("=="))
                return dataValue.equals(strValue);
            if (operation.equals("<>"))
                return !dataValue.equals(strValue);
            if (operation.equals("<"))
                return this.interchanged ^ dataValue.compareTo(strValue) < 0;
            if (operation.equals(">"))
                return this.interchanged ^ dataValue.compareTo(strValue) > 0;
        } else {
            double dataValue = jsonInput.get(exprKey).getAsDouble();
            if (operation.equals("=="))
                return dataValue == dblValue;
            if (operation.equals("<"))
                return this.interchanged ^ dataValue < dblValue;  // invert if the order of the expr is interchanged
            if (operation.equals(">"))
                return this.interchanged ^ dataValue > dblValue;
        }

        BaseNode.logger.error("Exception in Node: " + this.toString());
        System.exit(43);
        return false;
    }

    @Override
    public float arithmeticEvaluate() {
        return 0;
    }

    /**
     * Return the degree of the node, by recursively calling the children's getDegree till leafNode with degree 0.
     * @return int the degree of the node
     */
    public int getDegree() {
        int degree = 1;
        if (this.child1 != null)
            degree = this.child1.getDegree();
        if (this.child2 != null)
            degree = Math.max(degree, this.child2.getDegree());

        return degree;  // as this is the leaf if no ArithmeticNode exists
//        if (this.isLeaf)
//            return 0;
//        else
//            return Math.max(this.child1.getDegree(), this.child2.getDegree()) + 1;
    }

}
