# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Post-processing functions for SpeciesNet predictions."""

# IMPORTANT: Replace these with the actual labels from your taxonomy file.
ELK_LABEL = "c5ce946f-8f0d-4379-992b-cc0982381f5e;mammalia;cetartiodactyla;cervidae;cervus;canadensis;elk"
RED_DEER_LABEL = "eb3829b0-772e-4088-ae90-f11b9fe38284;mammalia;cetartiodactyla;cervidae;cervus;elaphus;red deer"
MULE_DEER_LABEL = "febff896-db40-4ac8-bcfe-5bb99a600950;mammalia;cetartiodactyla;cervidae;odocoileus;hemionus;mule deer"
CERVUS_LABEL = "9388f0bc-910e-4324-84de-414feca9b4f7;mammalia;cetartiodactyla;cervidae;cervus;;cervus species"


def apply_cervidae_rule(predictions):
    """Applies custom rules to down-weight non-elk/mule deer Cervidae and remap red deer to elk."""

    for prediction in predictions:
        if "classifications" not in prediction:
            continue

        classifications = prediction["classifications"]
        initial_labels = classifications["classes"]
        initial_scores = classifications["scores"]

        # Create a dictionary of label -> score for easier manipulation
        scores_map = dict(zip(initial_labels, initial_scores))

        # Move red deer and cervus score to elk
        for label in [RED_DEER_LABEL, CERVUS_LABEL]:
            if label in scores_map:
                score = scores_map.pop(label)
                scores_map[ELK_LABEL] = scores_map.get(ELK_LABEL, 0) + score

        # Apply the general Cervidae rule
        for label in list(scores_map.keys()):
            try:
                parts = label.split(";")
                # family = parts[3]
                order = parts[2]
                common_name = parts[6]
                # print(order, common_name)
                if common_name == "" or common_name is None:
                    print("Warning: Common name is empty for label:", label)
                # if family == "cervidae" and common_name not in ["elk", "mule deer"]:
                if order == "cetartiodactyla" and common_name not in [
                    "elk",
                    "mule deer",
                    "cervidae family",
                    "cervus species",
                    "cetartiodactyla order",
                    "odocoileus species",
                ]:
                    scores_map[label] /= 20.0
            except IndexError:
                pass  # Ignore malformed labels

        # Re-normalize scores
        total_score = sum(scores_map.values())
        if total_score > 0:
            normalized_scores_map = {
                ll: s / total_score for ll, s in scores_map.items()
            }
        else:
            normalized_scores_map = scores_map

        # Sort and update prediction
        sorted_pairs = sorted(
            normalized_scores_map.items(), key=lambda item: item[1], reverse=True
        )

        if sorted_pairs:
            updated_labels, updated_scores = zip(*sorted_pairs)
            prediction["classifications"]["classes"] = list(updated_labels)
            prediction["classifications"]["scores"] = list(updated_scores)
        else:
            prediction["classifications"]["classes"] = []
            prediction["classifications"]["scores"] = []

    return predictions
