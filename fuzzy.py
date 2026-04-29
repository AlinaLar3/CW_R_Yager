from typing import List, Dict, Tuple
from intervals import Interval, interval_yager_method

class FuzzyTrapezoid:
    """Класс для представления трапецевидного нечеткого множества"""
    def __init__(self, x1: float, x2: float, x3: float, x4: float):
        if not (x1 <= x2 <= x3 <= x4):
            raise ValueError(f"Должно быть: x1 <= x2 <= x3 <= x4, получено: {x1}, {x2}, {x3}, {x4}")
        self.x1 = x1
        self.x2 = x2
        self.x3 = x3
        self.x4 = x4

    def get_alpha_cut(self, alpha: float) -> Interval:
        if alpha < 0 or alpha > 1:
            raise ValueError(f"Alpha должна быть в [0, 1], получено: {alpha}")
        if alpha == 0:
            return Interval(self.x1, self.x4)
        elif alpha == 1:
            return Interval(self.x2, self.x3)
        else:
            left = self.x1 + (self.x2 - self.x1) * alpha
            right = self.x4 - (self.x4 - self.x3) * alpha
            return Interval(left, right)  

    @staticmethod
    def from_interval(interval: Interval):
        return FuzzyTrapezoid(interval.left, interval.left, interval.right, interval.right)

class FuzzyYagerResult:
    """Класс для хранения результатов для нечеткого множества"""
    def __init__(self, alpha_cuts: Dict[float, Interval], overall_rep: float):
        self.alpha_cuts = alpha_cuts
        self.overall_rep = overall_rep

    def __repr__(self):
        return f"{self.overall_rep:.6f}"

def fuzzy_yager_method(alternatives: List[str], criteria_importance: Dict[str, FuzzyTrapezoid],
                      ratings_matrix: List[List[FuzzyTrapezoid]], resolve_tie: bool = False,
                      alpha_levels: List[float] = None) -> Tuple[Dict[str, FuzzyYagerResult],
                                                                List[Tuple[str, FuzzyYagerResult]],
                                                                bool]:
    """Метод Яджера для нечетких множеств"""
    if not alternatives or not criteria_importance or not ratings_matrix:
        return {}, [], False
    if alpha_levels is None:
        alpha_levels = [round(i * 0.1, 1) for i in range(11)]
    criteria_names = list(criteria_importance.keys())
    alt_alpha_intervals = {alt: {} for alt in alternatives}
    alt_results = {alt: {} for alt in alternatives}
    for alpha in alpha_levels:
        importance_intervals = {}
        for crit, fuzzy_imp in criteria_importance.items():
            importance_intervals[crit] = fuzzy_imp.get_alpha_cut(alpha)
        interval_matrix = []
        for i in range(len(alternatives)):
            alt_intervals = []
            for j in range(len(criteria_names)):
                alt_intervals.append(ratings_matrix[i][j].get_alpha_cut(alpha))
            interval_matrix.append(alt_intervals)
        _, sorted_alts, _ = interval_yager_method(alternatives, importance_intervals, interval_matrix, resolve_tie=False)
        for alt, interval, rep in sorted_alts:
            alt_alpha_intervals[alt][alpha] = interval
            alt_results[alt][alpha] = rep
    total_weight = sum(alpha_levels)
    overall_reps = {}
    for alt in alternatives:
        weighted_sum = sum(alt_results[alt][alpha] * alpha for alpha in alpha_levels)
        overall_reps[alt] = weighted_sum / total_weight if total_weight > 0 else 0
    best_rep = max(overall_reps.values())
    best_alternatives = [alt for alt, rep in overall_reps.items() if abs(rep - best_rep) < 1e-10]
    was_tie = len(best_alternatives) > 1
    if was_tie and resolve_tie:
        winners_dict = _resolve_fuzzy_tie(best_alternatives, alternatives, criteria_names, criteria_importance, ratings_matrix, alpha_levels)
        for alt in best_alternatives:
            if alt in winners_dict:
                alt_alpha_intervals[alt] = winners_dict[alt].alpha_cuts
                overall_reps[alt] = winners_dict[alt].overall_rep
        if len(winners_dict) > 1:
            max_rep = max(result.overall_rep for result in winners_dict.values())
            winners_dict = {alt: result for alt, result in winners_dict.items() if abs(result.overall_rep - max_rep) < 1e-10}
        winners = winners_dict
    else:
        winners = {alt: FuzzyYagerResult(alt_alpha_intervals[alt], overall_reps[alt]) 
                  for alt in best_alternatives}
    sorted_alternatives = sorted([(alt, FuzzyYagerResult(alt_alpha_intervals[alt], overall_reps[alt])) for alt in alternatives],
        key=lambda x: x[1].overall_rep, reverse=True)
    return winners, sorted_alternatives, was_tie


