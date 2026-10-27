def _positions(lst, code, n):
    d = {}
    for p in lst:
        if 1 <= p <= n:
            d[p] = code
    return d


def _every8_from9(code, n):
    return _positions([9, 17, 25, 33, 41, 49], code, n)


def _odd_from3(code, n):
    return _positions(list(range(3, n + 1, 2)), code, n)


def _coolant_like(code, n):
    return _positions([5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53], code, n)


def _brake_air(code, n):
    return _positions([3, 6, 9, 12, 15, 20, 23, 28, 31, 36, 39, 44, 47, 52, 55], code, n)


def _fuel_filter(code, n):
    return _positions([3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51, 55], code, n)


def _fuel_tank(code, n):
    return _positions([12, 20, 28, 36, 44, 52], code, n)


def expand_operation(op, n):
    """Возвращает dict {to_number: code} для одной операции."""
    t = op["type"]
    code = op.get("code", "I")
    
    # Вспомогательная функция для сдвига старых индексов (1-based) в новые (0-based)
    def shift_and_filter(positions_list):
        return {p - 1: code for p in positions_list if 0 <= (p - 1) < n}

    if t == "all":
        # Каждое ТО (начиная с ТО-0)
        return {i: code for i in range(0, n)}
        
    if t == "positions":
        # Если в JSON заданы точные позиции, тоже сдвигаем их
        return shift_and_filter(op["positions"])
        
    if t == "every8_from9":
        return shift_and_filter([9, 17, 25, 33, 41, 49])
        
    if t == "odd_from3":
        return shift_and_filter(list(range(3, n + 2, 2)))
        
    if t == "coolant_like":
        return shift_and_filter([5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53])
        
    if t == "brake_air":
        return shift_and_filter([3, 6, 9, 12, 15, 20, 23, 28, 31, 36, 39, 44, 47, 52, 55])
        
    if t == "fuel_filter":
        return shift_and_filter([3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51, 55])
        
    if t == "fuel_tank":
        return shift_and_filter([12, 20, 28, 36, 44, 52])
        
    return {}


def build_matrix(regulations):
    """Возвращает {to_number: [ (op, code), ... ] }."""
    n = regulations["interval"]["max_to"]
    matrix = {i: [] for i in range(1, n + 1)}
    for op in regulations["operations"]:
        expanded = expand_operation(op, n)
        for to_num, code in expanded.items():
            matrix[to_num].append({**op, "schedule_code": code})
    return matrix


def mileage_for(to_num, interval):
    if to_num == 0:
        return 1000
    return to_num * 10000