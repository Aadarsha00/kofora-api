def calculate_shipping_amount(method, subtotal):
    if method.free_shipping_threshold and subtotal >= method.free_shipping_threshold:
        return 0
    matched_rule = method.rate_rules.filter(min_subtotal__lte=subtotal).order_by("-min_subtotal").first()
    if matched_rule and (matched_rule.max_subtotal is None or subtotal <= matched_rule.max_subtotal):
        return matched_rule.rate
    return method.base_rate
