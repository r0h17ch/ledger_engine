def validate_transaction(entries):
    if len(entries) < 2:
        return False

    total_debit = 0
    total_credit = 0

    for entry in entries:
        debit = entry["debit"]
        credit = entry["credit"]

        if not isinstance(debit, int) or isinstance(debit, bool):
            return False

        if not isinstance(credit, int) or isinstance(credit, bool):
            return False

        if debit < 0 or credit < 0:
            return False

        if (debit > 0) == (credit > 0):
            return False

        total_debit += debit
        total_credit += credit

    return total_debit == total_credit