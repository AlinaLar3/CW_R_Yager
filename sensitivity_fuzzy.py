from typing import List, Dict, Tuple, Set
import copy
from fuzzy import FuzzyTrapezoid, fuzzy_yager_method

def _get_best_set_from_fuzzy(ranking: List[Tuple[str, 'FuzzyYagerResult']]) -> Set[str]:
    if not ranking:
        return set()
    best_score = ranking[0][1].overall_rep
    return {alt for alt, res in ranking if abs(res.overall_rep - best_score) < 1e-10}

def _shift_trapezoid(trap: FuzzyTrapezoid, delta: float) -> FuzzyTrapezoid:
    """Сдвиг трапеции с сохранением формы"""
    center = (trap.x2 + trap.x3) / 2
    dist_x1 = center - trap.x1
    dist_x2 = center - trap.x2
    dist_x3 = trap.x3 - center
    dist_x4 = trap.x4 - center    
    new_center = max(0.0, min(1.0, center * (1 + delta)))
    x1 = max(0.0, min(1.0, new_center - dist_x1))
    x2 = max(0.0, min(1.0, new_center - dist_x2))
    x3 = max(0.0, min(1.0, new_center + dist_x3))
    x4 = max(0.0, min(1.0, new_center + dist_x4))
    if x1 > x2: x1, x2 = x2, x1
    if x2 > x3: x2, x3 = x3, x2
    if x3 > x4: x3, x4 = x4, x3
    return FuzzyTrapezoid(x1, x2, x3, x4)

def sensitivity_importance_fuzzy(alternatives: List[str], criteria_importance: Dict[str, FuzzyTrapezoid],
    ratings_matrix: List[List[FuzzyTrapezoid]], delta_range: Tuple[float, float, float] = (-0.5, 0.5, 0.05),
    alpha_levels: List[float] = None, resolve_tie: bool = True) -> Dict:
    """Чувствительность модели к важности в нечётких множествах"""
    if alpha_levels is None:
        alpha_levels = [round(i * 0.1, 1) for i in range(11)]
    _, original_ranking, _ = fuzzy_yager_method(
        alternatives, criteria_importance, ratings_matrix,
        resolve_tie, alpha_levels
    )
    best_original_set = _get_best_set_from_fuzzy(original_ranking)
    criterion_names = list(criteria_importance.keys())
    # Стабильность решения
    stable = True
    for crit_name in criterion_names:
        original_trap = criteria_importance[crit_name]
        start, end, step = delta_range
        delta = start
        while delta <= end + 1e-10:
            modified_weights = copy.deepcopy(criteria_importance)
            modified_weights[crit_name] = _shift_trapezoid(original_trap, delta)
            _, ranking, _ = fuzzy_yager_method(
                alternatives, modified_weights, ratings_matrix,
                resolve_tie, alpha_levels
            )
            new_best_set = _get_best_set_from_fuzzy(ranking)
            if new_best_set!=best_original_set:
                stable = False
                break
            delta += step
        if not stable:
            break
    # Значимость через экстремумы 
    significant = []
    redundant = []
    for crit_name in criterion_names:
        w0 = copy.deepcopy(criteria_importance)
        w0[crit_name] = FuzzyTrapezoid(0, 0, 0, 0)
        _, ranking0, _ = fuzzy_yager_method(alternatives, w0, ratings_matrix, resolve_tie, alpha_levels)
        best0_set = _get_best_set_from_fuzzy(ranking0)
        w1 = copy.deepcopy(criteria_importance)
        w1[crit_name] = FuzzyTrapezoid(1, 1, 1, 1)
        _, ranking1, _ = fuzzy_yager_method(alternatives, w1, ratings_matrix, resolve_tie, alpha_levels)
        best1_set = _get_best_set_from_fuzzy(ranking1)
        if best0_set != best1_set:
            significant.append(crit_name)
        else:
            redundant.append(crit_name)
    return {'is_stable': stable, 'significant': significant, 'redundant': redundant}


def sensitivity_ratings_fuzzy(alternatives: List[str], criteria_importance: Dict[str, FuzzyTrapezoid],
    ratings_matrix: List[List[FuzzyTrapezoid]], delta_range: Tuple[float, float, float] = (-0.5, 0.5, 0.05),
    alpha_levels: List[float] = None, resolve_tie: bool = True) -> Dict:
    """Чувствительность модели к оценкам в нечетких множествах"""
    if alpha_levels is None:
        alpha_levels = [round(i * 0.1, 1) for i in range(11)]
    _, original_ranking, _ = fuzzy_yager_method(
        alternatives, criteria_importance, ratings_matrix,
        resolve_tie, alpha_levels
    )
    best_original_set = _get_best_set_from_fuzzy(original_ranking)
    criterion_names = list(criteria_importance.keys())
    # Стабильность решения
    stable = True
    for alt_idx, alt_name in enumerate(alternatives):
        for crit_idx, crit_name in enumerate(criterion_names):
            original_trap = ratings_matrix[alt_idx][crit_idx]
            start, end, step = delta_range
            delta = start
            while delta <= end + 1e-10:
                modified_ratings = [row[:] for row in ratings_matrix]
                modified_ratings[alt_idx][crit_idx] = _shift_trapezoid(original_trap, delta)
                _, ranking, _ = fuzzy_yager_method(
                    alternatives, criteria_importance, modified_ratings,
                    resolve_tie, alpha_levels
                )
                new_best_set = _get_best_set_from_fuzzy(ranking)
                if new_best_set!=best_original_set:
                    stable = False
                    break
                delta += step
            if not stable:
                break
        if not stable:
            break
    # Значимость через экстремумы
    significant = []
    redundant = []
    for alt_idx, alt_name in enumerate(alternatives):
        for crit_idx, crit_name in enumerate(criterion_names):
            mat0 = [row[:] for row in ratings_matrix]
            mat0[alt_idx][crit_idx] = FuzzyTrapezoid(0, 0, 0, 0)
            _, ranking0, _ = fuzzy_yager_method(alternatives, criteria_importance, mat0, resolve_tie, alpha_levels)
            best0_set = _get_best_set_from_fuzzy(ranking0)
            mat1 = [row[:] for row in ratings_matrix]
            mat1[alt_idx][crit_idx] = FuzzyTrapezoid(1, 1, 1, 1)
            _, ranking1, _ = fuzzy_yager_method(alternatives, criteria_importance, mat1, resolve_tie, alpha_levels)
            best1_set = _get_best_set_from_fuzzy(ranking1)
            pair_key = f"{alt_name}[{crit_name}]"
            if best0_set != best1_set:
                significant.append(pair_key)
            else:
                redundant.append(pair_key)
    return {'is_stable': stable, 'significant': significant, 'redundant': redundant}