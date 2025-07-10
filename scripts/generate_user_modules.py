import json
from ai_engine.dynamic_module_generator import DynamicModuleGenerator

def main():
    """
    Read recent action_metadata.json, generate modules for each action.
    """
    with open("user_data/actions_metadata.json") as f:
        actions = json.load(f)
    gen = DynamicModuleGenerator()
    for action in actions:
        fname = gen.generate(action["user_id"], action)
        print("Generated module:", fname)

if __name__ == "__main__":
    main()
