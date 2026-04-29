from typing import List, Dict, Tuple, Set
import copy
from linguistic import yager_method_linguistic

def _get_best_set_linguistic(ranking: List[Tuple[str, str]]) -> Set[str]:
    if not ranking:
        return set()
    best_score = ranking[0][1] 
    return {alt for alt, word in ranking if word == best_score}

def sensitivity_importance_linguistic(alternatives: List[str],criteria_importance: Dict[str, str],
    ratings_matrix: List[List[str]], linguistic_scale: List[str]) -> Dict:
    """Чувствительность модели к важности в вербальных"""
    word_to_index = {word: i for i, word in enumerate(linguistic_scale)}
    index_to_word = {i: word for i, word in enumerate(linguistic_scale)}
    max_idx = len(linguistic_scale) - 1
    _, original_ranking, _ = yager_method_linguistic(
        alternatives, criteria_importance, ratings_matrix, linguistic_scale
    )
    best_score_idx = word_to_index[original_ranking[0][1]]
    best_original_set = {alt for alt, word in original_ranking if word_to_index[word] == best_score_idx}
    criterion_names = list(criteria_importance.keys())
    # Стабильность решения
    stable = True
    for crit_name in criterion_names:
        original_idx = word_to_index[criteria_importance[crit_name]]
        for new_idx, new_word in index_to_word.items():
            if new_idx == original_idx:
                continue
            modified_weights = copy.deepcopy(criteria_importance)
            modified_weights[crit_name] = new_word
            _, ranking, _ = yager_method_linguistic(
                alternatives, modified_weights, ratings_matrix, linguistic_scale
            )
            new_best_idx = word_to_index[ranking[0][1]]
            new_best_set = {alt for alt, word in ranking if word_to_index[word] == new_best_idx}
            if new_best_set!=best_original_set:
                stable = False
                break
        if not stable:
            break
    # Значимость через экстремумы
    significant = []
    redundant = []
    for crit_name in criterion_names:
        w_min = copy.deepcopy(criteria_importance)
        w_min[crit_name] = index_to_word[0]
        _, ranking_min, _ = yager_method_linguistic(alternatives, w_min, ratings_matrix, linguistic_scale)
        best_min_idx = word_to_index[ranking_min[0][1]]
        best_min_set = {alt for alt, word in ranking_min if word_to_index[word] == best_min_idx}
        w_max = copy.deepcopy(criteria_importance)
        w_max[crit_name] = index_to_word[max_idx]
        _, ranking_max, _ = yager_method_linguistic(alternatives, w_max, ratings_matrix, linguistic_scale)
        best_max_idx = word_to_index[ranking_max[0][1]]
        best_max_set = {alt for alt, word in ranking_max if word_to_index[word] == best_max_idx}
        if best_min_set != best_max_set:
            significant.append(crit_name)
        else:
            redundant.append(crit_name)
    return {
        'is_stable': stable,
        'significant': significant,
        'redundant': redundant
    }


def sensitivity_ratings_linguistic(alternatives: List[str],criteria_importance: Dict[str, str],
    ratings_matrix: List[List[str]], linguistic_scale: List[str]) -> Dict:
    """Чувствительность модели к оценкам в вербальных"""
    word_to_index = {word: i for i, word in enumerate(linguistic_scale)}
    index_to_word = {i: word for i, word in enumerate(linguistic_scale)}
    max_idx = len(linguistic_scale) - 1
    _, original_ranking, _ = yager_method_linguistic(
        alternatives, criteria_importance, ratings_matrix, linguistic_scale
    )
    best_score_idx = word_to_index[original_ranking[0][1]]
    best_original_set = {alt for alt, word in original_ranking if word_to_index[word] == best_score_idx}
    criterion_names = list(criteria_importance.keys())
    # Стабильность решения
    stable = True    
    for alt_idx, alt_name in enumerate(alternatives):
        for crit_idx, crit_name in enumerate(criterion_names):
            original_idx = word_to_index[ratings_matrix[alt_idx][crit_idx]]
            
            for new_idx, new_word in index_to_word.items():
                if new_idx == original_idx:
                    continue
                
                modified_ratings = [row[:] for row in ratings_matrix]
                modified_ratings[alt_idx][crit_idx] = new_word
                
                _, ranking, _ = yager_method_linguistic(
                    alternatives, criteria_importance, modified_ratings, linguistic_scale
                )
                new_best_idx = word_to_index[ranking[0][1]]
                new_best_set = {alt for alt, word in ranking if word_to_index[word] == new_best_idx}
                if not new_best_set!=best_original_set:
                    stable = False
                    break
            if not stable:
                break
        if not stable:
            break
    # Значимость через экстремумы
    significant = []
    redundant = []
    for alt_idx, alt_name in enumerate(alternatives):
        for crit_idx, crit_name in enumerate(criterion_names):
            mat_min = [row[:] for row in ratings_matrix]
            mat_min[alt_idx][crit_idx] = index_to_word[0]
            _, ranking_min, _ = yager_method_linguistic(alternatives, criteria_importance, mat_min, linguistic_scale)
            best_min_idx = word_to_index[ranking_min[0][1]]
            best_min_set = {alt for alt, word in ranking_min if word_to_index[word] == best_min_idx}
            mat_max = [row[:] for row in ratings_matrix]
            mat_max[alt_idx][crit_idx] = index_to_word[max_idx]
            _, ranking_max, _ = yager_method_linguistic(alternatives, criteria_importance, mat_max, linguistic_scale)
            best_max_idx = word_to_index[ranking_max[0][1]]
            best_max_set = {alt for alt, word in ranking_max if word_to_index[word] == best_max_idx}
            pair_key = f"{alt_name}[{crit_name}]"
            if best_min_set != best_max_set:
                significant.append(pair_key)
            else:
                redundant.append(pair_key)
    return {'is_stable': stable, 'significant': significant, 'redundant': redundant}