def _resolve_fuzzy_tie(tied_alts: List[str], all_alts: List[str], criteria_names: List[str],
                      criteria_importance: Dict[str, FuzzyTrapezoid], ratings_matrix: List[List[FuzzyTrapezoid]],
                      alpha_levels: List[float]) -> Dict[str, FuzzyYagerResult]:
    all_tied_alts = tied_alts.copy()
    current_tied = tied_alts.copy()
    excluded = {alt: [] for alt in all_tied_alts}
    n_criteria = len(criteria_names)    
    for iteration in range(n_criteria):
        if len(current_tied) <= 1:
            break
        if any(len(excluded[alt]) >= n_criteria - 1 for alt in current_tied):
            break
        alphas_to_remove = {alt: [] for alt in current_tied}
        for alpha in alpha_levels:
            importance_intervals = {crit: fuzzy_imp.get_alpha_cut(alpha) for crit, fuzzy_imp in criteria_importance.items()}
            for alt in current_tied:
                alt_idx = all_alts.index(alt)
                alt_intervals = [ratings_matrix[alt_idx][j].get_alpha_cut(alpha) for j in range(n_criteria)]
                barriers = [Interval(1 - imp.right, 1 - imp.left) for imp in importance_intervals.values()]
                barred = [Interval.max_interval(barriers[j], alt_intervals[j]) for j in range(n_criteria)]
                remaining = [(j, barred[j]) for j in range(n_criteria) if j not in excluded[alt]]
                if remaining:
                    min_left = min(interval.left for _, interval in remaining)
                    for j, interval in remaining:
                        if abs(interval.left - min_left) < 1e-10:
                            alphas_to_remove[alt].append(j)
                            break
        criteria_to_remove = {}
        for alt in current_tied:
            if alphas_to_remove[alt]:
                counts = {}
            for crit in alphas_to_remove[alt]:
                counts[crit] = counts.get(crit, 0) + 1
            criteria_to_remove[alt] = max(counts, key=lambda k: counts[k])
        for alt in current_tied:
            if alt in criteria_to_remove:
                excluded[alt].append(criteria_to_remove[alt])
        temp_results = {}
        for alt in current_tied:
            alt_idx = all_alts.index(alt)
            alt_alpha_reps = {}
            for alpha in alpha_levels:
                importance_intervals = {crit: fuzzy_imp.get_alpha_cut(alpha) for crit, fuzzy_imp in criteria_importance.items()}
                alt_intervals = [ratings_matrix[alt_idx][j].get_alpha_cut(alpha) for j in range(n_criteria)]
                barriers = [Interval(1 - imp.right, 1 - imp.left) for imp in importance_intervals.values()]
                barred = [Interval.max_interval(barriers[j], alt_intervals[j]) for j in range(n_criteria)]
                remaining = [barred[j] for j in range(n_criteria) if j not in excluded[alt]]
                if remaining:
                    min_interval = remaining[0]
                    for interval in remaining[1:]:
                        min_interval = Interval.min_interval(min_interval, interval)
                    alt_alpha_reps[alpha] = min_interval.rep()
            total_weight = sum(alpha_levels)
            weighted_sum = sum(alt_alpha_reps[alpha] * alpha for alpha in alt_alpha_reps)
            temp_results[alt] = weighted_sum / total_weight if total_weight > 0 else 0
        if temp_results:
            max_rep = max(temp_results.values())
            current_tied = [alt for alt in current_tied if abs(temp_results[alt] - max_rep) < 1e-10]
    
    all_results = {}
    for alt in all_tied_alts:
        alt_idx = all_alts.index(alt)
        alt_alpha_intervals = {}
        alt_alpha_reps = {}
        for alpha in alpha_levels:
            importance_intervals = {crit: fuzzy_imp.get_alpha_cut(alpha) for crit, fuzzy_imp in criteria_importance.items()}
            alt_intervals = [ratings_matrix[alt_idx][j].get_alpha_cut(alpha) for j in range(n_criteria)]
            barriers = [Interval(1 - imp.right, 1 - imp.left) for imp in importance_intervals.values()]
            barred = [Interval.max_interval(barriers[j], alt_intervals[j]) for j in range(n_criteria)]
            alt_excluded = excluded.get(alt, [])
            remaining = [barred[j] for j in range(n_criteria) if j not in alt_excluded]
            if remaining:
                min_interval = remaining[0]
                for interval in remaining[1:]:
                    min_interval = Interval.min_interval(min_interval, interval)
                alt_alpha_intervals[alpha] = min_interval
                alt_alpha_reps[alpha] = min_interval.rep()
        total_weight = sum(alpha_levels)
        weighted_sum = sum(alt_alpha_reps[alpha] * alpha for alpha in alt_alpha_reps)
        overall_rep = weighted_sum / total_weight if total_weight > 0 else 0
        all_results[alt] = FuzzyYagerResult(alt_alpha_intervals, overall_rep)
    return all_results
