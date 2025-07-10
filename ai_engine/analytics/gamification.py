"""
Gamification & User Engagement Engine
=====================================

This module provides a comprehensive gamification system designed to drive user
adoption, encourage best practices, and make the process of automation more
engaging and rewarding.

Key Features:
-   **Productivity Scoring**: Calculates a holistic "Productivity Score" for each
    user based on a weighted combination of their automation activities, such as
    the number of workflows created, successful executions, and total time saved.
-   **Achievement & Badge System**: A flexible, definition-driven system for
    awarding users badges for reaching specific milestones (e.g., "First Workflow
    Created," "Automation Power User," "ROI Champion").
-   **Leaderboards**: Generates ranked leaderboards to foster friendly competition,
    showcasing top performers based on metrics like hours saved or automations run.
-   **User-Centric Analytics**: All calculations are scoped to individual users,
    providing personalized feedback and progress tracking.
-   **Extensible Design**: The badge definitions and scoring logic are designed to
    be easily configurable and extendable, allowing administrators to tailor the
    gamification system to their organization's specific goals.
-   **Data-Driven**: Operates on historical execution and workflow data, which would
    be queried from the production database in a real environment.

This engine helps transform the user experience from a purely functional one into
an engaging journey of continuous improvement and measurable achievement.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Callable
import random

# Configure logging
logger = logging.getLogger(__name__)

# --- Badge Definitions ---
# This dictionary acts as a central registry for all achievable badges.
# Each badge has a unique ID, a display name, a description, and a `checker`
# function that determines if a user has earned it based on their stats.

BADGE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "first_workflow": {
        "name": "Automation Pioneer",
        "description": "Created your very first workflow.",
        "icon": "🚀",
        "checker": lambda stats: stats.get("workflows_created", 0) >= 1,
    },
    "first_successful_run": {
        "name": "It's Alive!",
        "description": "Successfully completed your first workflow execution.",
        "icon": "✅",
        "checker": lambda stats: stats.get("successful_runs", 0) >= 1,
    },
    "ten_successful_runs": {
        "name": "Automation Enthusiast",
        "description": "Completed 10 successful workflow executions.",
        "icon": "🔥",
        "checker": lambda stats: stats.get("successful_runs", 0) >= 10,
    },
    "hundred_successful_runs": {
        "name": "Automation Power User",
        "description": "Completed 100 successful workflow executions.",
        "icon": "💯",
        "checker": lambda stats: stats.get("successful_runs", 0) >= 100,
    },
    "roi_champion": {
        "name": "ROI Champion",
        "description": "Saved over 10 hours of manual work.",
        "icon": "💰",
        "checker": lambda stats: stats.get("hours_saved", 0) > 10,
    },
    "high_flyer": {
        "name": "High Flyer",
        "description": "Achieved a productivity score over 500.",
        "icon": "⭐",
        "checker": lambda stats: stats.get("productivity_score", 0) > 500,
    },
    "perfectionist": {
        "name": "Perfectionist",
        "description": "Maintained a 100% success rate over at least 20 runs.",
        "icon": "🎯",
        "checker": lambda stats: stats.get("success_rate", 0) == 100 and stats.get("total_runs", 0) >= 20,
    },
}

# --- Mock Data Store ---
# In a real application, this would query multiple database tables (users, workflows, executions).

def _get_user_stats_for_gamification(user_id: int) -> Dict[str, Any]:
    """
    Mock function to simulate fetching a user's complete activity stats.
    """
    # Simulate some realistic-looking data for a given user
    total_runs = random.randint(5, 150)
    successful_runs = int(total_runs * random.uniform(0.85, 0.99))
    total_duration_saved_s = successful_runs * random.uniform(60, 600)
    
    return {
        "user_id": user_id,
        "username": f"user_{user_id}",
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": total_runs - successful_runs,
        "success_rate": (successful_runs / total_runs) * 100 if total_runs > 0 else 100,
        "total_duration_saved_seconds": total_duration_saved_s,
        "hours_saved": total_duration_saved_s / 3600.0,
        "workflows_created": random.randint(1, 20),
        "first_run_date": datetime.now() - timedelta(days=random.randint(1, 90)),
    }

def _get_all_user_stats_for_leaderboard() -> List[Dict[str, Any]]:
    """
    Mock function to simulate fetching stats for all users for the leaderboard.
    """
    # Simulate stats for 10 users
    return [_get_user_stats_for_gamification(user_id) for user_id in range(1, 11)]


# --- Core Gamification Logic ---

def calculate_productivity_score(stats: Dict[str, Any]) -> int:
    """
    Calculates a user's Productivity Score based on their activities.
    This score provides a single, comparable metric for engagement and impact.
    """
    # Define weights for different activities
    weights = {
        "successful_runs": 1,
        "hours_saved": 25,
        "workflows_created": 10,
        "success_rate_bonus": 50, # Bonus for high reliability
    }
    
    score = (
        stats.get("successful_runs", 0) * weights["successful_runs"] +
        stats.get("hours_saved", 0) * weights["hours_saved"] +
        stats.get("workflows_created", 0) * weights["workflows_created"]
    )
    
    # Add a bonus for maintaining a high success rate
    if stats.get("success_rate", 0) >= 98.0:
        score += weights["success_rate_bonus"]
        
    return int(score)


def award_badges(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Checks the user's stats against the badge definitions and returns all
    badges they have earned.
    """
    earned_badges = []
    for badge_id, details in BADGE_DEFINITIONS.items():
        checker_func: Callable[[Dict], bool] = details["checker"]
        if checker_func(stats):
            earned_badges.append({
                "id": badge_id,
                "name": details["name"],
                "description": details["description"],
                "icon": details["icon"],
            })
    return earned_badges


