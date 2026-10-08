"""Money and VAT calculations shared by product and document forms."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CENT = Decimal("0.01")


def decimal_value(value):
    try:
        result = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Podaj poprawną liczbę.") from error
    if not result.is_finite():
        raise ValueError("Podaj poprawną liczbę.")
    return result


def vat_rate(value):
    rate = decimal_value(value)
    if not 0 <= rate <= 100 or rate != rate.quantize(CENT):
        raise ValueError("VAT musi być liczbą od 0 do 100 z maksymalnie dwoma miejscami po przecinku.")
    return rate


def net_price(value):
    price = decimal_value(value)
    if price < 0 or price != price.quantize(CENT):
        raise ValueError("Cena netto musi być nieujemna i mieć najwyżej dwa miejsca po przecinku.")
    return price


def quantity(value):
    amount = decimal_value(value)
    if amount <= 0 or amount != amount.to_integral_value():
        raise ValueError("Ilość musi być dodatnią liczbą całkowitą.")
    return int(amount)


def line_totals(price, amount, rate):
    price = net_price(price)
    amount = quantity(amount)
    net = (price * amount).quantize(CENT, rounding=ROUND_HALF_UP)
    return totals_from_net(net, rate)


def totals_from_net(net, rate):
    net = decimal_value(net).quantize(CENT, rounding=ROUND_HALF_UP)
    rate = vat_rate(rate)
    tax = (net * rate / 100).quantize(CENT, rounding=ROUND_HALF_UP)
    return net, tax, net + tax


def money_text(value):
    return f"{decimal_value(value).quantize(CENT, rounding=ROUND_HALF_UP):.2f}"
