# **Graph Edit Distance Approximation - Experimental Repository**  

This repository contains all code used for the **experimental work** in my Bachelor thesis on **Approximation Algorithms for Graph Edit Distance (GED)**. The experiments focus on benchmarking approximation methods against exact GED computations, using **GEDLIB** as the primary backend.

## **📌 Repository Overview**
- **Graph Edit Distance (GED) Evaluation**: Compare multiple GED approximation algorithms.
- **Dataset Processing & Conversion**: Convert datasets to different formats (TXT → GXL/XML, JSON).
- **GEDLIB Benchmarking**: Execute and log results from GEDLIB-based algorithms.
- **SimGNN Model Training & Evaluation**: Train and test a neural network-based GED predictor.
- **Results Analysis & Visualization**: Compare accuracy, runtime, and scalability across methods.

---

## **📂 Project Structure**
```
📦 ged-approximation
├── 📜 README.md                           # Documentation
├── 📜 requirements.txt                     # Dependencies
├── 📂 data/                                # Raw datasets (original txt files)
│   ├── 📂 AIDS/
│   ├── 📂 IMDB-BINARY/
│   ├── 📂 PROTEINS/
│   ├── 📂 MUTAG/
│   ├── ...                                 # Additional datasets
├── 📂 processed_data/                       # Preprocessed versions of datasets
│   ├── 📂 gxl/                              # Converted files for GEDLIB
│   │   ├── 📂 AIDS/
│   │   ├── 📂 IMDB-BINARY/
│   │   ├── 📂 PROTEINS/
│   │   ├── 📂 MUTAG/
│   ├── 📂 xml/                              # GEDLIB-compatible collection files
│   │   ├── AIDS.xml
│   │   ├── IMDB-BINARY.xml
│   │   ├── PROTEINS.xml
│   │   ├── MUTAG.xml
│   ├── 📂 json_pairs/                       # Converted graph pairs for SimGNN
│   │   ├── 📂 AIDS/
│   │   ├── 📂 IMDB-BINARY/
│   │   ├── 📂 PROTEINS/
│   │   ├── 📂 MUTAG/
├── 📂 scripts/                              # Code for data processing and execution
│   ├── 📂 convert_to_gxl_xml/               # TXT to GXL/XML converters
│   │   ├── aids_converter.py
│   │   ├── imdb_binary_converter.py
│   │   ├── proteins_converter.py
│   │   ├── mutag_converter.py
│   ├── 📂 convert_to_json/                  # TXT to JSON converters
│   │   ├── aids_converter.py
│   │   ├── imdb_binary_converter.py
│   │   ├── proteins_converter.py
│   │   ├── mutag_converter.py
│   ├── 📜 gedlib_parser.py                  # Runs GEDLIB and logs results
│   ├── 📜 analyze_results.py                 # Evaluates experiment results
│   ├── 📜 visualize_results.py               # Plots comparisons
├── 📂 results/                               # Stores experiment results
│   ├── 📂 gedlib/                            # GEDLIB method results
│   │   ├── AIDS_results.xlsx
│   │   ├── IMDB-BINARY_results.xlsx
│   │   ├── PROTEINS_results.xlsx
│   │   ├── MUTAG_results.xlsx
│   ├── 📂 neural/                            # SimGNN results
│   │   ├── AIDS_predictions.json
│   │   ├── IMDB-BINARY_predictions.json
│   │   ├── PROTEINS_predictions.json
│   │   ├── MUTAG_predictions.json
├── 📂 SimGNN/                                # Organized SimGNN implementation
│   ├── 📜 README.md                          # SimGNN-specific documentation
│   ├── 📜 architecture.png                   # Image explaining SimGNN model
│   ├── 📜 training_process.png               # Training visualization
│   ├── 📂 src/                               # Source code
│   │   ├── 📂 dataset/                       # Stores json data needed for training
│   │   │   ├── train/
│   │   │   ├── test/
│   │   ├── 📂 models/                        # Stores trained models
│   │   │   ├── simgnn_model_aids.pth
│   │   │   ├── simgnn_model_imdb.pth
│   │   │   ├── simgnn_model_proteins.pth
│   │   │   ├── simgnn_model_mutag.pth
│   │   ├── 📜 layers.py                      # Neural network layers for SimGNN
│   │   ├── 📜 main.py                        # Main training script
│   │   ├── 📜 param_parser.py                # Parses hyperparameters
│   │   ├── 📜 simgnn.py                      # SimGNN model definition
│   │   ├── 📜 tester.py                      # Testing SimGNN on JSON graph pairs
│   │   ├── 📜 utils.py                       # Utility functions
```

