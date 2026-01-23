def format_sizes(sizes_list):
    """
    Форматирует список размеров, группируя последовательные размеры в диапазоны.
    Пример: ['41', '42', '43'] -> '41-43'
    """
    if not sizes_list:
        return ""

    # Преобразуем в числа для сортировки
    try:
        # Извлекаем числа из строк (например "41 EU" -> 41.0)
        # Предполагаем, что размер это первое число в строке
        parsed_sizes = []
        for s in sizes_list:
            # Очищаем от букв и пробелов, оставляем цифры и точку/запятую
            clean_s = "".join(c for c in str(s) if c.isdigit() or c in [".", ","])
            clean_s = clean_s.replace(",", ".")
            if clean_s:
                parsed_sizes.append(float(clean_s))

        if not parsed_sizes:
            return ", ".join(sizes_list)

        # Сортируем и удаляем дубликаты
        sorted_sizes = sorted(list(set(parsed_sizes)))

        result_parts = []
        if not sorted_sizes:
            return ""

        start = sorted_sizes[0]
        prev = sorted_sizes[0]
        count = 1

        for i in range(1, len(sorted_sizes)):
            current = sorted_sizes[i]
            # Считаем последовательностью, если разница <= 1.0 (чтобы учесть 41, 42 и 41, 41.5)
            # Но для красивых диапазонов 41-43 обычно имеют в виду целые шаги или "подряд идущие"
            # Давайте будем считать последовательностью, если разница <= 1.0
            diff = current - prev

            if diff <= 1.05:  # Небольшой запас для float
                prev = current
                count += 1
            else:
                # Закрываем предыдущую группу
                if count >= 3:
                    # Убираем .0 если число целое
                    start_str = f"{int(start)}" if start.is_integer() else f"{start}"
                    prev_str = f"{int(prev)}" if prev.is_integer() else f"{prev}"
                    result_parts.append(f"{start_str}-{prev_str}")
                else:
                    # Добавляем все числа из группы по отдельности
                    # (тут надо аккуратно, так как мы хранили только start и prev)
                    # Проще пересобрать логику: собираем буфер
                    pass

                # Сброс
                start = current
                prev = current
                count = 1

        # Эта логика выше сложная для восстановления промежуточных чисел,
        # если мы их не хранили. Давайте перепишем проще.

        groups = []
        if not sorted_sizes:
            return ""

        current_group = [sorted_sizes[0]]

        for i in range(1, len(sorted_sizes)):
            curr = sorted_sizes[i]
            prev = sorted_sizes[i - 1]

            # Если шаг небольшой (до 1.0 включительно), добавляем в группу
            if (curr - prev) <= 1.05:
                current_group.append(curr)
            else:
                groups.append(current_group)
                current_group = [curr]
        groups.append(current_group)

        final_strings = []
        for group in groups:
            if len(group) >= 3:
                start_v = group[0]
                end_v = group[-1]
                s_str = f"{int(start_v)}" if start_v.is_integer() else f"{start_v}"
                e_str = f"{int(end_v)}" if end_v.is_integer() else f"{end_v}"
                final_strings.append(f"{s_str}-{e_str}")
            else:
                for v in group:
                    v_str = f"{int(v)}" if v.is_integer() else f"{v}"
                    final_strings.append(v_str)

        return ", ".join(final_strings)

    except Exception as e:
        print(f"Ошибка форматирования размеров: {e}")
        return ", ".join(sizes_list)


def has_valid_size(sizes_list, min_size=41.0):
    """
    Проверяет, есть ли в списке хотя бы один размер >= min_size.
    Args:
        sizes_list: список строк с размерами (например ['39 EU', '41.5 EU'])
        min_size: минимальный размер для прохождения фильтра (по умолчанию 41.0)
    Returns:
        True, если есть подходящий размер, иначе False.
    """
    if not sizes_list:
        return False

    try:
        found = False
        for s in sizes_list:
            # Очищаем от букв и пробелов, оставляем цифры и точку/запятую
            clean_s = "".join(c for c in str(s) if c.isdigit() or c in [".", ","])
            clean_s = clean_s.replace(",", ".")

            if clean_s:
                size_val = float(clean_s)
                if size_val >= min_size:
                    found = True
                    break
        return found
    except Exception as e:
        print(f"Ошибка при проверке размера {sizes_list}: {e}")
        # Если не смогли распарсить, лучше пропустить или оставить?
        # Допустим, оставим False (строгий фильтр), чтобы мусор не летел.
        return False


if __name__ == "__main__":
    # Simple tests
    print(format_sizes(["41", "42", "43"]))  # Expected: 41-43
    print(format_sizes(["40", "42", "44"]))  # Expected: 40, 42, 44
    print(format_sizes(["40", "40.5", "41", "41.5", "42"]))  # Expected: 40-42
    print(format_sizes(["39", "40", "41", "45", "46"]))  # Expected: 39-41, 45, 46

    # Test has_valid_size
    print(
        f"Has valid size (41+): {has_valid_size(['39 EU', '40 EU'])}"
    )  # Expected: False
    print(
        f"Has valid size (41+): {has_valid_size(['40 EU', '41 EU'])}"
    )  # Expected: True
    print(
        f"Has valid size (41+): {has_valid_size(['36 EU', 42, 45])}"
    )  # Expected: True
