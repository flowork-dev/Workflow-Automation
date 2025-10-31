#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\utils\condition_evaluator.py JUMLAH BARIS 61 
#######################################################################

from .type_converter import to_number
def evaluate_condition(actual_value, operator, compare_value):
    """
    Evaluates a condition between an actual value and a comparison value using a specified operator.
    This is the central logic for all 'if' comparisons in the system.
    Args:
        actual_value: The value from the payload.
        operator (str): The comparison operator (e.g., '==', '>', 'contains').
        compare_value: The value to compare against.
    Returns:
        bool: True if the condition is met, False otherwise.
    """
    if operator == "is empty":
        return not actual_value
    if operator == "is not empty":
        return bool(actual_value)
    if operator == "is number":
        return to_number(actual_value) is not None
    if operator == "is not number":
        return to_number(actual_value) is None
    str_actual = str(actual_value).lower()
    str_compare = str(compare_value).lower()
    if operator == "contains":
        return str_compare in str_actual
    if operator == "not contains":
        return str_compare not in str_actual
    if operator == "starts_with":
        return str_actual.startswith(str_compare)
    if operator == "ends_with":
        return str_actual.endswith(str_compare)
    if operator == "==":
        try:
            typed_compare_value = type(actual_value)(compare_value)
            return actual_value == typed_compare_value
        except (ValueError, TypeError):
            return str(actual_value) == str(compare_value)
    if operator == "!=":
        try:
            typed_compare_value = type(actual_value)(compare_value)
            return actual_value != typed_compare_value
        except (ValueError, TypeError):
            return str(actual_value) != str(compare_value)
    num_actual = to_number(actual_value)
    num_compare = to_number(compare_value)
    if num_actual is not None and num_compare is not None:
        if operator == ">":
            return num_actual > num_compare
        if operator == "<":
            return num_actual < num_compare
        if operator == ">=":
            return num_actual >= num_compare
        if operator == "<=":
            return num_actual <= num_compare
    return False
