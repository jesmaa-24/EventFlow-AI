
import sys

from dotenv import load_dotenv

load_dotenv()

from agents.requirement_agent import RequirementAgent
from agents.coordinator_agent import CoordinatorAgent, MAX_RETRIES
from agents.decision_agent import DecisionAgent, STATUS_APPROVE, STATUS_REVISE, STATUS_REJECT
from agents import LLMConfigError
from utils.logger import get_logger

logger = get_logger("main")

BANNER = "=" * 45


def print_header(title: str):
    print(f"\n[{title}]")


def print_banner():
    print(BANNER)
    print("             EVENTFLOW AI")
    print(BANNER)


def print_final_plan(requirements: dict, results: dict, decision: dict):
    venue_info = results.get("venue", {})
    selected_venue = venue_info.get("selected_venue") or {}
    budget_info = results.get("budget", {})
    logistics_info = results.get("logistics", {})
    weather = logistics_info.get("weather", {})

    print("\n" + BANNER)
    print("          FINAL EVENT PLAN")
    print(BANNER)
    print(f"Event:              {requirements.get('event_type')}")
    print(f"Location:           {requirements.get('location')}")
    print(f"Attendees:          {requirements.get('attendees')}")
    print(f"Selected Venue:     {selected_venue.get('name', 'N/A')} "
          f"(capacity {selected_venue.get('capacity', 'N/A')}, ₹{selected_venue.get('price', 'N/A')})")
    print(f"Total Budget:       ₹{budget_info.get('total_budget', 'N/A')}")

    print("Budget Breakdown:")
    allocations = budget_info.get("category_allocations", {})

    for category, amount in allocations.items():
        print(f"  {category.title():15} ₹{amount}")

    print(f"Estimated Cost:     ₹{budget_info.get('total_estimated_cost', 'N/A')}")
    print(f"Remaining Budget:   ₹{budget_info.get('remaining_budget', 'N/A')}")

    if weather.get("status") == "ok":
        print(f"Weather:            {weather['condition']}, {weather['temperature_c']}°C")
    elif weather.get("status") == "unavailable":
        print("Weather:            Unavailable")
    else:
        print("Weather:            Not applicable")

    print("Schedule:")
    for line in logistics_info.get("schedule", []):
        print(f"  - {line}")

    all_recs = logistics_info.get("recommendations", []) + decision.get("recommendations", [])
    if all_recs:
        print("Recommendations:")
        for rec in all_recs:
            print(f"  - {rec}")

    print(BANNER)
    print(f"Decision Score: {decision.get('score')} / 100")
    print(f"Reason: {decision.get('reason')}")
    print(BANNER)


def run_pipeline(user_request: str):
    requirement_agent = RequirementAgent()
    coordinator = CoordinatorAgent()
    decision_agent = DecisionAgent()

    print_header("Requirement Agent")
    requirements = requirement_agent.run(user_request)
    if requirements.get("_valid"):
        print("✓ Requirements extracted")
    else:
        print("✗ Requirements incomplete:")
        for p in requirements.get("_problems", []):
            print(f"    - {p}")

    print_header("Coordinator Agent")
    results = coordinator.run_cycle(requirements)

    print_header("Decision Agent")
    decision = decision_agent.evaluate(requirements, results)

    retries = 0
    while decision["status"] == STATUS_REVISE and retries < MAX_RETRIES:
        retries += 1
        print_header("Coordinator Agent")
        print(f"REVISE requested. Retry {retries}/{MAX_RETRIES} for: {decision['agents_to_retry']}")
        results = coordinator.run_cycle(
            requirements, retry_only=decision["agents_to_retry"], previous_results=results
        )

        print_header("Decision Agent")
        decision = decision_agent.evaluate(requirements, results)

    if decision["status"] == STATUS_REVISE and retries >= MAX_RETRIES:
        print("\n[Decision Agent]")
        print(f"Maximum retry limit ({MAX_RETRIES}) reached. Stopping with best available plan.")
        decision["status"] = STATUS_REJECT
        decision["reason"] = (
            f"Maximum retries ({MAX_RETRIES}) reached without resolving all violations: "
            f"{decision['violations']}"
        )

    if decision["status"] == STATUS_APPROVE:
        print_final_plan(requirements, results, decision)
    else:
        print("\n" + BANNER)
        print(f"          DECISION: {decision['status']}")
        print(BANNER)
        print(f"Reason: {decision.get('reason')}")
        if decision.get("violations"):
            print("Violations:")
            for v in decision["violations"]:
                print(f"  - {v}")
        print(BANNER)


def main():
    print_banner()
    print("\nEnter your event details:\n")

    try:
        event_type = input("Event type: ").strip()
        location = input("Location: ").strip()
        date = input("Date: ").strip()
        attendees = input("Number of attendees: ").strip()
        budget = input("Budget (₹): ").strip()
        venue_type = input("Venue preference (Indoor/Outdoor/Any): ").strip()
        food_preference = input("Food preference: ").strip()
        additional = input("Additional requirements (or None): ").strip()

    except (EOFError, KeyboardInterrupt):
        print("\nInput cancelled. Exiting.")
        sys.exit(0)

    # Check important fields
    if not event_type or not location or not attendees or not budget:
        print("\nRequired event details are missing. Exiting.")
        sys.exit(0)

    # Convert the individual answers into a natural-language request
    # so the existing Requirement Agent can process it.
    user_request = f"""
    Plan a {event_type} in {location}.
    Date: {date if date else 'Not specified'}.
    Number of attendees: {attendees}.
    Budget: ₹{budget}.
    Venue preference: {venue_type if venue_type else 'Any'}.
    Food preference: {food_preference if food_preference else 'Not specified'}.
    Additional requirements: {additional if additional else 'None'}.
    """

    print("\n✓ Event details collected successfully.")
    print("\nStarting EventFlow AI...")

    try:
        run_pipeline(user_request)

    except LLMConfigError as e:
        print(f"\n[Configuration Error]\n{e}")
        sys.exit(1)

    except Exception as e:
        logger.exception("Unexpected error while running the pipeline.")
        print(f"\n[Unexpected Error] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
