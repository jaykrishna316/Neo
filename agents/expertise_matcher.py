"""Developer expertise matching - recommend best developer for task.

Uses historical patterns to match developers/agents to change types and code regions.
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import statistics


class Expertise(Enum):
    """Expertise levels based on performance."""
    NOVICE = "novice"          # High variance, slow
    INTERMEDIATE = "intermediate"  # Moderate speed
    EXPERT = "expert"          # Fast and consistent
    SPECIALIST = "specialist"  # Very fast in specific domain


@dataclass
class ExpertiseProfile:
    """Developer expertise in a domain."""
    developer_id: str
    expertise_level: Expertise
    primary_skills: List[str]  # e.g., ["auth", "payment", "api"]
    speed_score: float  # 0-100, based on median time
    consistency_score: float  # 0-100, std dev (higher = more consistent)
    confidence_score: float  # 0-100, based on sample size
    recommended_for: List[str]  # Types of changes they excel at


def build_expertise_profile(
    developer_id: str,
    completion_history: List[Dict[str, Any]],
    skill_tags: Dict[str, List[str]] = None,
) -> ExpertiseProfile:
    """
    Build expertise profile from developer's history.

    Args:
        developer_id: Developer identifier
        completion_history: List of {"duration", "category", "file_path", ...}
        skill_tags: Optional dict mapping file patterns to skills

    Returns:
        ExpertiseProfile with skills and performance metrics
    """
    if not completion_history:
        return ExpertiseProfile(
            developer_id=developer_id,
            expertise_level=Expertise.NOVICE,
            primary_skills=[],
            speed_score=50.0,
            consistency_score=50.0,
            confidence_score=0.0,
            recommended_for=[]
        )

    # Extract durations
    durations = [h.get("duration", 0) for h in completion_history]
    categories = [h.get("category", "general") for h in completion_history]
    file_paths = [h.get("file_path", "") for h in completion_history]

    # Speed score: lower duration = higher score
    median_duration = statistics.median(durations) if durations else 0
    # Normalize to 0-100: assume 30min is median across team
    # 5min = 90, 10min = 80, 30min = 50, 60min = 20
    speed_score = max(0, min(100, 100 - (median_duration / 3.6)))

    # Consistency score: lower std dev = higher consistency
    consistency_score = 50.0
    if len(durations) > 1:
        try:
            std_dev = statistics.stdev(durations)
            # Lower std dev = higher score
            # 0 std dev = 100, 600 std dev = 0
            consistency_score = max(0, min(100, 100 - (std_dev / 6)))
        except:
            consistency_score = 50.0

    # Determine expertise level
    if len(completion_history) < 3:
        expertise_level = Expertise.NOVICE
        confidence = len(completion_history) * 20  # 20-60%
    elif speed_score > 80 and consistency_score > 80:
        expertise_level = Expertise.SPECIALIST
        confidence = min(100, len(completion_history) * 10)
    elif speed_score > 70 and consistency_score > 70:
        expertise_level = Expertise.EXPERT
        confidence = min(100, len(completion_history) * 10)
    elif speed_score > 50:
        expertise_level = Expertise.INTERMEDIATE
        confidence = min(100, len(completion_history) * 8)
    else:
        expertise_level = Expertise.NOVICE
        confidence = min(100, len(completion_history) * 8)

    # Identify primary skills from categories and files
    primary_skills = list(set(categories))[:3]  # Top 3 categories

    # Recommended types based on expertise
    if expertise_level == Expertise.SPECIALIST:
        recommended = primary_skills + ["urgent", "complex"]
    elif expertise_level == Expertise.EXPERT:
        recommended = primary_skills + ["critical"]
    elif expertise_level == Expertise.INTERMEDIATE:
        recommended = primary_skills
    else:
        recommended = ["simple", "guided"]

    return ExpertiseProfile(
        developer_id=developer_id,
        expertise_level=expertise_level,
        primary_skills=primary_skills,
        speed_score=speed_score,
        consistency_score=consistency_score,
        confidence_score=confidence,
        recommended_for=recommended
    )


def recommend_developer(
    change_type: str,
    change_scope: str,
    urgency: str,  # low/medium/high
    expertise_profiles: Dict[str, ExpertiseProfile],
) -> List[Tuple[str, float, str]]:
    """
    Recommend best developer(s) for a change.

    Args:
        change_type: Type of change (feature/bugfix/refactor/etc)
        change_scope: Scope (single-function/file/module)
        urgency: Urgency level
        expertise_profiles: Dict of developer_id -> ExpertiseProfile

    Returns:
        List of (developer_id, score, reasoning)
    """
    recommendations = []

    for dev_id, profile in expertise_profiles.items():
        score = 0.0
        reasons = []

        # Match on expertise level
        if urgency == "high":
            if profile.expertise_level == Expertise.SPECIALIST:
                score += 30
                reasons.append("Specialist-level expertise for urgent changes")
            elif profile.expertise_level == Expertise.EXPERT:
                score += 25
                reasons.append("Expert-level developer")
            elif profile.expertise_level == Expertise.INTERMEDIATE:
                score += 10
                reasons.append("Intermediate developer")
            else:
                score += 0
                reasons.append("Not recommended for urgent work")
        else:
            # For non-urgent, lower bar
            if profile.expertise_level in (Expertise.SPECIALIST, Expertise.EXPERT):
                score += 20
                reasons.append("High expertise available")
            elif profile.expertise_level == Expertise.INTERMEDIATE:
                score += 15
                reasons.append("Suitable for this change")
            else:
                score += 5
                reasons.append("Available, but limited experience")

        # Match on skills
        if change_type in profile.primary_skills:
            score += 25
            reasons.append(f"Experienced in {change_type}")
        elif change_type in profile.recommended_for:
            score += 15
            reasons.append(f"Good fit for {change_type}")

        # Speed bonus for large changes
        if change_scope in ("module", "file"):
            score += profile.speed_score * 0.1
            reasons.append(f"Fast ({profile.speed_score:.0f}/100)")

        # Consistency bonus for critical changes
        if urgency == "high":
            score += profile.consistency_score * 0.1
            reasons.append(f"Consistent ({profile.consistency_score:.0f}/100)")

        # Confidence penalty for low confidence
        score *= (profile.confidence_score / 100)

        if score > 0:
            reasoning = " + ".join(reasons)
            recommendations.append((dev_id, score, reasoning))

    # Sort by score descending
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations


def get_expertise_gap(
    developer_id: str,
    needed_skill: str,
    expertise_profiles: Dict[str, ExpertiseProfile],
) -> Dict[str, Any]:
    """
    Identify expertise gaps and recommend training.

    Args:
        developer_id: Developer to assess
        needed_skill: Skill they need
        expertise_profiles: All developers' profiles

    Returns:
        Gap assessment with recommendations
    """
    profile = expertise_profiles.get(developer_id)

    if not profile:
        return {"gap": "unknown", "recommendation": "No expertise data yet"}

    if needed_skill in profile.primary_skills:
        return {
            "gap": "none",
            "current_level": "expert",
            "recommendation": f"Developer is already strong in {needed_skill}"
        }

    if needed_skill in profile.recommended_for:
        return {
            "gap": "minor",
            "current_level": "intermediate",
            "recommendation": f"Good foundation in {needed_skill}, could deepen knowledge"
        }

    # Find expert in this skill to pair with
    experts = [
        (dev_id, prof.speed_score)
        for dev_id, prof in expertise_profiles.items()
        if needed_skill in prof.primary_skills
    ]

    if experts:
        expert_id, expert_speed = sorted(experts, key=lambda x: x[1], reverse=True)[0]
        return {
            "gap": "major",
            "current_level": "novice",
            "recommendation": f"Pair with {expert_id} for knowledge transfer",
            "mentor": expert_id
        }

    return {
        "gap": "major",
        "current_level": "novice",
        "recommendation": f"No current expert in {needed_skill} - consider external training"
    }


if __name__ == "__main__":
    print("Expertise Matching System")
    print("=" * 60)

    # Example history
    alice_history = [
        {"duration": 900, "category": "feature", "file_path": "src/auth.py"},
        {"duration": 1200, "category": "feature", "file_path": "src/auth.py"},
        {"duration": 600, "category": "bugfix", "file_path": "src/auth.py"},
        {"duration": 1100, "category": "feature", "file_path": "src/payment.py"},
    ]

    bob_history = [
        {"duration": 300, "category": "bugfix", "file_path": "src/payment.py"},
        {"duration": 400, "category": "bugfix", "file_path": "src/payment.py"},
        {"duration": 350, "category": "bugfix", "file_path": "src/logging.py"},
    ]

    charlie_history = [
        {"duration": 2000, "category": "refactor", "file_path": "src/auth.py"},
        {"duration": 2100, "category": "refactor", "file_path": "src/db.py"},
    ]

    print("\n1. Build Expertise Profiles:")
    profiles = {
        "alice": build_expertise_profile("alice", alice_history),
        "bob": build_expertise_profile("bob", bob_history),
        "charlie": build_expertise_profile("charlie", charlie_history),
    }

    for dev_id, profile in profiles.items():
        print(f"\n{dev_id.upper()}:")
        print(f"  Level: {profile.expertise_level.value}")
        print(f"  Speed: {profile.speed_score:.0f}/100")
        print(f"  Consistency: {profile.consistency_score:.0f}/100")
        print(f"  Skills: {', '.join(profile.primary_skills)}")

    print("\n\n2. Recommend Developer for Feature:")
    recs = recommend_developer(
        change_type="feature",
        change_scope="file",
        urgency="high",
        expertise_profiles=profiles
    )
    for dev_id, score, reasoning in recs[:2]:
        print(f"  {dev_id}: {score:.0f} - {reasoning}")

    print("\n\n3. Recommend Developer for Bugfix:")
    recs = recommend_developer(
        change_type="bugfix",
        change_scope="single-function",
        urgency="high",
        expertise_profiles=profiles
    )
    for dev_id, score, reasoning in recs[:2]:
        print(f"  {dev_id}: {score:.0f} - {reasoning}")

    print("\n\n4. Expertise Gap Assessment:")
    gap = get_expertise_gap("alice", "payment", profiles)
    print(f"  Gap: {gap['gap']}")
    if "mentor" in gap:
        print(f"  Mentor: {gap['mentor']}")
    print(f"  Recommendation: {gap['recommendation']}")
