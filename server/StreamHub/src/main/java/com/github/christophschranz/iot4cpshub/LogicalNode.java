package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;


/**
 * Class representing a LogicalNode of the stream Parser that is represented by an unary or binary logic operation and
 * two children that are either two LogicalNodes or one ComparisonNode.
 * A LogicalNode is either: TRUE, FALSE, or an abstract proposition of the form: [left_term] [operation] [right_term],
 * where the operations "XOR", "OR", "AND" and "NOT" are implemented and hierarchical ranked in the given order.
 * Note that "NOT" is the only unary operation, where child2 is set to TRUE and the operation to XOR
 */
public class LogicalNode extends BaseNode {
//    inherited variables and methods:
//    // variables or BaseNode
//    String rawExpression;
//    int degree;
//    boolean isLeaf;
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

    String expressionType;  // expressionType is either proposition, comparision, negation, variable
    boolean logicalValue;


    /**
     * Initializes a new LogicalNode. Take a string expression and build the operator and children.
     * @param str String expression that describes an comparison operation
     */
    public LogicalNode(String str) {
        super();
        // remove recursively outer brackets and trim spaces
        this.rawExpression = str = strip(str);
        
        // extract the outer logic operator. First iterate through the expr
        String outer_str = getOuterExpr(str);

        this.expressionType = "proposition";
        // select the main operation of the abstract proposition, if there isn't any, it must be a logical variable
        if (outer_str.contains(" XOR "))
            super.operation = "XOR";
        else if (outer_str.contains(" OR "))
            super.operation = "OR";
        else if (outer_str.contains(" AND "))
            super.operation = "AND";
        else if (outer_str.contains("NOT ")) {  // left bound may not exist in unary operation
//            super.operation = "XOR";  // operation is set to XOR such that child1 XOR TRUE equals NOT child1
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
        if (this.expressionType.equals("proposition")) {
            String expr1 = str.substring(0, str.indexOf(" " + super.operation + " ")).trim();
            this.child1 = new LogicalNode(expr1);

            String expr2 = str.substring(
                    str.indexOf(" " + super.operation + " ")+super.operation.length()+2).trim();
            this.child2 = new LogicalNode(expr2);
        }
        // "NOT" is an unary operation, where child2 is set to TRUE and the operation to XOR
        else if (this.expressionType.equals("negation")) {
            System.out.println("building negation");
            String expr1 = str.substring(str.indexOf("NOT ") + "NOT ".length()).trim();
            System.out.println(expr1);
            this.child1 = new LogicalNode(expr1);
        }
        else if (this.expressionType.equals("comparision")) {
            this.child1 = new ComparisonNode(str);
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

    public boolean evaluate(JsonObject jsonInput) {
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
        logger.error("Exception for expressionType " + this.expressionType + " in Node: " + this.toString());
        System.out.println(this.child1.child1.toString());
        System.exit(33);
        return false;
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
}
