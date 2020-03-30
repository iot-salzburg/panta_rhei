package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;


/**
 * Class representing a ComparisionNode of the stream Parser that is represented by an binary comparision of two
 * ArithmeticNodes.
 */
public class ComparisonNode extends BaseNode {
//    inherited variables and methods:
//    // variables or BaseNode
//    String rawExpression;
//    int degree;
//    boolean isLeaf;
//    String operation;  // can be any form of operation: logical, comparison, or arithmetic.
//    BaseNode child1;  // left term of an expression
//    BaseNode child2;  // right term of an expression.
//    ArrayList<String> allowedKeys = new ArrayList<String>() {{
//        add("name");
//        add("result");
//        add("time");
//    }};
//    // methods:
//    public String toString();
//    public abstract boolean evaluate(JsonObject jsonInput);
//    public abstract int getDegree();
//    public static String getOuterExpr(String str);
//    public static String strip(String str);
//    public static Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);

    boolean stringOperation;
    String left_expr;
    String right_expr;
    double dblValue;
    boolean switchedKeySide;

    /**
     * Initializes a new ComparisionNode. Take a string expression and build the operator and children
     * @param str String expression that describes an comparison operation
     */
    public ComparisonNode(String str) {
        super();
        // remove recursively outer brackets and trim spaces
        this.rawExpression = str = strip(str);  // TODO substitute outer_str with class var

        // extract the outer logic operator. First iterate through the expr
        String outer_str = getOuterExpr(str);
        if (this.allowedKeys.stream().noneMatch(this.rawExpression::contains)) {
            BaseNode.logger.error("the expression does not contain a key for ['name', 'result' or 'time'], syntax error near '"
                    + this.rawExpression + "'.");
            System.exit(40);
        }

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

        // separate the expressions
        left_expr = str.substring(0, str.indexOf(operator));
        right_expr = str.substring(str.indexOf(operator) + operator.length());

        // check which side contains the the keyword, if the key is on the right, switch the sides
        if (this.allowedKeys.stream().noneMatch(this.left_expr::contains)) {
            String helper = this.right_expr;
            this.right_expr = this.left_expr;
            this.left_expr = helper;
            this.switchedKeySide = true;
        }

        // check whether the key can be evaluated as arithmetic operation for keyword = result, or as
        // string operation, e.g., for name = 'asdf' or time='2020-04-23'
        if (this.left_expr.contains(this.arithmeticKeyword)) { //TODO here is a bug for result -5 > 124
            // extract both children, convert the correct object. (the one must match 'name', 'result' or 'time'
            this.child1 = new ArithmeticNode(left_expr);
            this.child2 = new ArithmeticNode(right_expr);
        }
        else {
            if (this.right_expr.contains("'")) {
                this.stringOperation = true;
                this.right_expr = this.right_expr.replaceAll("'","");
            }
            else {
                BaseNode.logger.error("Unexpected situation. There might be a syntax error in '" + this.rawExpression + "'.");
                System.exit(42);
            }
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
            String dataValue = jsonInput.get(this.left_expr).getAsString();
            if (operation.equals("=="))
                return dataValue.equals(this.right_expr);
            if (operation.equals("<>"))
                return !dataValue.equals(this.right_expr);
            if (operation.equals("<"))
                return this.switchedKeySide ^ dataValue.compareTo(this.right_expr) < 0;
            if (operation.equals(">"))
                return this.switchedKeySide ^ dataValue.compareTo(this.right_expr) > 0;
        } else {
            // refer to ArithmeticNode for arithmetic operation
//            double dataValue = jsonInput.get(this.left_expr).getAsDouble();
            if (operation.equals("=="))
                return (this.child1.arithmeticEvaluate(jsonInput) - this.child2.arithmeticEvaluate(jsonInput)) < 1E-7;
            if (operation.equals("<"))
                return this.switchedKeySide ^ this.child1.arithmeticEvaluate(jsonInput) < this.child2.arithmeticEvaluate(jsonInput);  // invert if the order of the expr is interchanged
            if (operation.equals(">"))
                return this.switchedKeySide ^ this.child1.arithmeticEvaluate(jsonInput) > this.child2.arithmeticEvaluate(jsonInput);
        }

        BaseNode.logger.error("Exception in ComparisonNode: " + this.toString());
        System.exit(43);
        return false;
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