---

## **🚀 Installation & Setup**
### **1️⃣ Install Dependencies**
Ensure you have Python 3 installed, then install the required packages:
```bash
pip install -r requirements.txt
```

### **2️⃣ Clone & Compile GEDLIB**
This repository partially relies on GEDLIB for GED computation:
```bash
git clone https://github.com/dbblumenthal/gedlib.git
cd gedlib
mkdir build && cd build
cmake ..
make
```
Modify `GED_EXECUTABLE` in `scripts/gedlib_parser.py` to point to the compiled binary. See [GEDLIB](https://github.com/dbblumenthal/gedlib) for more information.

---

## **🛠 Running Experiments**
### **1️⃣ Convert Datasets**
#### **For GEDLIB:**
```bash
python scripts/convert_to_gxl_xml/aids_converter.py
python scripts/generate_xml.py --dataset AIDS
```
Generates:
```
processed_data/gxl/AIDS/
processed_data/xml/AIDS.xml
```

#### **For SimGNN:**
```bash
python scripts/convert_to_json/aids_converter.py
```
Generates:
```
processed_data/json_pairs/AIDS/
```

### **2️⃣ Run GEDLIB Experiments**
```bash
python scripts/gedlib_parser.py --dataset AIDS
```
Results stored in:
```
results/gedlib/AIDS_results.xlsx
```

### **3️⃣ Train & Test SimGNN**
```bash
python SimGNN/src/main.py --dataset AIDS
python SimGNN/src/tester.py --dataset AIDS
```
Saves:
```
SimGNN/src/models/simgnn_model_aids.pth
results/neural/AIDS_predictions.json
```

### **4️⃣ Analyze & Visualize**
```bash
python scripts/analyze_results.py
python scripts/visualize_results.py
```

---

## **📜 Citation & References**
If you use this code in your work, please cite:
```
@misc{Filippov2025,
  author = {Mikhail Filippov},
  title = {Graph Edit Distance Approximation - Experimental Repository},
  year = {2025},
  url = {https://github.com/michaelflppv/ged-approximation},
  note = {Bachelor Thesis, University of Mannheim}
}
```
For GEDLIB, refer to the [official repository](https://github.com/dbblumenthal/gedlib). The source code of GEDLIB is distributed under the [GNU Lesser General Public License](https://www.gnu.org/licenses/lgpl-3.0.en.html).

- D. B. Blumenthal, S. Bougleux, J. Gamper, and L. Brun. &ldquo;GEDLIB: A C++ library for graph edit distance computation&rdquo;, GbRPR 2019, [https://doi.org/10.1007/978-3-030-20081-7_2](https://doi.org/10.1007/978-3-030-20081-7_2)
- D. B. Blumenthal, N. Boria, J. Gamper, S. Bougleux, and L. Brun. &ldquo;Comparing heuristics for graph edit distance computation&rdquo;, VLDB J. 29(1), pp. 419-458, 2020, [https://doi.org/10.1007/s00778-019-00544-1](https://doi.org/10.1007/s00778-019-00544-1)

---

## **📬 Contact**
For questions, create an issue or reach out via email.
