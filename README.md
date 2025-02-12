# **Graph Edit Distance Approximation - Experimental Repository**  

This repository contains all code used for the **experimental work** in my Bachelor thesis on **Approximation Algorithms for Graph Edit Distance (GED)**. The experiments focus on benchmarking approximation methods against exact GED computations, using **GEDLIB** as the primary backend.

## **📌 Repository Overview**
- **Framework**: Python for experiment automation, C++ (GEDLIB) for GED computation  
- **Dataset**: GREC dataset (modifiable)  
- **Methods**: Includes multiple approximation techniques (IPFP, BIPARTITE, REFINE, etc.)  
- **Outputs**: GED values, computation time, and method comparisons, logged in an **Excel file**  

---

## **📂 Directory Structure**
📦 ged-approximation-experiments
├── 📜 README.md # Documentation (this file) 
├── 📜 requirements.txt # Required dependencies 
├── 📂 data/ # Dataset storage 
│ ├── datasets/ # Graph dataset (e.g., GREC) 
│ ├── collections/ # Collection XML files 
├── 📂 scripts/ # Experiment scripts 
│ ├── gedlib-parser.py # Runs GEDLIB and logs results 
│ ├── analyze_results.py # Generates evaluation metrics 
│ ├── visualize_results.py # Plots runtime and accuracy 
├── 📂 results/ # Stores output files 
│ ├── ged_results.xlsx # Main output file 
└── 📂 gedlib/ # Cloned GEDLIB repository

---

## **🚀 Setup Instructions**
### **1️⃣ Install Dependencies**
Ensure you have Python 3 installed, then install required packages:
```bash
pip install -r requirements.txt
```

2️⃣ Clone GEDLIB
Since this repository relies on GEDLIB for exact GED computation, clone and compile it:
```bash
git clone https://github.com/dbblumenthal/gedlib.git
cd gedlib
mkdir build && cd build
cmake ..
make
Modify GED_EXECUTABLE in gedlib-parser.py to point to the compiled binary.
```

3️⃣ Run Experiments
To execute GED computations on the dataset:
```bash
python scripts/gedlib-parser.py
```
This will run GEDLIB on the GREC dataset and save results to results/ged_results.xlsx.
