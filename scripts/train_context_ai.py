import json
from agent.recorder.intent_recognizer import IntentRecognizer

def train(model_path: str, training_data: str):
    """
    Fine-tune the intent recognizer on user-approved traces.
    """
    # TODO: load data, run training loops, export ONNX or adapter
    pass

if __name__ == "__main__":
    train("model.onnx", "data/training_traces.json")
