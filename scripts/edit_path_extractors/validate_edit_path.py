#!/usr/bin/env python3
import subprocess
import json
import random

def check_values(output):
    try:
        edit_op = output["edit_operations_count"]
        ged = output["graph_edit_distance"]
        # Bei ged == 0 nehmen wir exakte Übereinstimmung an, um Division durch Null zu vermeiden.
        if ged == 0:
            return edit_op == ged
        return abs(edit_op - ged) <= 0.05 * abs(ged)
    except KeyError:
        print("Erforderliche Schlüssel fehlen in der Ausgabe:", output)
        return False

def run_executable(dataset_path, collection_xml, idx1, idx2, executable):
    command = [
        executable,
        dataset_path,
        collection_xml,
        str(idx1),
        str(idx2)
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Fehler beim Ausführen des Executables für Indizes {} und {}:".format(idx1, idx2), e)
        print("stderr:", e.stderr)
        return None

    try:
        output_json = json.loads(result.stdout)
        return output_json
    except Exception as e:
        print("Fehler beim Parsen der JSON-Ausgabe für Indizes {} und {}:".format(idx1, idx2), e)
        print("Ausgabe war:", result.stdout)
        return None

def main():
    # Parameter festlegen
    dataset = "PROTEINS"
    dataset_path = f"/home/mfilippov/ged_data/processed_data/gxl/{dataset}"
    collection_xml = f"/home/mfilippov/ged_data/processed_data/xml/{dataset}.xml"
    executable = "/home/mfilippov/CLionProjects/gedlib/build/edit_path_exec"
    max_index = 999
    samples = 3
    pairs_per_sample = 1000

    random.seed(42)  # Für Reproduzierbarkeit; entfernen, falls nicht benötigt.

    for sample in range(1, samples + 1):
        within_tolerance_count = 0
        for _ in range(pairs_per_sample):
            idx1 = random.randint(0, max_index)
            idx2 = random.randint(0, max_index)
            output = run_executable(dataset_path, collection_xml, idx1, idx2, executable)
            if output is None:
                continue
            if check_values(output):
                within_tolerance_count += 1
        print(f"Stichprobe {sample}: {within_tolerance_count} von {pairs_per_sample} Paaren entsprechen der 5% Toleranzbedingung.")

if __name__ == "__main__":
    main()