def _positions(lst, code, n):
    d = {}
    for p in lst:
        if 0 <= p < n:  # Проверка границ: индекс должен быть от 0 до 55
            d[p] = code
    return d


def _every8_from9(code, n):
    # Старые индексы 9, 17, 25... сдвигаем на -1 (становятся 8, 16, 24...)
    return _positions([8, 16, 24, 32, 40, 48], code, n)


def _odd_from3(code, n):
    # Старое "нечетное начиная с 3" теперь начинается с 2 (ТО-2, ТО-4 и т.д.)
    return _positions(list(range(2, n, 2)), code, n)


def _coolant_like(code, n):
    # Старые 5, 9, 13... сдвигаются на -1 (становятся 4, 8, 12...)
    return _positions([4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52], code, n)


def _brake_air(code, n):
    # Старые 3, 6, 9... сдвигаются на -1 (становятся 2, 5, 8...)
    return _positions([2, 5, 8, 11, 14, 19, 22, 27, 30, 35, 38, 43, 46, 51, 54], code, n)


def _fuel_filter(code, n):
    # Старые 3, 7, 11... сдвигаются на -1 (становятся 2, 6, 10...)
    return _positions([2, 6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46, 50, 54], code, n)


def _fuel_tank(code, n):
    # Старые 12, 20, 28... сдвигаются на -1 (становятся 11, 19, 27...)
    return _positions([11, 19, 27, 35, 43, 51], code, n)


def expand_operation(op, n):
    """Возвращает dict {to_number: code} для одной операции."""
    t = op["type"]
    code = op.get("code", "I")
    
    if t == "all":
        return {i: code for i in range(0, n)}
        
    if t == "positions":
        # Для точных позиций из JSON тоже сдвигаем на -1
        shifted = [p - 1 for p in op["positions"]]
        return _positions(shifted, code, n)
        
    if t == "every8_from9":
        return _every8_from9(code, n)
        
    if t == "odd_from3":
        return _odd_from3(code, n)
        
    if t == "coolant_like":
        return _coolant_like(code, n)
        
    if t == "brake_air":
        return _brake_air(code, n)
        
    if t == "fuel_filter":
        return _fuel_filter(code, n)
        
    if t == "fuel_tank":
        return _fuel_tank(code, n)
        
    return {}


def build_matrix(regulations):
    """Возвращает {to_number: [ (op, code), ... ] }."""
    n = regulations["interval"]["max_to"]
    matrix = {i: [] for i in range(0, n)} # Коробочки от 0 до 55
    
    for op in regulations["operations"]:
        expanded = expand_operation(op, n)
        for to_num, code in expanded.items():
            # Железобетонная проверка: если номер ТО существует, добавляем
            if to_num in matrix:
                matrix[to_num].append({**op, "schedule_code": code})
                
    return matrix


def mileage_for(to_num, interval):
    if to_num == 0:
        return 1000
    return to_num * 10000