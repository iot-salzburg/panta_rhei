

def is_valid(payload):
    """
    Checks the stream for validity.
    :param payload: String instance from the database
    :return: True if valid, else False
    """
    logic = payload.get("FILTER_LOGIC", "")

    # An empty filter_logic is valid
    if logic == "":
        return True

    if logic.count("SELECT") != 1 or logic.count("FROM") != 1 or \
            logic.count("WHERE") > 1:
        return False

    # TODO implement more checks in Java and get feedback if the node can be built
    return True
