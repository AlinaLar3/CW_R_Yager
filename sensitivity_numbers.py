from typing import List, Dict, Tuple, Set
import copy
from our_numbers import yager_method


def _get_best_set(ranking: List[Tuple[str, float]]) -> Set[str]:
    if not ranking:
        return set()
    best_score = ranking[0][1]
    return {alt for alt, score in ranking if abs(score - best_score) < 1e-10}


def sensitivity_importance_numeric(alternatives: List[str], criteria_importance: Dict[str, float], ratings_matrix: List[List[float]], delta_range: Tuple[float, float, float] = (-0.5, 0.5, 0.05)) -> Dict:
    """Чувствительность модели к важности в числовых"""
    _, original_ranking, _ = yager_method(alternatives, criteria_importance, ratings_matrix)
    best_original_set = _get_best_set(original_ranking)
    criterion_names = list(criteria_importance.keys())
    # Стабильность решения
    stable = True
    for crit_name in criterion_names:
        original_weight = criteria_importance[crit_name]
        start, end, step = delta_range
        delta = start
        while delta <= end + 1e-10:
            new_weight = max(0.0, min(1.0, original_weight * (1 + delta)))
            modified_weights = copy.deepcopy(criteria_importance)
            modified_weights[crit_name] = new_weight
            _, ranking, _ = yager_method(alternatives, modified_weights, ratings_matrix)
            new_best_set = _get_best_set(ranking)
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
        w0[crit_name] = 0.0
        _, ranking0, _ = yager_method(alternatives, w0, ratings_matrix)
        best0_set = _get_best_set(ranking0)
        w1 = copy.deepcopy(criteria_importance)
        w1[crit_name] = 1.0
        _, ranking1, _ = yager_method(alternatives, w1, ratings_matrix)
        best1_set = _get_best_set(ranking1)
        if best0_set != best1_set:
            significant.append(crit_name)
        else:
            redundant.append(crit_name)
    return {'is_stable': stable, 'significant': significant, 'redundant': redundant}

def sensitivity_ratings_numeric(alternatives: List[str], criteria_importance: Dict[str, float],
    ratings_matrix: List[List[float]], delta_range: Tuple[float, float, float] = (-0.5, 0.5, 0.05)) -> Dict:
    """Чувствительность модели к оценкам в числовых"""
    _, original_ranking, _ = yager_method(alternatives, criteria_importance, ratings_matrix)
    best_original_set = _get_best_set(original_ranking)
    criterion_names = list(criteria_importance.keys())
    # Стабильность решения
    stable = True
    for alt_idx, alt_name in enumerate(alternatives):
        for crit_idx, crit_name in enumerate(criterion_names):
            original_rating = ratings_matrix[alt_idx][crit_idx]
            start, end, step = delta_range
            delta = start
            while delta <= end + 1e-10:
                new_rating = max(0.0, min(1.0, original_rating * (1 + delta)))
                modified_ratings = [row[:] for row in ratings_matrix]
                modified_ratings[alt_idx][crit_idx] = new_rating
                _, ranking, _ = yager_method(alternatives, criteria_importance, modified_ratings)
                new_best_set = _get_best_set(ranking)
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
            mat0[alt_idx][crit_idx] = 0.0
            _, ranking0, _ = yager_method(alternatives, criteria_importance, mat0)
            best0_set = _get_best_set(ranking0)
            mat1 = [row[:] for row in ratings_matrix]
            mat1[alt_idx][crit_idx] = 1.0
            _, ranking1, _ = yager_method(alternatives, criteria_importance, mat1)
            best1_set = _get_best_set(ranking1)
            pair_key = f"{alt_name}[{crit_name}]"
            if best0_set != best1_set:
                significant.append(pair_key)
            else:
                redundant.append(pair_key)
    return {'is_stable': stable, 'significant': significant, 'redundant': redundant}