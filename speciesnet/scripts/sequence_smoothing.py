#!/usr/bin/env python3

import json
import argparse
from collections import Counter
from datetime import datetime, timedelta
import os


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def group_into_sequences(predictions, time_gap_minutes=3, group_by_folder=False):
    """
    Group images into sequences based on time gap between consecutive images or by folder.
    Returns a list of (seq_id, [prediction_dicts]).
    """
    if group_by_folder:
        # Group by folder (using 'filepath' field)
        from collections import defaultdict

        folder_groups = defaultdict(list)
        for p in predictions:
            folder = os.path.dirname(p.get("filepath", ""))
            folder_groups[folder].append(p)
        sequences = []
        seq_counter = 0
        for folder, preds in folder_groups.items():
            seq_id = f"folder_{os.path.basename(folder) or 'root'}_{seq_counter}"
            sequences.append((seq_id, preds))
            seq_counter += 1
        return sequences
    else:
        # Sort by datetime
        preds_with_dt = [p for p in predictions if "datetime" in p]
        preds_with_dt.sort(key=lambda p: p["datetime"])

        sequences = []
        current_seq = []
        last_dt = None
        seq_counter = 0
        for p in preds_with_dt:
            dt = datetime.fromisoformat(p["datetime"])
            if last_dt is None or (dt - last_dt) > timedelta(minutes=time_gap_minutes):
                # Start new sequence
                if current_seq:
                    sequences.append((f"seq_{seq_counter}", current_seq))
                    seq_counter += 1
                current_seq = [p]
            else:
                current_seq.append(p)
            last_dt = dt
        if current_seq:
            sequences.append((f"seq_{seq_counter}", current_seq))
        return sequences


def smooth_classification_results_sequence_level(
    predictions,
    time_gap_minutes=3,
    keep_original_predictions=False,
    group_by_folder=False,
):
    """
    For each sequence, assign the dominant class (by count) to all images in the sequence.
    Adds 'seq_id' and 'smoothed_class' to each prediction.
    """

    def is_blank_prediction(pred):
        val = pred.get("prediction")
        if not val:
            return True
        last_label = val.split(";")[-1].strip()
        return last_label == "blank"

    sequences = group_into_sequences(predictions, time_gap_minutes, group_by_folder)
    smoothed = []
    for seq_id, seq_preds in sequences:
        # Exclude predictions where the last label is 'blank' or prediction is missing/None
        top_classes = [
            p.get("prediction") for p in seq_preds if not is_blank_prediction(p)
        ]
        if top_classes:
            dominant_class = Counter(top_classes).most_common(1)[0][0]
        else:
            dominant_class = None
        # Find max top-1 prediction_score for dominant class in the sequence
        max_prob = 0.0
        for p in seq_preds:
            if p.get("prediction") == dominant_class and "prediction_score" in p:
                if p["prediction_score"] > max_prob:
                    max_prob = p["prediction_score"]
        for p in seq_preds:
            p["seq_id"] = seq_id
            p["smoothed_class"] = dominant_class
            p["smoothed_class_score"] = max_prob
            # Only update prediction if detections are present and non-empty
            has_detection = bool(p.get("detections"))
            if (
                not keep_original_predictions
                and has_detection
                and dominant_class is not None
            ):
                p["prediction"] = dominant_class
                p["prediction_score"] = max_prob
            smoothed.append(p)
    return smoothed


def get_smoothed_output_path(input_path):
    base, ext = os.path.splitext(input_path)
    return base + "_smoothed" + ext


def main():
    parser = argparse.ArgumentParser(
        description="Sequence-level smoothing for SpeciesNet predictions."
    )
    parser.add_argument(
        "--predictions_json",
        required=True,
        help="Input predictions JSON file (with datetime field)",
    )
    parser.add_argument(
        "--time_gap_minutes",
        type=float,
        default=3.0,
        help="Time gap (minutes) to start a new sequence",
    )
    parser.add_argument(
        "--keep_original_predictions",
        action="store_true",
        help="Do not overwrite original prediction fields",
    )
    parser.add_argument(
        "--group_by_folder",
        action="store_true",
        help="Group all images in the same folder (from 'filepath' field) into a single sequence, ignoring time gaps.",
    )
    args = parser.parse_args()

    preds = load_json(args.predictions_json)
    if "predictions" in preds:
        preds = preds["predictions"]

    smoothed = smooth_classification_results_sequence_level(
        preds,
        time_gap_minutes=args.time_gap_minutes,
        keep_original_predictions=args.keep_original_predictions,
        group_by_folder=args.group_by_folder,
    )
    output_path = get_smoothed_output_path(args.predictions_json)
    save_json({"predictions": smoothed}, output_path)
    print(f"Wrote smoothed predictions to {output_path}")


if __name__ == "__main__":
    main()
