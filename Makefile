SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

POETRY ?= poetry
PYTHON ?= python
POETRY_RUN ?= $(POETRY) run
RUN_PY ?= $(POETRY_RUN) $(PYTHON)
CMAKE ?= cmake
GEDLIB_BUILD_DIR ?= gedlib/build
GEDLIB_LIB ?= gxl
GXL_DATASET ?= aids
GXL_OPTIONS := aids imdb proteins

.PHONY: help gedlib-install gedlib-configure gedlib-build gedlib-all gedlib-test \
	convert-gxl convert-json convert-txt lower-bound lower-bound-validate \
	exact-ged gedlib-run gedlib-edit-path simgnn-edit-path apply-edit-path \
	gedlib-validate-path simgnn-validate-path generate-gxl-collection \
	generate-json-pairs simgnn-train simgnn-eval test-python

help: ## Show available make targets
	@printf "Available targets:\\n"
	@grep -E '^[a-zA-Z0-9_.-]+:.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"} {printf "  %-24s %s\n", $$1, $$2}'

gedlib-install: ## Run GEDLIB install script with cleanup and docs (set GEDLIB_LIB=gxl|... as needed)
	cd gedlib && $(PYTHON) install.py --clean --doc --lib $(GEDLIB_LIB)

gedlib-configure: ## Configure GEDLIB CMake build directory
	$(CMAKE) -S gedlib -B $(GEDLIB_BUILD_DIR)

gedlib-build: gedlib-configure ## Build GEDLIB via CMake
	$(CMAKE) --build $(GEDLIB_BUILD_DIR)

gedlib-all: ## Install and build GEDLIB
	$(MAKE) gedlib-install
	$(MAKE) gedlib-build

gedlib-test: ## Run GEDLIB ctest suite after building
	cd $(GEDLIB_BUILD_DIR) && ctest

convert-gxl: ## Convert a dataset to GXL/XML for GEDLIB (set GXL_DATASET=$(GXL_OPTIONS))
	cd src/converters/gxl_xml && \
	if [ ! -f preprocess_$(GXL_DATASET).py ]; then \
		echo "Unknown dataset '$(GXL_DATASET)'. Choose from: $(GXL_OPTIONS)"; \
		exit 1; \
	fi; \
	$(RUN_PY) preprocess_$(GXL_DATASET).py

convert-json: ## Convert datasets to JSON pairs for SimGNN
	cd src/converters/json && $(RUN_PY) preprocess_all.py

convert-txt: ## Convert datasets to TXT graph pairs
	cd src/converters/txt && $(RUN_PY) preprocess_all.py

lower-bound: ## Estimate lower bounds for graph pairs
	cd heuristics && $(RUN_PY) estimate_lower_bound.py

lower-bound-validate: ## Validate lower bound estimations
	cd heuristics && $(RUN_PY) validate_lower_bounds.py

exact-ged: ## Compute exact GED using AStar-BMao parser
	cd src/c++_parsers && $(RUN_PY) astar_exact_ged.py

gedlib-run: ## Run GEDLIB parser for approximate GED
	cd src/c++_parsers && $(RUN_PY) gedlib_parser.py

gedlib-edit-path: ## Extract GEDLIB edit paths
	cd src/c++_parsers && $(RUN_PY) gedlib_edit_path.py

simgnn-edit-path: ## Extract SimGNN edit paths
	cd SimGNN/src && $(RUN_PY) simgnn_extract_edit_path.py

apply-edit-path: ## Apply edit paths to simulate edits
	cd src/edit_path_test && $(RUN_PY) apply_edit_path.py

gedlib-validate-path: ## Validate GEDLIB edit paths
	cd src/edit_path_test/test && $(RUN_PY) gedlib_validate_edit_path.py

simgnn-validate-path: ## Validate SimGNN edit paths
	cd SimGNN/src && $(RUN_PY) simgnn_validate_edit_path.py

generate-gxl-collection: ## Generate synthetic GXL collection for edit-path testing
	cd src/edit_path_test/generate_synthetic_graphs && $(RUN_PY) generate_gxl_collection.py

generate-json-pairs: ## Generate synthetic JSON pairs for edit-path testing
	cd src/edit_path_test/generate_synthetic_graphs && $(RUN_PY) generate_json_pairs.py

simgnn-train: ## Train SimGNN model
	cd SimGNN/src && $(RUN_PY) main.py

simgnn-eval: ## Evaluate SimGNN model
	cd SimGNN/src && $(RUN_PY) simgnn_evaluate.py

test-python: ## Run pytest suite
	$(RUN_PY) -m pytest