def get_leaderboard(top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Generates a leaderboard of top users based on their Productivity Score.
    """
    all_user_stats = _get_all_user_stats_for_leaderboard()
    
    leaderboard_data = []
    for stats in all_user_stats:
        score = calculate_productivity_score(stats)
        leaderboard_data.append({
            "user_id": stats["user_id"],
            "username": stats["username"],
            "productivity_score": score,
            "hours_saved": round(stats["hours_saved"], 1),
        })
        
    # Sort users by score in descending order
    sorted_leaderboard = sorted(leaderboard_data, key=lambda x: x['productivity_score'], reverse=True)
    
    return sorted_leaderboard[:top_n]


# --- Public Orchestration Function ---

def get_user_gamification_stats(user_id: int) -> Dict[str, Any]:
    """
    The main public function for this module. It orchestrates all gamification
    calculations for a single user.

    Args:
        user_id: The ID of the user to get stats for.

    Returns:
        A comprehensive dictionary containing the user's productivity score,
        earned badges, and other key metrics.
    """
    logger.info(f"Calculating gamification stats for user_id={user_id}")
    
    # 1. Get the base activity stats
    stats = _get_user_stats_for_gamification(user_id)
    
    # 2. Calculate the productivity score and add it to the stats
    stats["productivity_score"] = calculate_productivity_score(stats)
    
    # 3. Determine which badges the user has earned
    stats["earned_badges"] = award_badges(stats)
    
    # 4. Clean up the response to be more API-friendly
    # (e.g., rounding floats)
    stats["hours_saved"] = round(stats["hours_saved"], 2)
    stats["success_rate"] = round(stats["success_rate"], 1)
    
    return stats


# --- Example Usage ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("--- Gamification & User Engagement Engine Demo ---")
    
    # --- Demo 1: Get stats for a single user ---
    demo_user_id = 123
    user_stats = get_user_gamification_stats(demo_user_id)
    
    print(f"\n📊 Gamification Profile for User: {user_stats['username']}")
    print("-------------------------------------------------")
    print(f"  - 🏆 Productivity Score: {user_stats['productivity_score']}")
    print(f"  - ✅ Successful Runs: {user_stats['successful_runs']}")
    print(f"  - ⏰ Hours Saved: {user_stats['hours_saved']}")
    print(f"  -  workflows_created: {user_stats['workflows_created']}")
    print("\n  - 🎖️ Earned Badges:")
    if user_stats['earned_badges']:
        for badge in user_stats['earned_badges']:
            print(f"    - {badge['icon']} {badge['name']}: {badge['description']}")
    else:
        print("    - None yet. Keep automating!")
    print("-------------------------------------------------")
    
    # --- Demo 2: Get the global leaderboard ---
    leaderboard = get_leaderboard()
    
    print("\n\n🏆 Top 10 Automation Leaders")
    print("=================================================")
    print(f"{'Rank':<5} {'Username':<15} {'Score':<10} {'Hours Saved':<15}")
    print(f"{'----':<5} {'--------':<15} {'-----':<10} {'-----------':<15}")
    for i, user in enumerate(leaderboard):
        rank = i + 1
        print(f"{rank:<5} {user['username']:<15} {user['productivity_score']:<10} {user['hours_saved']:<15.1f}")
    print("=================================================")

