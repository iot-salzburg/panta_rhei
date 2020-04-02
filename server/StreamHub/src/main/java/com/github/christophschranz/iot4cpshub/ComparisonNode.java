package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;


/**
 * Class representing a ComparisionNode of the stream Parser that is represented by an binary comparision of two
 * ArithmeticNodes.
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
public class ComparisonNode extends BaseNode {
    boolean stringOperation;
    String left_expr;
    String right_expr;
    boolean switchedKeySide;

    /**
     * Initializes a new ComparisionNode. Take a string expression and build the operator and children
     * @param str String expression that describes an comparison operation
     */
    public ComparisonNode(String str) throws StreamSQLException {
        super();
        // remove recursively outer brackets and trim spaces
        this.rawExpression = strip(str);

        // extract the outer logic operator. First iterate through the expr
        String outer_str = getOuterExpr(this.rawExpression);

        // do sanity check
        sanityCheck(outer_str);

        // sanity check if the raw expression contains a keyword
        if (safeFreeOfKeywords(this.rawExpression)) {
            throw new StreamSQLException("The expression does not contain a key for ['name', 'result' or 'time'], " +
                    "syntax error near '" + this.rawExpression + "'.");
        }

        // extract the comparision operator else
        String operator;
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
            throw new StreamSQLException("Couldn't find operator for string expression '" + this.rawExpression + "'.");
        }

        // separate the expressions
        left_expr = this.rawExpression.substring(0, this.rawExpression.indexOf(operator));
        right_expr = this.rawExpression.substring(this.rawExpression.indexOf(operator) + operator.length());

        // check which side contains the the keyword, if the key is on the right, switch the sides
        if (safeFreeOfKeywords(this.left_expr)) {
            String helper = this.right_expr;
            this.right_expr = this.left_expr;
            this.left_expr = helper;
            this.switchedKeySide = true;
        }

        // check whether the key can be evaluated as arithmetic operation for keyword = result, or as
        // string operation, e.g., for name = 'asdf' or time='2020-04-23'
        // it the expression contains the arithmeticKeyword, then two children are created as ArithmeticNode
        if (safeContainsKeyword(this.left_expr, this.arithmeticKeyword)) {
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
                throw new  StreamSQLException("Unexpected situation. There might be a syntax error in '" +
                        this.rawExpression + "'.");
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
    public boolean evaluate(JsonObject jsonInput) throws StreamSQLException {
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

        throw new  StreamSQLException("Exception in ComparisonNode: " + this.toString());
    }

    @Override
    public double arithmeticEvaluate(JsonObject jsonInput) {
        return 0;
    }
    /**
     * Secure return whether the expr contains one of multiple keywords that are given as global variable.
     * It ignores keywords in quotes.
     * @return boolean whether the expr contains a keyword or not
     */
    private boolean safeFreeOfKeywords(String expr) throws StreamSQLException {
//      if (this.allowedKeys.stream().noneMatch(this.rawExpression::contains)) {
        for (String keyword: this.allowedKeys)
            if (this.safeContainsKeyword(expr, keyword)) {
                return false;
            }
        return true;
    }
    /**
     * Secure return whether the expr contains a keyword or not, it ignores keywords in quotes
     * @return boolean whether the expr contains a keyword or not
     */
    private boolean safeContainsKeyword(String expr, String keyword) throws StreamSQLException {
        // copy all chars that are not in quotes to new char array
        int expr_i = 0;  // idx for str
        int res_i = 0;  // idx for outerString generation
        boolean isInQuotes = false;
        char[] ca = new char[expr.length()];
        while (expr_i<expr.length()) {
            if (expr.charAt(expr_i) == '\'')
                isInQuotes = !isInQuotes;
            if (!isInQuotes) {
                ca[res_i] = expr.charAt(expr_i);
                res_i ++;
            }
            expr_i ++;
        }
        // correct invalid number of quotes
        if (isInQuotes)
            throw new  StreamSQLException("Query is invalid, odd number of single quotes: " + this.rawExpression);

        // create new String from resulting char array and check if the arithmetic key word is in it
        String outerString = String.valueOf(ca);
        return outerString.contains(keyword);
    }

    /**
     * Does a sanity check of the comparision expression
     */
    private void sanityCheck(String expr) throws StreamSQLException {
        // remove all allowed Keywords
        for (String keyword: this.allowedKeys)
            expr = expr.replaceAll(keyword, "");

        // remove all strings
        int expr_i = 0;  // idx for str
        int res_i = 0;  // idx for outerString generation
        boolean isInQuotes = false;
        char[] ca = new char[expr.length()];
        while (expr_i<expr.length()) {
            if (expr.charAt(expr_i) == '\'')
                isInQuotes = !isInQuotes;
            if (!isInQuotes) {
                ca[res_i] = expr.charAt(expr_i);
                res_i ++;
            }
            expr_i ++;
        }
        expr = String.valueOf(ca);
        res_i = Math.min(res_i, expr.length());
        expr = expr.substring(0, res_i);

        expr = expr.replaceAll("[\\d.]","");  // remove all numbers
        expr = expr.replaceAll(" ","");  // remove all spaces

        if (expr.length() > 3)
            throw new StreamSQLException("The sanity check fails for expression '" + this.rawExpression + "'.");
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
    }
}
