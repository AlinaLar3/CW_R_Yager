from typing import List, Dict, Tuple, Set
import copy
from intervals import Interval, interval_yager_method

def _get_best_set_from_interval(ranking: List[Tuple[str, Interval, float]]) -> Set[str]:
    if not ranking:
        return set()
    best_score = ranking[0][2]
    return {alt for alt, _, score in ranking if abs(score - best_score) < 1e-10}


def sensitivity_importance_interval(alternatives: List[str], criteria_importance: Dict[str, Interval],
    ratings_matrix: List[List[Interval]], delta_range: Tuple[float, float, float] = (-0.5, 0.5, 0.05),
    resolve_tie: bool = True) -> Dict:
    """Чувствительность модели к важности в интервалах"""
    _, original_ranking, _ = interval_yager_method(
        alternatives, criteria_importance, ratings_matrix, resolve_tie
    )
    best_original_set = _get_best_set_from_interval(original_ranking)
    criterion_names = list(criteria_importance.keys())
    print(original_ranking)
    # Стабильность решения
    stable = True
    for crit_name in criterion_names:
        original_interval = criteria_importance[crit_name]
        original_mid = original_interval.midpoint()
        width = original_interval.length()
        start, end, step = delta_range
        delta = start
        while delta <= end + 1e-10:
            new_mid = max(0.0, min(1.0, original_mid * (1 + delta)))
            new_left = max(0.0, new_mid - width / 2)
            new_right = min(1.0, new_mid + width / 2)
            if new_left > new_right:
                new_left, new_right = new_right, new_left
            modified_weights = copy.deepcopy(criteria_importance)
            modified_weights[crit_name] = Interval(new_left, new_right)
            _, ranking, _ = interval_yager_method(
                alternatives, modified_weights, ratings_matrix, resolve_tie
            )
            new_best_set = _get_best_set_from_interval(ranking)
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
        w0[crit_name] = Interval(0, 0)
        _, ranking0, _ = interval_yager_method(alternatives, w0, ratings_matrix, resolve_tie)
        best0_set = _get_best_set_from_interval(ranking0)
        w1 = copy.deepcopy(criteria_importance)
        w1[crit_name] = Interval(1, 1)
        _, ranking1, _ = interval_yager_method(alternatives, w1, ratings_matrix, resolve_tie)
        best1_set = _get_best_set_from_interval(ranking1)
        if best0_set != best1_set:
            significant.append(crit_name)
        else:
            redundant.append(crit_name)
    return {'is_stable': stable, 'significant': significant, 'redundant': redundant}


def sensitivity_ratings_interval(alternatives: List[str], criteria_importance: Dict[str, Interval],
    ratings_matrix: List[List[Interval]], delta_range: Tuple[float, float, float] = (-0.5, 0.5, 0.05),
    resolve_tie: bool = True) -> Dict:
    """Чувствительность модели к оценкам в интервалах"""
    _, original_ranking, _ = interval_yager_method(
        alternatives, criteria_importance, ratings_matrix, resolve_tie
    )
    best_original_set = _get_best_set_from_interval(original_ranking)
    criterion_names = list(criteria_importance.keys())
    # Стабильность решения
    stable = True
    for alt_idx, alt_name in enumerate(alternatives):
        for crit_idx, crit_name in enumerate(criterion_names):
            original_interval = ratings_matrix[alt_idx][crit_idx]
            original_mid = original_interval.midpoint()
            width = original_interval.length()
            start, end, step = delta_range
            delta = start
            while delta <= end + 1e-10:
                new_mid = max(0.0, min(1.0, original_mid * (1 + delta)))
                new_left = max(0.0, new_mid - width / 2)
                new_right = min(1.0, new_mid + width / 2)
                if new_left > new_right:
                    new_left, new_right = new_right, new_left
                modified_ratings = [row[:] for row in ratings_matrix]
                modified_ratings[alt_idx][crit_idx] = Interval(new_left, new_right)
                _, ranking, _ = interval_yager_method(
                    alternatives, criteria_importance, modified_ratings, resolve_tie
                )
                new_best_set = _get_best_set_from_interval(ranking)
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
            mat0[alt_idx][crit_idx] = Interval(0, 0)
            _, ranking0, _ = interval_yager_method(alternatives, criteria_importance, mat0, resolve_tie)
            best0_set = _get_best_set_from_interval(ranking0)
            mat1 = [row[:] for row in ratings_matrix]
            mat1[alt_idx][crit_idx] = Interval(1, 1)
            _, ranking1, _ = interval_yager_method(alternatives, criteria_importance, mat1, resolve_tie)
            best1_set = _get_best_set_from_interval(ranking1)
            pair_key = f"{alt_name}[{crit_name}]"
            if best0_set != best1_set:
                significant.append(pair_key)
            else:
                redundant.append(pair_key)
    
    return {'is_stable': stable, 'significant': significant, 'redundant': redundant}