package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;


/**
 * Class representing a base node of the stream Parser and is extended by an the LogicNode, ComparisonNode
 * and ArithmeticNode.
 */
public abstract class BaseNode {
    String rawExpression;
    private int degree;

    String operation;  // can be any form of operation: logical, comparison, or arithmetic.
    BaseNode child1;  // left term of an expression
    BaseNode child2;  // right term of an expression.

    ArrayList<String> allowedKeys = new ArrayList<String>() {{
        add("name");
        add("result");
        add("time");
    }};
    String arithmeticKeyword = "result";

    /** toString-method
     * @return the node
     */
    public String toString(){
        String ch1_expr = null;
        String ch2_expr = null;
        if (this.child1 != null)
            ch1_expr = this.child1.getClass().getName() + ": \"" + this.child1.toStringSingleLine() + '"' ;
        if (this.child2 != null)
            ch2_expr = this.child2.getClass().getName() + ": \"" + this.child2.toStringSingleLine() + '"' ;
        return  "\n\t rawExpression: " + this.rawExpression +
                "\n\t maximal degree: " + this.degree +
                "\n\t main operation: " + this.operation +
                "\n\t child1: " + ch1_expr+
                "\n\t child2: " + ch2_expr;
    }
    /** toString-method, compact version for a single line
     * @return the node
     */
    public String toStringSingleLine(){
        String ch1_expr;
        String ch2_expr;
        if (this.child1 != null)
            ch1_expr = this.child1.toStringSingleLine();
        else
            return rawExpression;
        if (this.child2 != null)
            ch2_expr = this.child2.toStringSingleLine();
        else
            return rawExpression;
        return  "(" + ch1_expr + " " + this.operation + " " + ch2_expr + ")";
    }
    /**
     * Return a boolean expression whether the jsonInput is evaluated by the expression as true or false
     * This works by traversing the Nodes recursively to the comparision leaf nodes.
     * @return boolean expression
     */
    public abstract boolean evaluate(JsonObject jsonInput) throws StreamSQLException;

    /**
     * Return the result of an arithmetic expression, by recursively calling this function until the leaf nodes yield a number.
     * @return int the degree of the node
     */
    public abstract double arithmeticEvaluate(JsonObject jsonInput) throws StreamSQLException;
    /**
     * Return the degree of the node, by recursively calling the children's getDegree till leafNode with degree 0.
     * @return int the degree of the node
     */
    public abstract int getDegree();    /**
     * Return the degree of the node, by recursively calling the children's getDegree till leafNode with degree 0.
     */
    public void setDegree(int degree) {
        this.degree = degree;
    }
    /**
     * Return the outer expression that is not between brackets.
     * Remove brackets if no outer statement was found.
     * @return String of the outer expression
     */
    public static String getOuterExpr(String str) throws StreamSQLException {
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
            throw new StreamSQLException("Query is invalid, parentheses are not closing: '" + str + "'.");

        }
        if (idx <= 0) {
            // recursive call to remove outer parentheses
            if (str.startsWith("(") && str.endsWith(")")) {
                logger.debug("case idx <= idx, " + str);
                return getOuterExpr(str.substring(1, str.length()-1));
            }
            throw new StreamSQLException("Query is invalid: '" + str + "'.");
        }
        String outerString = String.valueOf(ca);
        idx = Math.min(idx, str.length()-1);
        outerString = outerString.substring(0, idx+1).replaceAll("[)]", "");
        logger.debug("outer String is: '" + outerString + "'");
        return outerString;
    }
    /**
     * Strip outer parenthesis recursively
     * Remove brackets and strip the expression if no outer statement was found.
     * @return Cleaned expression String
     */
    public static String strip(String str) {
        str = str.trim();
        if (str.charAt(0) == '(' && str.charAt(str.length()-1) == ')')  // trim  '(' and ')' for split
            return strip(str.substring(1, str.length()-1).trim());
        return str;
    }

    public static Logger logger = LoggerFactory.getLogger(BaseNode.class);
}
