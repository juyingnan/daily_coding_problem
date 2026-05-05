import random
import string

def generate_alias_rule_1(first_name, last_name):
    """
    Rule #1: Classic approach like 'billg'
        - Take up to 5 letters of the first name (lowercased)
        - Append up to 2 letters of the last name (lowercased)
        - e.g. 'Bill Gates' -> 'billga'
    """
    # If either name is missing, fall back to rule 6
    if not first_name or not last_name:
        return generate_alias_rule_6(first_name or last_name, last_name or first_name)
    
    first_part = first_name[:5].lower()  # up to 5 letters
    last_part = last_name[:2].lower()   # up to 2 letters
    return first_part + last_part

def generate_alias_rule_2(first_name, last_name):
    """
    Rule #2: Reverse approach like 'gatbil'
        - Take 3 letters from the last name
        - Append 3 letters from the first name
    """
    # If either name is missing, fall back to rule 6
    if not first_name or not last_name:
        return generate_alias_rule_6(first_name or last_name, last_name or first_name)
    
    return last_name[:3].lower() + first_name[:3].lower()

def generate_alias_rule_3(first_name, middle_name, last_name):
    """
    Rule #3: Incorporate middle initial if it exists
        - Format: <first_name_initial><middle_name_initial><last_name[:4]>
        - e.g. 'William Henry Gates' -> 'whgate'
        - If no middle name, ignore it (just do <first_initial><last[:5]>).
    """
    first_initial = first_name[0].lower() if first_name else ''
    middle_initial = middle_name[0].lower() if middle_name else ''
    last_part = last_name[:4].lower()
    
    # If there's no middle_name, fall back to <first_initial><last[:5]>
    if not middle_name:
        return first_initial + last_name[:5].lower()
    else:
        return first_initial + middle_initial + last_part

def generate_alias_rule_4(first_name, last_name=None):
    """
    Rule #4: First name + random number (e.g., 'bill42')
    """
    number = str(random.randint(10, 99))
    return f"{first_name.lower()}{number}"

def generate_alias_rule_5(first_name, last_name):
    """
    Rule #5: first+dot+last (e.g., 'bill.gates')
    """
    # If either name is missing, fall back to rule 6
    if not first_name or not last_name:
        return generate_alias_rule_6(first_name or last_name, last_name or first_name)
    
    return f"{first_name.lower()}.{last_name.lower()}"

def generate_alias_rule_6(first_name, last_name):
    """
    Rule #6: first+last (e.g., 'billgates')
    """
    # If either name is missing, fall back to rule 4
    if not first_name or not last_name:
        return generate_alias_rule_4(first_name or last_name)
    
    return f"{first_name.lower()}{last_name.lower()}"


def generate_random_alias(full_name):
    """
    Master function to parse the input name, pick a random rule,
    and generate an alias accordingly.
    full_name can have first, middle, and last name separated by spaces.
    e.g. "Bill Gates" or "William Henry Gates"
    """
    # Split the input into parts
    parts = full_name.strip().split()
    if len(parts) == 1:
        # Only one "name" given - treat as first_name, no last_name
        first_name = parts[0]
        middle_name = ""
        last_name = ""
    elif len(parts) == 2:
        first_name, last_name = parts
        middle_name = ""
    else:
        # If there's more than 2, assume the final part is last_name, the first is first_name, 
        # and everything else in between is middle names (just combine them for our middle_name).
        first_name = parts[0]
        last_name = parts[-1]
        middle_name = " ".join(parts[1:-1])
    
    # Prepare the rules. Some rules do/don't use middle_name. We'll handle that logic inside the rule.
    rules = [
        (generate_alias_rule_1, False),
        (generate_alias_rule_2, False),
        (generate_alias_rule_3, True),
        (generate_alias_rule_4, False),
        (generate_alias_rule_5, False),
        (generate_alias_rule_6, False)
    ]
    
    # Pick a random rule
    chosen_rule, needs_middle = random.choice(rules)
    
    # Call that rule with appropriate parameters
    if needs_middle:
        alias = chosen_rule(first_name, middle_name, last_name)
    else:
        alias = chosen_rule(first_name, last_name)
    
    return alias


if __name__ == "__main__":
    # Example usage:
    test_names = [
        "Bill Gates",
        "Satya Nadella",
        "William Henry Gates",
        "Ada",
        "Elon Reeve Musk",
        "Jean-luc Picard"
    ]
    
    for name in test_names:
        alias = generate_random_alias(name)
        print(f"Name: {name} -> Alias: {alias}")
