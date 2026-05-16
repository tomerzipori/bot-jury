def label_for_index(index: int) -> str:
    if index < 0:
        raise ValueError("index must be non-negative")

    label = ""
    value = index
    while True:
        value, remainder = divmod(value, 26)
        label = chr(ord("A") + remainder) + label
        if value == 0:
            return label
        value -= 1
