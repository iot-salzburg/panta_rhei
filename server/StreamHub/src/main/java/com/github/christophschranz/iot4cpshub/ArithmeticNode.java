package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import org.apache.kafka.common.protocol.types.Field;


/**
 * Class representing the ArithmeticNode of the stream Parser and is represented by an arithmetic operation and two
 * children that are ArithmeticNodes.
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
public class ArithmeticNode extends BaseNode {
    boolean isAtomic = false;  // specifies if the Node represents a number or an arithmetic expression
    boolean isNumber = false;
    boolean isKeyword = false;
    String keyword;
    float numberValue;
    String strValue;

    /**
     * Initializes a new Node. Take a string expression and build the operator and children
     * @param str String expression that describes an arithmetic operation or number
     */
    public ArithmeticNode(String str) throws StreamSQLException {
        super();
        // remove recursively outer brackets and trim spaces
        this.rawExpression = strip(str);

        // extract the outer logic operator. First iterate through the expr
        String outer_str = getOuterExpr(this.rawExpression);

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
            // expression is a keyword and this will be set
            if (allowedKeys.stream().anyMatch(outer_str::contains)) {
                for (String key: this.allowedKeys) {
                    if (outer_str.equals(key)) {
                        this.keyword = key;
                        this.isKeyword = true;
                    }
                }
                // exit in case that should not happen
                if (!this.isKeyword) {
                    throw new StreamSQLException("the expression is not valid for keys ['name', 'result' or 'time']," +
                            " syntax error near '" + this.rawExpression + "'.");
                }
            }
            // the expression must be a number or string and is tried to be parsed
            else {
                this.isAtomic = true;
                if (outer_str.contains("'")) {
                    this.isNumber = false;
                    this.strValue = outer_str.replaceAll("'", "");
                }
                else  {
                    try {
                        this.numberValue = Float.parseFloat(rawExpression);
                        this.isNumber = true;
                    } catch (NumberFormatException e) {
                        throw new StreamSQLException("Couldn't parse arithmetic expression '" + rawExpression + "'.");
                    }
                }
            }
        }

        // this node could be an inner node which gets two ArithmeticNodes as childs. Or a leaf node, that is either
        // a number or a keyword expression
        if (!this.isAtomic && !this.isKeyword) {
            String expr1 = this.rawExpression.substring(0, this.rawExpression.indexOf(this.operation)).trim();
            this.child1 = new ArithmeticNode(expr1);

            String expr2 = this.rawExpression.substring(this.rawExpression.indexOf(this.operation)+1).trim();
            this.child2 = new ArithmeticNode(expr2);
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
    public double arithmeticEvaluate() throws StreamSQLException {
        // for testing expressions, it is useful to call evaluation without input
        JsonObject jsonInput = new JsonObject();
        return arithmeticEvaluate(jsonInput);
    }
    public double arithmeticEvaluate(JsonObject jsonInput) throws StreamSQLException {
        // base case. The Node represents a number
        if (this.isAtomic)
            return this.numberValue;
        if (this.isKeyword) {
            return jsonInput.get(this.arithmeticKeyword).getAsDouble();  // the keyword should be result
        }
        // recursive case. The nodes subtree must be evaluated
        switch (this.operation) {
            case "-":
                return this.child1.arithmeticEvaluate(jsonInput) - this.child2.arithmeticEvaluate(jsonInput);
            case "+":
                return this.child1.arithmeticEvaluate(jsonInput) + this.child2.arithmeticEvaluate(jsonInput);
            case "/":
                return this.child1.arithmeticEvaluate(jsonInput) / this.child2.arithmeticEvaluate(jsonInput);
            case "*":
                return this.child1.arithmeticEvaluate(jsonInput) * this.child2.arithmeticEvaluate(jsonInput);
            case "^":
                return (float) Math.pow(this.child1.arithmeticEvaluate(jsonInput), this.child2.arithmeticEvaluate(jsonInput));
            case "%":
                return this.child1.arithmeticEvaluate(jsonInput) % this.child2.arithmeticEvaluate(jsonInput);
        }
        throw new StreamSQLException("Exception for operation " + this.operation + " in Node: " + this.toString());
    }

    /**
     * Return the degree of the node, by recursively calling the children's getDegree till leafNode with degree 0.
     * @return int the degree of the node
     */
    public int getDegree() {
        if (this.isAtomic || this.isKeyword)
            return 0;
        else
            return Math.max(this.child1.getDegree(), this.child2.getDegree()) + 1;
    }
}
