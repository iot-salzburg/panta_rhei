package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


/**
 * Class representing a LogicalNode of the stream Parser that is represented by an unary or binary logic operation and
 * two children that are either two LogicalNodes or one ComparisonNode.
 * A LogicalNode is either: TRUE, FALSE, or an abstract proposition of the form: [left_term] [operation] [right_term],
 * where the operations "XOR", "OR", "AND" and "NOT" are implemented and hierarchical ranked in the given order.
 * Note that "NOT" is the only unary operation, where child2 is set to TRUE and the operation to XOR
 *     inherited variables and methods:
 *     // variables or BaseNode
 *     String rawExpression;
 *     int degree;
 *     String operation;  // can be any form of operation: logical, comparison, or arithmetic.
 *     BaseNode child1;  // left term of an expression
 *     BaseNode child2;  // right term of an expression.
 *     ArrayList<String> allowedKeys = new ArrayList<String>() {{
 *         add("name");
 *         add("result");
 *         add("time");
 *     }};
 *     // methods:
 *     public String toString();
 *     public abstract boolean evaluate(JsonObject jsonInput);
 *     public abstract int getDegree();
 *     public static String getOuterExpr(String str);
 *     public static String strip(String str);
 *     public static Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);
 */
public class LogicalNode extends BaseNode {
    String expressionType;  // expressionType is either proposition, comparision, negation, variable
    boolean logicalValue;


    /**
     * Initializes a new LogicalNode. Take a string expression and build the operator and children.
     * @param str String expression that describes an comparison operation
     */
    public LogicalNode(String str) throws StreamSQLException {
        super();
        // remove recursively outer brackets and trim spaces
        this.rawExpression = strip(str);
        
        // extract the outer logic operator. First iterate through the expr
        String outer_str = getOuterExpr(this.rawExpression);

        this.expressionType = "proposition";
        // select the main operation of the abstract proposition, if there isn't any, it must be a logical variable
        if (outer_str.contains(" XOR "))
            super.operation = "XOR";
        else if (outer_str.contains(" OR "))
            super.operation = "OR";
        else if (outer_str.contains(" AND "))
            super.operation = "AND";
        else if (outer_str.contains("NOT ")) {  // left bound may not exist in unary operation
            super.operation = this.expressionType = "negation";
        }

        // the expression must be a logical Variable, as a ComparisonNode or TRUE rsp. FALSE
        // test if the outer_str is a logicalVariable instead of an abstract proposition
        // set TRUE, FALSE and "" that is mapped to TRUE (for not operation)
        // if the input is empty, a logical true may be useful
        else if (outer_str.equals("TRUE") || outer_str.equals("")) {
            this.logicalValue = true;
            super.operation = "logical TRUE";  // operation is set to AND such that child1 AND TRUE equals child1
            this.expressionType = "variable";
        }
        else if (outer_str.equals("FALSE")) {
            this.logicalValue = false;
            super.operation = "logical FALSE";  // operation is set to AND such that child1 AND TRUE equals child1
            this.expressionType = "variable";
        }
        else {
            super.operation = "refer to comparison";
            this.expressionType = "comparision";
        }

        // create the child nodes that are LogicalNodes if they are not variables
        switch (this.expressionType) {
            case "proposition": {
                String expr1 = this.rawExpression.substring(0,
                        this.rawExpression.indexOf(" " + super.operation + " ")).trim();
                this.child1 = new LogicalNode(expr1);
                String expr2 = this.rawExpression.substring(
                        this.rawExpression.indexOf(" " + super.operation + " ") + super.operation.length() + 2).trim();
                this.child2 = new LogicalNode(expr2);
                break;
            }
            // "NOT" is an unary operation, where child2 is set to TRUE and the operation to XOR
            case "negation": {
                String expr1 = this.rawExpression.substring(this.rawExpression.indexOf("NOT ") + "NOT ".length()).trim();
                this.child1 = new LogicalNode(expr1);
                break;
            }
            case "comparision":
                this.child1 = new ComparisonNode(this.rawExpression);
                break;
        }
        // logical variables are evaluated directly

        super.setDegree(this.getDegree());
    }

    /** toString-method
     * @return the LogicalNode that is the class and the toString method from the base class
     */
    public String toString(){
        return "\tNode:" + "\n\t Class: " + getClass().getName() + super.toString();
    }

    /**
     * Return a boolean expression whether the jsonInput is evaluated by the expression as true or false
     * This works by traversing the Nodes recursively to the comparision leaf nodes.
     * @return boolean expression
     */
    public boolean evaluate(JsonObject jsonInput) throws StreamSQLException {
        logger.info("Check the logical expression '" + this.rawExpression + "'.");
        switch (this.expressionType) {
            case "proposition":
                if (super.operation.equals("XOR"))
                    return (child1.evaluate(jsonInput) ^ child2.evaluate(jsonInput));
                if (super.operation.equals("OR"))
                    return (child1.evaluate(jsonInput) || child2.evaluate(jsonInput));
                if (super.operation.equals("AND"))
                    return (child1.evaluate(jsonInput) && child2.evaluate(jsonInput));
                break;
            case "negation":
                return (!child1.evaluate(jsonInput));
            case "comparision":
                return child1.evaluate(jsonInput);
            case "variable":
                return this.logicalValue;  // logicalValue is either true or false
        }
        throw new StreamSQLException("Exception for expressionType " + this.expressionType +
                " in Node: " + this.toString());
    }

    @Override
    public double arithmeticEvaluate(JsonObject jsonInput) {
        return 0;
    }

    /**
     * Return the degree of the node, by recursively calling the children's getDegree till leafNode with degree 0.
     * @return int the degree of the node
     */
    public int getDegree() {
        // expressionType is either a proposition, a comparision, negation or variable
        switch (this.expressionType) {
            case "proposition":
                return Math.max(this.child1.getDegree(), this.child2.getDegree()) + 1;
            case "comparision":
            case "negation":
                return this.child1.getDegree() + 1;
        }
        return 0;
    }

    public static Logger logger = LoggerFactory.getLogger(LogicalNode.class);
}
