package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import org.apache.kafka.common.protocol.types.Field;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;


/**
 * Class representing the ArithmeticNode of the stream Parser and is represented by an arithmetic operation and two
 * children that are ArithmeticNodes.
 */
public class ArithmeticNode extends BaseNode {
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

    boolean isNumber = false;  // specifies if the Node represents a number or an arithmetic expression
    float number;


    /**
     * Initializes a new Node. Take a string expression and build the operator and children
     * @param str String expression that describes an arithmetic operation or number
     */
    public ArithmeticNode(String str) {
        super();
        // remove recursively outer brackets and trim spaces
        this.rawExpression = str = strip(str);

        // extract the outer logic operator. First iterate through the expr
        String outer_str = getOuterExpr(str);

        if (outer_str.contains("-"))
            this.operation = "-";
        else if (outer_str.contains("+"))
            this.operation = "+";
        else if (outer_str.contains("/"))
            this.operation = "/";
        else if (outer_str.contains("*"))
            this.operation = "*";
        else if (outer_str.contains("^"))
            this.operation = "^";
        else if (outer_str.contains("%"))
            this.operation = "%";
        else {
            this.isNumber = true;
        }

        // create the child nodes if not a leaf
        if (!this.isNumber) {  // TODO substring the string with the operation found in the OUTER_STR
            String expr1 = str.substring(0, str.indexOf(this.operation)).trim();
            this.child1 = new ArithmeticNode(expr1);

            String expr2 = str.substring(
                    str.indexOf(this.operation)+1).trim();
            this.child2 = new ArithmeticNode(expr2);
        }
        // expression is a number
        else
            try {
                this.number = Float.parseFloat(rawExpression);
            } catch (NumberFormatException e) {
                BaseNode.logger.error("Couldn't parse arithmetic expression '" + rawExpression + "'.");
                System.exit(52);
            }
        super.setDegree(this.getDegree());
    }

    /** toString-method
     * @return the ArithmeticNode that is the class and the toString method from the base class
     */
    public String toString(){
        return "\tNode:" + "\n\t Class: " + getClass().getName() + super.toString();
    }

    @Override
    public boolean evaluate(JsonObject jsonInput) {
        return false;
    }

    /**
     * Return the result of an arithmetic expression, by recursively calling this function until the leaf nodes yield a number.
     * @return int the degree of the node
     */
    public float arithmeticEvaluate() {
        // base case. The Node represents a number
        if (this.isNumber)
            return this.number;
        // recursive case. The nodes subtree must be evaluated
        switch (this.operation) {
            case "-":
                return this.child1.arithmeticEvaluate() - this.child2.arithmeticEvaluate();
            case "+":
                return this.child1.arithmeticEvaluate() + this.child2.arithmeticEvaluate();
            case "/":
                return this.child1.arithmeticEvaluate() / this.child2.arithmeticEvaluate();
            case "*":
                return this.child1.arithmeticEvaluate() * this.child2.arithmeticEvaluate();
            case "^":
                return (float) Math.pow(this.child1.arithmeticEvaluate(), this.child2.arithmeticEvaluate());
            case "%":
                return this.child1.arithmeticEvaluate() % this.child2.arithmeticEvaluate();
        }
        logger.error("Exception for operation " + this.operation + " in Node: " + this.toString());
        System.exit(53);
        return this.number;
    }

    /**
     * Return the degree of the node, by recursively calling the children's getDegree till leafNode with degree 0.
     * @return int the degree of the node
     */
    public int getDegree() {
        if (this.isNumber)
            return 0;
        else
            return Math.max(this.child1.getDegree(), this.child2.getDegree()) + 1;
    }

    public static Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);
}
